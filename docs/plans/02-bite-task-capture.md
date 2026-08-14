# Bite 2 — Task capture

**Feature:** The user enters and manages the tasks they want to be held
accountable for, from the PWA, categorized as work or personal. This is the
data the whole product orbits; bite 3 consumes it directly.

**Not in this bite:** goals hierarchy, Claude-assisted planning, per-day
plans or "key item" selection (that's a *daily* choice, made in the morning
flow of a later bite — it does not belong on the task record), streaks,
check-ins, LLM anything.

## Layer-by-layer

### L6 Structured store
- Migration 0002: `task` — id, title (short, imperative), note (optional
  free text), category (`work`/`personal`), status
  (`active`/`paused`/`archived`), sort_order, created_at, updated_at.
- No hard deletes — archive only. Do **not** add goal_id, streak fields, or
  schedule fields yet; those arrive with the bites that need them as cheap
  column migrations.
- **Extensibility note:** `status=paused` exists now because the stall rule
  (bite 6) will rescope tasks into it; naming it today avoids a rename
  migration later.

### L4 API
- `GET /api/tasks?status=active` — list (default active, param for all).
- `POST /api/tasks` — create.
- `PATCH /api/tasks/{id}` — edit title/note/category/status/sort_order.
- Validation: title required and ≤ ~120 chars; category required.
- Soft cap: the API never blocks creation, but `GET /api/tasks` response
  includes `active_count` so the client can warn — research says >5 tracked
  items causes check-in fatigue, but the user stays in charge.

### L1 Client
- Add client-side routing (needed from here on): `/` home, `/tasks`.
- Tasks screen: list grouped by category, add via a single always-visible
  input + category toggle (capture must be near-zero friction), tap to
  edit, swipe-or-menu to pause/archive, drag or up/down controls for
  sort_order.
- Show a gentle warning banner when active tasks > 5 ("more than 5 items
  makes check-ins fatiguing — consider pausing some").
- Home screen gains a link/summary ("4 active tasks").

### L5 Scheduler — one seam touched
- `send_scheduled_notification(evening)` body now uses live data: "Evening
  check-in — N tasks on your list." First proof that reach-out content
  derives from DB state (the adaptive-tone lesson from research). Morning
  copy unchanged.

### Layers untouched
L2 push mechanics, L3 Caddy, L7 Vault, L8 LLM, L9 compose (no new
services). If any of these needs modification to complete this bite,
something is over-scoped — stop and reconsider.

## Definition of done
- [ ] `pytest` green: CRUD + validation, archive-not-delete enforced,
      active_count correct, evening notification body reflects task count
      (fake clock).
- [ ] On the iPhone PWA: add work and personal tasks, edit, reorder, pause,
      archive; >5 active shows the warning; data survives backend restart
      (SQLite volume persisted).
- [ ] Evening push observed with the live task count in its body.
