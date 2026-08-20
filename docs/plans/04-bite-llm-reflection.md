# Bite 4 — LLM reflection conversation

Status: implemented (2026-08-19). First feature touching L8 (LLM layer).

## Feature

After completing the evening check-in, the user can tap **"Start reflection"**
to enter an optional multi-turn conversation with a local LLM (Ollama). The
LLM acknowledges what was accomplished, asks gentle questions, and helps the
user reflect on their day. When done, the user taps **"Finish reflection"** and
the conversation is saved as a `type: reflection` journal entry in the Vault.

## Layers touched

| # | Layer | What changed |
|---|-------|--------------|
| L1 | Client | New ReflectionPage (chat UI with streaming), "Start/View reflection" button on CheckInPage, new route `/reflect/:checkinId` |
| L4 | API | New `/api/reflections` router — GET messages, POST chat (SSE streaming), POST finish |
| L5 | Scheduler | `retry_journals` now also retries failed reflection journal writes |
| L6 | Store | New `reflection_message` table, two new columns on `check_in` (`reflection_finished`, `reflection_journal_written`), migration 0004 |
| L7 | Journal | New `type: reflection` entries (`DD-reflection.md`), same directory structure and retry mechanics |
| L8 | LLM | New `services/llm.py` — streaming Ollama chat client with `<think>` tag filtering; new `services/reflection.py` — system prompt construction and message persistence |
| L9 | Infra | `extra_hosts` on backend container for Ollama; `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_MAX_TOKENS` env vars |

L2 (push), L3 (Caddy) unchanged.

## Key design decisions

- **Streaming via SSE**: The backend streams Ollama tokens to the frontend as
  Server-Sent Events. The generator manages its own DB session (not the
  FastAPI dependency-injected one, which closes before streaming begins).
- **`<think>` tag filtering**: Qwen3 models emit `<think>...</think>` blocks.
  These are filtered using a streaming buffer approach that handles tags split
  across token boundaries.
- **Two flags on check_in**: `reflection_finished` (set when user clicks
  Finish) vs `reflection_journal_written` (set when Vault write succeeds).
  The retry job only retries entries where `finished=True` and
  `journal_written=False`, preventing premature closure of in-progress
  conversations.
- **System prompt persisted**: The system message is stored as a
  `role="system"` row in `reflection_message`, making conversations fully
  reconstructable from the DB.

## Configuration

```
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_MAX_TOKENS=256
```

The model must be pulled on the host first: `ollama pull qwen3.5:9b`.

## Extensibility notes for later bites

- Bite 5 (morning planning) can reuse `services/llm.py` — it's model-agnostic.
- The system prompt in `services/reflection.py` uses only check-in data. Bite 7
  (semantic recall) would add graph/vector context here.
- The journal writer follows the same pattern as checkin entries; future entry
  types just add a new renderer.
