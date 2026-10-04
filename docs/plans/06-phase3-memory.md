# Phase 3 — Long-horizon memory

**Goal:** Give the LLM useful context beyond "yesterday" so reflection and
planning conversations feel informed by the user's real history, not just
the last 24 hours.

**Architecture reference:** the three-version memory plan in ARCHITECTURE.md.
Each sub-bite below is one version, implemented as a vertical slice.

## Sub-bite 3a: Daily summaries (v1 memory)

**Feature:** A nightly job summarizes the day's structured data (check-in,
reflection, plan) into a ~150-token paragraph via the local LLM, stored in
SQLite. The last 7 days of summaries are injected into both the reflection
and planning system prompts, giving the LLM a running narrative of recent
history.

**Not in this sub-bite:** embeddings, vector search, graph memory.

### Layer-by-layer

#### L6 Structured store
- Migration 0006: `daily_summary` — id, for_date (unique), summary_text,
  generated_at (UTC), model_used.

#### L8 LLM
- New service `services/summary.py`:
  - `gather_day_data(db, for_date)` — pulls check-in items + note,
    reflection messages, plan items for the date. Returns a structured
    text block.
  - `generate_summary(db, for_date)` — calls Ollama (non-streaming) with
    a tight summarization prompt and the day's data. Stores result in
    `daily_summary`. Skips if the day has no completed check-in.
  - `get_recent_summaries(db, before_date, n=7)` — returns the last N
    summaries before a given date, formatted for prompt injection.
- Add a non-streaming `complete()` helper to `services/llm.py` (the
  summary job doesn't need streaming; planning suggestion already works
  this way via `stream_chat` consumed fully — but a one-shot call is
  cleaner for batch jobs).

#### L5 Scheduler
- New nightly job at midnight in `USER_TZ`: calls `generate_summary` for
  today's date. Runs after the follow-up window has closed.
- Also backfills: on startup, generates summaries for any past dates that
  have completed check-ins but no summary yet.

#### L4 API
- `GET /api/summaries?days=7` — recent summaries (diagnostic/debug use).

#### Prompt injection
- `reflection.py:build_system_prompt()` gains a "Recent days" section
  with the last 7 summaries.
- `planning.py:build_planning_prompt()` gains the same section.

#### L1 Client — untouched
No UI changes. The user experiences this as "the LLM knows more about my
week."

### Definition of done
- [ ] `pytest` green: summary generation from mock day data, backfill
      logic, prompt injection includes summaries, skips dates with no
      check-in.
- [ ] After a day of real use, the reflection and planning prompts
      reference patterns from the prior week.

---

## Sub-bite 3b: Semantic recall (v2 memory)

**Feature:** Journal entries are embedded using nomic-embed-text via Ollama
and stored in a sqlite-vec index. At prompt-build time, the current
context is embedded and the top-k most relevant past entries are retrieved
and injected, giving the LLM access to any past day — not just the last 7.

**Not in this sub-bite:** graph memory, entity extraction, weekly review.

### Layer-by-layer

#### L6 Structured store
- Migration 0007: `journal_embedding` — id, source_type
  (checkin/reflection/plan), source_date, chunk_text, embedding (blob
  via sqlite-vec), created_at.
- sqlite-vec loaded as an extension. Virtual table for ANN search.

#### L8 LLM
- New service `services/embeddings.py`:
  - `embed_text(text)` — calls Ollama embed API with nomic-embed-text.
  - `index_journal_entry(db, source_type, source_date, text)` — embeds
    and stores. Called by the journal writer after each entry is saved.
  - `recall(db, query_text, k=5, exclude_date=None)` — embeds the query,
    runs ANN search in sqlite-vec, returns top-k chunks. Excludes today
    to avoid self-retrieval.
- Modify journal.py writers to call the indexer after successful writes.

#### Prompt injection
- `reflection.py:build_system_prompt()` gains a "Relevant past entries"
  section: embed the current check-in summary → recall top-3.
- `planning.py:build_planning_prompt()` gains the same.

#### L9 Host infra
- Ollama must have nomic-embed-text pulled (`ollama pull nomic-embed-text`).
  Document in .env.example.
- sqlite-vec extension binary must be available in the Docker image. Add
  to Dockerfile (pip install sqlite-vec, or system package).

#### Decision: derived data location
Per architecture recommendation, the sqlite-vec index file lives in the
Vault alongside journal entries (`JOURNAL_PATH/index/embeddings.db` or
similar). If the Vault is locked, recall degrades gracefully to summaries-
only (v1 fallback).

### Definition of done
- [ ] `pytest` green: embed + store, recall returns relevant results,
      graceful degradation when sqlite-vec unavailable or Vault locked.
- [ ] In real use, reflection prompt includes a relevant past entry when
      a similar topic comes up.

---

## Sub-bite 3c: Graph memory + weekly review (v3 memory)

**Feature:** A nightly compression pass extracts temporal entities and
facts from the day's journal into a Graphiti knowledge graph. A weekly
review job surfaces patterns ("you skip workouts on Wednesdays") and
delivers them via push notification.

**Not in this sub-bite:** Claude API integration, goals workspace.

### Layer-by-layer

#### L6/L8 Graph store
- Graphiti with an embedded backend (FalkorDB or Neo4j-lite, TBD based
  on what runs cleanly in Docker without a separate service).
- Ontology seeds: Goal, Task, Plan, CheckIn, Obstacle, Win, Pattern,
  Person, Commitment (per architecture).
- Nightly extraction job: feed the day's journal entries to the local LLM
  with a structured extraction prompt → Graphiti ingestion.

#### L5 Scheduler
- Nightly graph extraction job (after daily summary, ~00:15 USER_TZ).
- Weekly review job (Sunday evening or Monday morning, TBD): query the
  graph for recurring patterns → push notification + journal entry.

#### L2 Push
- Weekly review notification: "Weekly patterns: ..." with a deep link
  to a new review screen.

#### L1 Client
- `/review` screen showing the weekly pattern summary.

#### Decision: extraction model
Per architecture recommendation, local LLM first. If graph quality is
poor (entities missed, relationships wrong), revisit with Claude API —
journal text is small, cost is cents per day.

### Definition of done
- [ ] Nightly extraction produces sensible graph nodes from real journal
      data.
- [ ] Weekly review surfaces at least one real pattern after 2+ weeks of
      data.
- [ ] Push notification delivers the review; tapping opens the review
      screen.

---

## Implementation order

3a first — it's the simplest, has zero new dependencies, and immediately
improves both the reflection and planning conversations. 3b follows once
summaries are working (it builds on the same journal data). 3c is the
riskiest (small-model graph extraction quality) and comes last.
