"""
Integration tests that hit real Ollama on localhost:11434.

No mocks — if Ollama is down, these fail, which is correct:
if you can't reach the LLM, AcctBud's reflection feature is broken.
"""

import json
from unittest.mock import patch

from app.services.llm import stream_chat


OLLAMA_URL = "http://localhost:11434"

SIMPLE_SYSTEM = (
    "You are AcctBud, a personal accountability companion. "
    "Respond in exactly one sentence."
)


class TestStreamChat:
    """Verify stream_chat works end-to-end against real Ollama."""

    def test_produces_tokens(self):
        messages = [
            {"role": "system", "content": SIMPLE_SYSTEM},
            {"role": "user", "content": "Hi"},
        ]
        with patch("app.config.settings.ollama_base_url", OLLAMA_URL):
            tokens = list(stream_chat(messages, max_tokens=64))

        assert len(tokens) > 0
        full = "".join(tokens)
        assert len(full) > 5

    def test_think_tags_stripped(self):
        messages = [
            {"role": "system", "content": SIMPLE_SYSTEM},
            {"role": "user", "content": "What is 2+2?"},
        ]
        with patch("app.config.settings.ollama_base_url", OLLAMA_URL):
            tokens = list(stream_chat(messages, max_tokens=128))

        full = "".join(tokens)
        assert "<think>" not in full
        assert "</think>" not in full

    def test_respects_max_tokens(self):
        messages = [
            {"role": "system", "content": "Write a long story about a cat."},
            {"role": "user", "content": "Go."},
        ]
        with patch("app.config.settings.ollama_base_url", OLLAMA_URL):
            tokens = list(stream_chat(messages, max_tokens=32))

        full = "".join(tokens)
        words = full.split()
        assert len(words) < 100

    def test_bad_model_raises(self):
        messages = [{"role": "user", "content": "Hi"}]
        import pytest

        with patch("app.config.settings.ollama_base_url", OLLAMA_URL):
            with pytest.raises(ValueError, match="not found"):
                list(stream_chat(messages, model="nonexistent-model-xyz:latest"))


class TestReflectionPromptQuality:
    """
    Smoke tests for reflection prompt quality.

    These aren't deterministic — they check that the model's output
    is in the right ballpark given the system prompt constraints.
    Failures here warrant eyeballing via the harness script, not
    necessarily a code fix.
    """

    def _reflection_response(self, system_prompt: str, user_msg: str = "Let's reflect.") -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        with patch("app.config.settings.ollama_base_url", OLLAMA_URL):
            tokens = list(stream_chat(messages, max_tokens=256, temperature=0.3))
        return "".join(tokens)

    def test_mentions_completed_task_by_name(self):
        prompt = (
            "You are AcctBud, a personal accountability companion.\n"
            "Be concise: 2-3 sentences. Reference specific task names.\n\n"
            "Completed tasks (1):\n  - [work] Ship login page\n\n"
            "Begin by warmly acknowledging what they accomplished (mention tasks by name)."
        )
        response = self._reflection_response(prompt)
        assert "login" in response.lower(), (
            f"Expected model to mention 'login page' task. Got: {response}"
        )

    def test_empathetic_when_nothing_done(self):
        prompt = (
            "You are AcctBud, a personal accountability companion.\n"
            "Be concise: 2-3 sentences.\n"
            "If nothing was completed, be empathetic and curious (not judgmental).\n"
            "Never lecture.\n\n"
            "Not completed (2):\n  - [work] Ship login page\n  - [personal] Run 3 miles\n\n"
            "Lead with empathy — not every day goes as planned."
        )
        response = self._reflection_response(prompt)
        negative_markers = ["you failed", "disappointed", "you should have", "unacceptable"]
        for marker in negative_markers:
            assert marker not in response.lower(), (
                f"Response was judgmental (found '{marker}'). Got: {response}"
            )

    def test_references_user_note(self):
        prompt = (
            "You are AcctBud, a personal accountability companion.\n"
            "Be concise: 2-3 sentences. Reference specific details.\n\n"
            "Completed tasks (1):\n  - [work] Ship login page\n"
            "Not completed (1):\n  - [personal] Run 3 miles\n\n"
            'User\'s note: "Got pulled into a production incident all afternoon"\n\n'
            "Acknowledge what they accomplished and reference their note."
        )
        response = self._reflection_response(prompt)
        assert any(
            word in response.lower()
            for word in ["incident", "production", "pulled"]
        ), f"Expected model to reference the user's note. Got: {response}"
