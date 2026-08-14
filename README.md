# AcctBud — Accountability Buddy

A personal accountability agent: morning planning, evening check-ins, and a
reflective journal, backed by a local LLM on TheRig and reachable from any
device (iPhone 13 first).

## Core loop

- **Morning:** push notification → short chat to set the day's plan, anchored on
  **1 key work item + 1 key personal item**.
- **Evening:** push notification → multiple-choice check-in ("which of today's
  tasks got done?" — one, many, or none), then a short reflective conversation:
  congratulate wins, probe what blocked the misses. Everything lands in the
  journal, timestamped.
- **Anytime:** a goals/tasks workspace where the Claude API helps explore goals,
  break them into tasks, and plan.

## Where things live

| Piece | Location |
|---|---|
| Backend (FastAPI + Ollama local LLM) | TheRig |
| Journal entries (plaintext markdown) | The Vault (encrypted area on TheRig) |
| Compressed memory (graph + embeddings) | TheRig — see open question in `docs/ARCHITECTURE.md` |
| Client | Installable PWA (iPhone home screen, also desktop) |

## Docs

- [`docs/RESEARCH.md`](docs/RESEARCH.md) — prior art and lessons learned from similar projects.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — proposed architecture, phased build plan, and open decisions.
