# Bite 5 — Morning planning flow

Status: **plan** (2026-08-20). Ready for review.

## Feature

The morning push deep-links to a planning screen where the user picks today's
focus items from their active tasks. A local LLM opens the conversation with a
suggested focus based on yesterday's check-in outcomes, referencing what was
completed and what was missed. The user selects their focus items — always at
least **1 key work item + 1 key personal item**, hard cap 5 total — and confirms
the plan. The confirmed plan is saved to SQLite and journaled to the Vault.

The evening check-in adapts: when a confirmed plan exists for today, the
check-in asks about *planned items only* instead of all active tasks. Days
without a morning plan fall back to the current behavior (all active tasks).

**Not in this bite:** streaks, stall rule, daily summaries (bite 6). Semantic
recall, graph memory (bite 7). Goals workspace (bite 8). The LLM conversation
here is a single opening suggestion, not a multi-turn planning chat — multi-turn
planning belongs with the Claude API goals workspace in bite 8.

## UX flow

1. Morning push arrives → user taps → `/plan/today`.
2. Page loads active tasks grouped by category (work / personal).
3. LLM streams a brief opening message: "Yesterday you finished X and Y — nice.
   Z has been on your list for a few days; maybe today's the day?" (2–3
   sentences, references specific task names, non-prescriptive).
4. User taps tasks to toggle them as today's focus. Key-item badges mark the
   primary work and personal items (first selection in each category auto-marks
   as key; user can tap to move the badge).
5. Validation: at least 1 work + 1 personal key item required; max 5 total.
6. User taps **"Confirm plan"** → plan saved, journal written, redirect to home.
7. Home screen shows "Today's plan: N items" card linking back to the plan
   (read-only once confirmed).

## Layer-by-layer

### L6 Structured store

Migration 0005:

- **`daily_plan`** — id, for_date (unique), status (`draft` / `confirmed`),
  created_at, confirmed_at (nullable), journal_written (bool, default false),
  llm_suggestion (text, nullable — the opening LLM message, stored for the
  journal).
- **`daily_plan_item`** — id, plan_id (FK → daily_plan), task_id, task_title,
  task_category, is_key (bool, default false).

No `plan_message` table — this bite is a single LLM suggestion, not a
multi-turn conversation. The `llm_suggestion` column on `daily_plan` is
sufficient. A future bite can add a messages table if multi-turn planning
becomes a feature.

**Evening check-in change:** `get_or_create_checkin` gains a check: if a
confirmed `daily_plan` exists for `for_date`, snapshot plan items instead of
all active tasks. The `check_in_item` table is unchanged — it already stores
`task_id`, `task_title`, `task_category`, `done`.

### L8 LLM

New `services/planning.py`:

- `build_planning_prompt(active_tasks, yesterday_checkin, yesterday_reflection)`
  — system prompt that includes today's active task list, yesterday's check-in
  results (done/not-done), and optionally yesterday's reflection summary. Asks
  the model to suggest 2–3 focus items with brief reasoning. Same concise style
  as the reflection prompt.
- Reuses `services/llm.py` `stream_chat` — no changes to the LLM client.

### L4 API

New router `routers/planning.py`, prefix `/api/plans`:

- **`GET /today`** — returns today's plan (creates a draft if none exists).
  Response includes plan status, items (empty for draft), the LLM suggestion
  text (if already generated), and the active task list for selection.
- **`POST /{id}/suggest`** — triggers the LLM suggestion. Streams SSE tokens
  (same format as reflection chat). Stores the assembled text in
  `daily_plan.llm_suggestion`. Idempotent: returns cached suggestion if already
  generated.
- **`POST /{id}/confirm`** — body: list of `{task_id, is_key}` items.
  Validates: ≥1 key work + ≥1 key personal, ≤5 total. Sets status to
  `confirmed`, snapshots items into `daily_plan_item`, writes journal, sets
  `confirmed_at`. Returns the confirmed plan. Idempotent (re-confirm updates).

### L7 Journal store

New entry type `type: plan` — `DD-plan.md`:

```
---
date: 2026-08-20T08:15:00Z
local_date: 2026-08-20
type: plan
plan_id: 42
---

# Morning plan

## Focus items
- **[work] Ship login page** ⭐ key
- **[work] Review PR #42**
- **[personal] Run 3 miles** ⭐ key

## AcctBud's suggestion
> Yesterday you shipped the API endpoint and ran 2 miles — solid
> progress. Review PR #42 has been waiting since Monday; maybe
> clear that today so it stops nagging at you?
```

Same retry mechanics as checkin and reflection journal entries — write on
confirm, set `journal_written` flag, retry job picks up failures.

### L1 Client

- **New `PlanPage.tsx`** — route `/plan/today`:
  - Loads `GET /api/plans/today` to get active tasks and plan state.
  - If plan is `draft`: fires `POST /api/plans/{id}/suggest` to stream the LLM
    suggestion (displayed as a card above the task list). Tasks shown as
    tappable rows grouped by category. Key-item badge (star toggle) on each
    selected task. Confirm button with validation feedback.
  - If plan is `confirmed`: read-only view of focus items with the suggestion.
- **Updated morning push URL:** `NOTIFICATION_CONTENT["morning"]["url"]`
  changes from `/acctbud/` to `/acctbud/plan/today`.
- **Home screen card:** new "Today's plan" card between Tasks and Check-in.
  Shows status (no plan yet / N focus items / confirmed). Links to
  `/plan/today`.
- **Route:** add `/plan/today` to `main.tsx`.

### L5 Scheduler

- Morning push URL updated (see L1).
- `retry_journals` extended: `retry_pending_plan_entries(db)`.
- `rollover_missed` extended: draft plans from prior days → status `skipped`
  (a skipped plan is not an error — the evening check-in falls back to all
  active tasks).

### L9 Host infra

No changes — Ollama config from bite 4 is reused.

### Layers untouched

L2 (push transport), L3 (Caddy).

## Key design decisions

1. **Single LLM suggestion, not multi-turn.** A short local model is good at
   "here's what I notice about your task list" but not at multi-turn planning
   negotiation. The structured UI (tap to select) does the heavy lifting; the
   LLM adds a warm, personalized nudge. Multi-turn planning with Claude API is
   bite 8.

2. **Plan items snapshot from tasks.** Same pattern as check-in items — the plan
   records `task_title` and `task_category` at confirmation time, so later task
   edits don't rewrite the day's plan.

3. **Evening check-in uses plan when available.** This is the architectural
   intent ("the day's plan as multiple choice") and makes the Plan–Act–Reflect
   cycle coherent. The fallback to all active tasks means skipping the morning
   plan never breaks the evening flow.

4. **Max 5 items enforced in the API.** The research says >5 causes check-in
   fatigue. The UI should make this feel like a natural constraint, not an
   error — e.g., graying out unselected tasks when 5 are chosen.

## Definition of done

- [ ] `pytest` green: plan CRUD, suggestion caching, confirm validation (key
      items, max 5), journal content, retry on locked Vault, evening check-in
      uses plan items when confirmed plan exists, evening check-in falls back
      to all active tasks when no plan exists, draft plans rolled over to
      `skipped`.
- [ ] LLM integration test: suggestion references yesterday's outcomes and
      active task names.
- [ ] On the iPhone, one real morning: push arrives → tap → plan screen → LLM
      suggests → select focus items → confirm → home screen shows plan → that
      evening's check-in shows only the planned items.
