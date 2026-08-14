# Bite 1 — Reach out

**Feature:** At configured morning and evening times, TheRig sends a push
notification that lands on the iPhone lock screen. Tapping it opens the
installed AcctBud PWA. This is the smallest thing that proves the product's
core claim: the agent contacts the user, not the other way around.

**Not in this bite:** tasks, check-ins, chat, LLM anything, Vault writes,
notification content beyond static-ish text. The PWA is a shell whose only
job is registration and receiving pushes.

## Layer-by-layer

### L9 Host infra
- Repo scaffold per overview conventions (`backend/`, `pwa/`, `deploy/`).
- `deploy/docker-compose.yml`: two services — `backend` (FastAPI via
  uvicorn) and `caddy`. Volumes for SQLite file and Caddy data.
- `deploy/.env.example`: `PUBLIC_ORIGIN`, `USER_TZ`, `MORNING_TIME`,
  `EVENING_TIME` (HH:MM local), `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
  `VAPID_SUBJECT` (mailto:), `DB_PATH`.
- A documented one-liner (script or make target) to generate the VAPID
  keypair once.

### L3 Edge / TLS
- `deploy/Caddyfile`: serve the built PWA as static files at `/`, reverse-
  proxy `/api/*` to the backend. HTTPS with a valid cert is **mandatory** —
  iOS service workers and Web Push require a secure context. Document both
  cert options (Tailscale cert / DNS-challenge) in the file's comments.

### L4 API (FastAPI)
- `GET /api/health` — returns version + server time in `USER_TZ` (doubles
  as a timezone sanity check).
- `GET /api/push/vapid-public-key` — the PWA needs it to subscribe.
- `POST /api/push/subscriptions` — store a browser PushSubscription JSON
  (endpoint URL is the natural unique key; upsert on it).
- `DELETE /api/push/subscriptions` — by endpoint URL (user disables
  notifications).
- `POST /api/push/test` — immediately sends a test push to all
  subscriptions; dev/verification tool so nobody waits for cron.
- Internal `send_push(title, body, url)` helper using `pywebpush`; on a
  404/410 response from the push service, mark that subscription expired
  (don't delete — status flag per conventions).

### L5 Scheduler
- APScheduler started with the app. Two cron jobs from `MORNING_TIME` /
  `EVENING_TIME` in `USER_TZ`.
- Both call one `send_scheduled_notification(kind)` function
  (`kind ∈ {morning, evening}`); bodies are placeholder copy for now
  ("Good morning — time to plan the day", "Evening check-in time").
- **Extensibility note:** later bites make this function build content from
  DB state and add follow-up logic; keep it a single seam. Log every send
  attempt (see L6) — the bite-3 follow-up rule and future adaptive tone
  depend on that log existing.

### L6 Structured store
- SQLAlchemy + Alembic initialized; migration 0001 creates:
  - `push_subscription` — id, endpoint (unique), subscription_json,
    created_at, status (`active`/`expired`).
  - `notification_log` — id, kind, sent_at (UTC), title, body,
    subscription_id, result (`sent`/`failed`/`expired`).

### L2 Push transport
- Web Push with VAPID via `pywebpush`. Outbound-only: TheRig connects out
  to Apple's push service; no inbound exposure. Payload: JSON
  `{title, body, url}`; the service worker renders it.

### L1 Client (PWA)
- Vite + React + vite-plugin-pwa. One screen:
  - Install hint (iOS: Share → Add to Home Screen — permission is only
    grantable from the installed app).
  - "Enable notifications" button (iOS requires a user gesture) →
    `Notification.requestPermission()` → `pushManager.subscribe()` with the
    VAPID key → POST to the API. Show current status (subscribed / denied /
    unsupported) and a "Send test notification" button wired to
    `/api/push/test`.
- Service worker: `push` handler → `showNotification(title, {body, data})`;
  `notificationclick` handler → focus or open the app at `data.url`.
- **Extensibility note:** route by the `url` field from day one — bite 3
  deep-links pushes to the check-in screen through this exact path.

## iOS gotchas the implementer must respect
- Web Push works only from a home-screen-installed PWA (iOS 16.4+; target
  device is iOS 26 — fine), Safari-installed, secure context.
- `showNotification` is the only way to surface a push; silent pushes are
  not honored — every push must display a notification.
- Permission prompt must come from a user gesture inside the installed app.

## Definition of done
- [ ] `pytest` green: subscription upsert/delete, expiry marking, scheduler
      fires `send_scheduled_notification` at configured times (test with a
      fake clock, not real waiting), notification_log rows written.
- [ ] `docker compose up` on TheRig serves the PWA over valid HTTPS via the
      tailnet hostname.
- [ ] On the iPhone: install PWA → enable notifications → test push arrives
      with the app closed → tapping it opens the PWA.
- [ ] Scheduled morning and evening pushes observed on the lock screen at
      the configured times over at least one real day.
