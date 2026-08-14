# Architecture

Status: **proposal** (2026-08-13). Decisions marked ⚠️ need Conrad's sign-off.

## Overview

```
iPhone 13 / any browser
   └─ PWA (installed to home screen; chat UI + goals workspace)
        │  HTTPS over Tailscale (no ports opened on TheRig)
        ▼
TheRig ─ FastAPI backend
   ├─ Scheduler (APScheduler): morning/evening triggers → Web Push (outbound
   │    to Apple/Google push services; phone need not be on the tailnet to
   │    receive the notification — only to open the app)
   ├─ Chat engine → Ollama (local LLM: Qwen3-class, sized to 16 GB VRAM)
   │    context = system prompt + today's state + graph/vector recall, so the
   │    small context window is never fed raw journal history
   ├─ Goals/Planning module → Claude API (explore goals, break down tasks)
   ├─ Memory layer
   │    ├─ SQLite: tasks, goals, plans, check-in results, streaks (source of
   │    │    truth for structured state)
   │    ├─ Vector index (sqlite-vec; embeddings via Ollama nomic-embed-text)
   │    └─ Graph memory (phase 3): Graphiti on an embedded/local backend —
   │         temporal facts extracted nightly from the day's journal
   └─ Journal writer → The Vault (plaintext markdown, timestamped, append-only)
```

## The daily cycle (Plan–Act–Reflect)

- **Morning push → plan chat.** Agent proposes candidates from open tasks and
  yesterday's reflection; conversation lands on the day's plan, always naming
  **1 key work item + 1 key personal item** (hard cap ~5 items total — research
  says more causes check-in fatigue). Plan saved to SQLite + journal.
- **Evening push → check-in.** First screen is *taps, not typing*: the day's
  plan as multiple choice (select one/many/none). Then the LLM responds from
  real data — congratulates what was done by name, and asks one gentle probing
  question about what blocked the rest. Optional free-text reflection follows
  the draft → clarify → user-approves loop. One follow-up nag max (2 h later)
  if the check-in is ignored.
- **Weekly review (later phase).** Pattern surfacing from the graph: "planning
  fell through on Wednesdays 3 weeks running."
- **Stall rule:** an item missed ≥3 consecutive days triggers a rescope
  conversation instead of another nag.

## Journal & The Vault

- Each entry: one markdown file `YYYY/MM/DD-<slug>.md` with frontmatter
  (timestamp, cycle phase: plan|checkin|reflection|freeform, related task ids).
  Written to a configured Vault mount path; the app treats it as append-only.
- The backend only requires the Vault to be *mounted/unlocked* when writing or
  doing recall-indexing; structured state in SQLite keeps the app functional
  otherwise.
- ⚠️ **Open decision — derived data leaks content.** Embeddings and graph facts
  are lossy-but-reconstructable derivatives of journal text. If the Vault's
  threat model matters, the vector index + graph DB should live in the Vault
  too (they're just files if we choose embedded stores). Recommendation: keep
  *all* memory-layer files in the Vault; only ephemeral state outside it.

## Memory: solving the small-context problem

Phased, because graph extraction is the riskiest piece (small models do it
poorly — see RESEARCH.md):

1. **v1:** SQLite structured state + last-N-days summaries in the prompt.
   Nightly job: local LLM writes a ~150-token summary of the day.
2. **v2:** semantic recall — embed journal entries (nomic-embed-text via
   Ollama, sqlite-vec index); chat engine retrieves top-k relevant snippets.
3. **v3:** Graphiti temporal graph. Nightly compression pass extracts
   entities/facts with validity intervals. Ontology seeds: `Goal`, `Task`,
   `Plan`, `CheckIn`, `Obstacle`, `Win`, `Pattern`, `Person`, `Commitment` —
   grown as the project progresses.
   ⚠️ **Open decision:** run extraction on the local model (private, lower
   quality) vs. Claude API (better ontology adherence, journal text leaves
   TheRig). Recommendation: local first; revisit if graph quality disappoints,
   possibly with per-entry sensitivity flags.

## Client

- **PWA** (Vite + React + vite-plugin-pwa): installable on the iPhone home
  screen, gets standard Web Push on iOS 16.4+, and runs on any other device —
  satisfies "variety of devices" with one codebase, no App Store.
- Two surfaces: **Chat** (daily cycle) and **Goals** (goal/task tree, Claude-
  assisted planning sessions).

## Access & security

- **Tailscale** on TheRig + phone; PWA served via Caddy with a real cert
  (Tailscale cert or DNS-challenge). Nothing exposed to the public internet;
  push notifications work anyway because Web Push is outbound-only from the
  server.
- Claude API calls: goals/planning module by design; journal text only per the
  open decision above. Never log or commit keys (env file on TheRig).

## Build phases

| Phase | Deliverable | Proves |
|---|---|---|
| 0 | Repo scaffold, FastAPI skeleton, Ollama wired, docker-compose for TheRig | plumbing |
| 1 | Evening check-in end-to-end: scheduler → push → PWA multiple-choice → LLM reflection → journal file in Vault + SQLite | the core loop |
| 2 | Morning planning flow + streaks/stall rule + daily summaries in prompt | Plan–Act–Reflect complete |
| 3 | Semantic recall, then Graphiti graph + nightly compression + weekly review | long-horizon memory |
| 4 | Goals workspace with Claude API planning sessions | the second app surface |

Phase 1 is deliberately the *evening* flow first: it exercises every subsystem
(scheduler, push, PWA, LLM, Vault) on the highest-value interaction.
