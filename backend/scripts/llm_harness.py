#!/usr/bin/env python3
"""
Manual harness for eyeballing AcctBud reflection quality against real Ollama.

Run from backend/:
    .venv/bin/python scripts/llm_harness.py [--scenario all-done|none-done|mixed|with-note]

Prints the system prompt and streams the model's opening reflection so you can
judge tone, conciseness, and whether it references tasks by name.
"""

import argparse
import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm import stream_chat

SCENARIOS = {
    "all-done": {
        "label": "All tasks completed",
        "done": [
            ("[work] Ship login page", True),
            ("[work] Review PR #42", True),
            ("[personal] Run 3 miles", True),
        ],
        "note": None,
    },
    "none-done": {
        "label": "Nothing completed",
        "done": [
            ("[work] Ship login page", False),
            ("[work] Review PR #42", False),
            ("[personal] Run 3 miles", False),
        ],
        "note": None,
    },
    "mixed": {
        "label": "Some done, some not",
        "done": [
            ("[work] Ship login page", True),
            ("[work] Review PR #42", False),
            ("[personal] Run 3 miles", False),
        ],
        "note": None,
    },
    "with-note": {
        "label": "Mixed results with a user note",
        "done": [
            ("[work] Ship login page", True),
            ("[work] Review PR #42", False),
            ("[personal] Run 3 miles", False),
        ],
        "note": "Got pulled into a production incident all afternoon",
    },
}


def build_test_prompt(scenario: dict) -> str:
    lines = [
        "You are AcctBud, a personal accountability companion.",
        "Your role is to help the user reflect on their day with warmth and gentle curiosity.",
        "Guidelines:",
        "- Be concise: 2-3 sentences per response.",
        "- Ask one question at a time.",
        "- Use positive reinforcement for what was accomplished.",
        "- If tasks were not completed, be empathetic and curious (not judgmental).",
        "- Never lecture. The user is the author of their own reflection.",
        "- Reference specific task names from the data below.",
        "",
        "Today's date: 2026-08-20",
        "",
    ]

    completed = [(t, d) for t, d in scenario["done"] if d]
    not_done = [(t, d) for t, d in scenario["done"] if not d]

    if completed:
        lines.append(f"Completed tasks ({len(completed)}):")
        for task, _ in completed:
            lines.append(f"  - {task}")
    if not_done:
        lines.append(f"Not completed ({len(not_done)}):")
        for task, _ in not_done:
            lines.append(f"  - {task}")
    if not completed and not not_done:
        lines.append("No tasks were active today.")

    if scenario["note"]:
        lines.append(f'\nUser\'s note: "{scenario["note"]}"')

    lines.extend([
        "",
        "Begin by warmly acknowledging what they accomplished (mention tasks by name),",
        "then ask one gentle question to start the reflection.",
        "If nothing was completed, lead with empathy — not every day goes as planned.",
    ])
    return "\n".join(lines)


def run_scenario(name: str, scenario: dict, ollama_url: str, model: str) -> None:
    prompt = build_test_prompt(scenario)

    print(f"\n{'=' * 60}")
    print(f"SCENARIO: {name} — {scenario['label']}")
    print(f"{'=' * 60}")
    print(f"\n--- System prompt ---\n{prompt}\n")
    print("--- Model response (streaming) ---")

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Hey AcctBud, let's reflect."},
    ]

    start = time.perf_counter()
    token_count = 0
    first_token_time = None

    for token in stream_chat(messages, model=model):
        if first_token_time is None:
            first_token_time = time.perf_counter()
        print(token, end="", flush=True)
        token_count += 1

    elapsed = time.perf_counter() - start
    ttft = (first_token_time - start) if first_token_time else elapsed

    print(f"\n\n--- Stats ---")
    print(f"Chunks: {token_count}  |  TTFT: {ttft:.1f}s  |  Total: {elapsed:.1f}s")
    print()


def main():
    parser = argparse.ArgumentParser(description="Test AcctBud reflection prompts against Ollama")
    parser.add_argument(
        "--scenario", "-s",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Which scenario to run (default: all)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: localhost:11434)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Override model (default: use OLLAMA_MODEL from .env / qwen3.5:9b)",
    )
    args = parser.parse_args()

    if args.scenario == "all":
        scenarios = SCENARIOS.items()
    else:
        scenarios = [(args.scenario, SCENARIOS[args.scenario])]

    from app.config import settings
    settings.ollama_base_url = args.ollama_url

    for name, scenario in scenarios:
        run_scenario(name, scenario, args.ollama_url, args.model)


if __name__ == "__main__":
    main()
