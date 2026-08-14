# Bite 3 — Respond & record

**Feature:** The evening push deep-links to a tap-only check-in: today's
active tasks as multiple choice — select one, many, or explicitly **none**
— submit, done. The response is recorded with timestamps in SQLite and
written as a markdown journal entry to The Vault. One follow-up nag fires
if the check-in is ignored for 2 hours. This closes the accountability
loop end-to-end; every subsystem except the LLM is now real.

**Not in this bite:** LLM reflection/congratulations/probing (bite 4 —
which is why check-in records and journal files must be complete enough
for an LLM to consume later), morning planning, streak computation,
free-text journaling UI (an optional note field is the only text input).

## Layer-by-layer

### L6 Structured store
- Migration 0003:
  - `check_in` — id, for_date (local date), created_at, notified_at,
    followup_at (nullable), completed_at (nullable), status
    (`pending`/`completed`/`missed`), note (nullable free text).
  - `check_in_item` — id, check_in_id, task_id, done (bool). Rows snapshot
    the active task list at creation time, so later task edits can't
    rewrite history.
- "None done" is completed_at set with all items done=false — completing a
  check-in honestly is success; only silence becomes `missed`.
- **Extensibility note:** bite 6 computes streaks purely from
  `check_in_item` history; bite 4 reads `note` + items to seed the
  reflection conversation. Nothing else is needed from this schema.

### L5 Scheduler
- Evening job becomes: create today's `check_in` + item snapshot → send
  push deep-linking to `/checkin/today` ("Evening check-in — which of your
  N tasks happened today?") → set notified_at.
- New follow-up job (runs a few minutes' resolution): if a `check_in` is
  pending, 2 h past notified_at, and followup_at is null → send exactly one
  gentler follow-up, set followup_at. Never more (research: cooldown rule;
  nagging twice reads as spam).
- Day rollover job at morning time: any prior pending check_in → `missed`.
  A missed day is data, not a retroactive to-do.
- Skip creation if no active tasks exist (send nothing — an empty check-in
  is noise).

### L4 API
- `GET /api/checkins/today` — today's check-in with items (creates
  on-demand if the scheduler hasn't yet, e.g. user opens app early; same
  snapshot code path as the scheduler — one function, two callers).
- `POST /api/checkins/{id}/complete` — body: done task_ids (possibly
  empty) + optional note. Sets items, completed_at, status; idempotent
  (re-submission updates, latest wins, journal entry rewritten).
- `GET /api/checkins?limit=30` — recent history, newest first.

### L7 Journal store — first Vault touch
- On completion, write `JOURNAL_PATH/YYYY/MM/DD-checkin.md`: frontmatter
  (timestamp UTC + local, type: checkin, task ids) and a human-readable
  body — done list, not-done list, the note. Plain markdown a future LLM
  (or the user, in any editor) can read; no app-private format.
- `JOURNAL_PATH` env var → the Vault mount. **Degrade gracefully:** if the
  path is missing/unwritable (Vault locked), the check-in still succeeds in
  SQLite; set a `journal_written` flag false and retry pending entries on a
  schedule and at next startup. The Vault being locked must never block the
  user's 30-second check-in.
- **Extensibility note:** this writer (frontmatter + body + retry queue) is
  *the* journal layer; bites 4–5 add new entry types through it, so keep
  entry-type-specific rendering separate from the write/retry mechanics.

### L1 Client
- `/checkin/today` screen: the day's tasks as large tap-to-toggle rows, an
  explicit "Nothing today" control (selecting none must be a first-class
  honest answer, visually equal — no shaming), optional one-line note,
  submit → confirmation of exactly what was recorded ("Recorded 2 of 4,
  8:42 PM").
- Push `notificationclick` routes to `/checkin/today` via the `url` field
  wired in bite 1.
- `/history`: read-only list of past check-ins (date, n-of-m, note) — the
  user's proof the record exists.
- Home screen shows tonight's check-in status (pending → link / completed
  → summary).

### L9 Host infra
- Compose: mount the Vault journal path into the backend container
  (read-write, that path only); add `JOURNAL_PATH` to `.env.example` with
  a comment documenting the locked-Vault behavior.

### Layers untouched
L2 push mechanics, L3 Caddy, L8 LLM.

## Definition of done
- [ ] `pytest` green: snapshot semantics (task edited/archived after
      creation doesn't alter the check-in), none-done vs missed
      distinction, idempotent completion, follow-up fires once and only
      once (fake clock), rollover marks missed, journal file content
      correct, locked-Vault path → check-in succeeds and entry is written
      on retry.
- [ ] On the iPhone, one real evening: push arrives → tap → check-in screen
      → select tasks (and, another day, "Nothing today") → submit →
      confirmation; history shows it.
- [ ] Journal file appears in the Vault with correct frontmatter and
      readable body; ignoring a check-in produces exactly one follow-up
      2 h later and a `missed` status next morning.
