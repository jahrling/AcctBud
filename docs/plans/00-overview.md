# Build plans — overview and conventions

Status: planning handoff (2026-08-13). Written for a Claude Code (Opus)
session to implement. Read `docs/ARCHITECTURE.md` and `docs/RESEARCH.md`
first; this file governs *how* we build, the numbered plans govern *what*.

## The cheeseburger-bite method

We never build a whole layer at a time. Every bite is a thin **vertical
slice through the entire deployment stack** — infra to iPhone — delivering
one user-valuable feature. Each layer gets only what this bite needs, built
so the next bite extends it instead of replacing it.

## The full stack (all layers, top to bottom)

| # | Layer | Technology (fixed decisions) |
|---|-------|------------------------------|
| L1 | Client | PWA — Vite + React + vite-plugin-pwa, installed to iPhone home screen |
| L2 | Push transport | Standard Web Push (VAPID, `pywebpush`); outbound-only from TheRig |
| L3 | Edge / TLS | Caddy reverse proxy, valid HTTPS cert, reachable over Tailscale only |
| L4 | API | FastAPI (Python 3.12+), Pydantic models |
| L5 | Scheduler | APScheduler inside the FastAPI process |
| L6 | Structured store | SQLite via SQLAlchemy 2.0 + Alembic migrations |
| L7 | Journal store | Timestamped markdown files in The Vault (mount path via env) |
| L8 | LLM | Ollama local (chat/reflection), Claude API (goals/planning) |
| L9 | Host infra | Docker Compose on TheRig; config via `.env` (never committed) |

A bite may legitimately leave a layer untouched (bites 1–3 never touch L8 —
**the first three bites require zero LLM work**), but must not build any
layer beyond what the bite's feature needs.

## Bite sequence

1. **[Bite 1 — Reach out](01-bite-reach-out.md):** a scheduled push
   notification from TheRig lands on the iPhone lock screen; tapping opens
   the installed PWA. (Research verdict: proactive reach-out *is* the
   product — so it ships first.)
2. **[Bite 2 — Task capture](02-bite-task-capture.md):** the user enters and
   manages the tasks they want to be held accountable for.
3. **[Bite 3 — Respond & record](03-bite-respond-record.md):** the evening
   push leads to a tap-only multiple-choice check-in (one / many / none);
   responses are recorded in SQLite and journaled to the Vault.

Future bites (not planned in detail yet; listed so extensibility choices
have a target): 4 — LLM reflection conversation after check-in (L8 local);
5 — morning planning flow (1 key work + 1 key personal item); 6 — streaks,
stall rule, daily summaries; 7 — semantic recall, then Graphiti graph
memory; 8 — goals workspace with Claude API planning.

## Conventions for the implementing session

- **Repo layout:** `backend/` (FastAPI app, Alembic, tests), `pwa/` (Vite
  app), `deploy/` (docker-compose.yml, Caddyfile, `.env.example`),
  `docs/`.
- **Config:** everything environment-driven (`.env` on TheRig from a
  committed `.env.example` with every key documented). No secrets in git —
  includes VAPID private key and, later, API keys.
- **Migrations:** every schema change is an Alembic migration from bite 1
  onward. Adding columns later is cheap; that is the extensibility valve —
  do not add speculative columns "for later."
- **Deletes:** accountability data is history — archive/status flags, no
  hard deletes of user data.
- **Tests:** backend logic (scheduling decisions, endpoints, persistence)
  gets pytest coverage; run tests before declaring a bite done. Push
  delivery and PWA install are verified manually per each bite's
  "definition of done" checklist.
- **Time:** store UTC in the DB; the user's timezone is a config value
  (`USER_TZ`, e.g. `America/New_York`) used by the scheduler and all
  user-facing rendering. Get this right in bite 1; it touches everything.
- **Single user, single server.** No auth system beyond network-level
  (Tailscale) in these bites; do not build accounts. Note in code where a
  user id would slot in (a `user` column default `1` is acceptable in
  tables where later multi-device/multi-user pressure is plausible — that
  is the only speculative allowance).

## Environment prerequisites (Conrad, not the coding agent)

- Tailscale running on TheRig and the iPhone; a stable HTTPS hostname for
  TheRig (Tailscale cert or DNS-challenge cert in Caddy).
- Docker + Compose on TheRig; the Vault mount path exists and is writable
  when unlocked (needed from bite 3).
