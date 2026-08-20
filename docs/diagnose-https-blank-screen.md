# AcctBud diagnostic: HTTPS + blank screen (resolved)

Written 2026-08-20 during debugging. All issues resolved — kept as a
reference for the serving architecture and the specific pitfalls we hit.

## Serving chain

```
Browser → Tailscale Serve (HTTPS, port 443) → Caddy (HTTP, port 8081) → backend (port 8000)
```

- Tailscale Serve terminates TLS and proxies `/acctbud` to `http://localhost:8081`
- **Tailscale Serve strips the mount path** — a request to `/acctbud/api/tasks`
  arrives at Caddy as `/api/tasks`
- Caddy runs in Docker, listening on container port 8080 (mapped to host 8081)
- The PWA is built with Vite `base: "/acctbud/"` — all asset paths in the HTML
  start with `/acctbud/`, which the browser sends through Tailscale, which strips
  the prefix, which Caddy serves from `/srv/pwa/`

## Root causes found

### 1. Tailscale Serve strips the path prefix (HTTPS broken)

`tailscale serve /acctbud http://localhost:8081` strips `/acctbud` before
forwarding. The original Caddyfile used `handle_path /acctbud/*`, which
never matched because the prefix was already gone.

**Fix:** Removed `handle_path /acctbud/*` — Caddy now handles paths at
the root since Tailscale already strips the prefix.

### 2. Caddy directive ordering (API calls returning HTML)

The original Caddyfile had `try_files`, `file_server`, and
`handle /api/*` at the same level inside `handle_path`. Caddy applies
directives in its built-in order (not file order):
`root` → `try_files` → `file_server` → `handle`. This meant
`try_files` rewrote `/api/tasks` to `/index.html` before the API proxy
ever ran.

**Fix:** Mutually exclusive `handle` blocks:

```caddyfile
:8080 {
    handle /api/* {
        reverse_proxy backend:8000
    }

    handle {
        root * /srv/pwa
        try_files {path} /index.html
        file_server
    }
}
```

### 3. React Router v7 basename trailing slash (blank screen)

`BrowserRouter basename="/acctbud/"` (with trailing slash, from Vite's
`BASE_URL`) caused React Router v7 to fail route matching. Unlike v6,
v7 does not normalize a trailing slash on the basename.

**Fix:** Strip the trailing slash before passing to the router:

```tsx
const basename = import.meta.env.BASE_URL.replace(/\/+$/, "");
<BrowserRouter basename={basename}>
```

### 4. Docker containers not running

The containers weren't started. Without Caddy on port 8081, Tailscale
Serve had nothing to proxy to.

**Fix:** `docker compose up -d --build` from `deploy/`.

## Key gotchas for future reference

- **Tailscale Serve always strips the mount path.** If you configure
  `/foo → http://localhost:PORT`, the backend receives requests without
  `/foo`. Don't double-strip in Caddy with `handle_path`.
- **Caddy directive ordering is not file ordering.** Use `handle` blocks
  for mutual exclusion when mixing `try_files`/`file_server` with
  `reverse_proxy`.
- **React Router v7 basename must not have a trailing slash.** Vite's
  `BASE_URL` always includes one; strip it.
- **Service workers on iOS Safari are persistent.** Clear site data via
  Settings → Apps → Safari → Advanced → Website Data if a stale SW is
  serving broken content. Private tabs on iOS do not bypass a registered SW.
- **An ErrorBoundary in main.tsx** now surfaces React crashes as visible
  red text, useful for debugging on mobile where DevTools aren't available.

## Diagnostic curl commands (still useful)

```bash
# Verify full chain over HTTPS
curl -s https://therig.tailab0bb6.ts.net/acctbud/ | head -5
curl -s https://therig.tailab0bb6.ts.net/acctbud/api/tasks
curl -s -o /dev/null -w '%{http_code}' https://therig.tailab0bb6.ts.net/acctbud/checkin/today

# Verify Caddy directly (bypass Tailscale)
curl -s http://localhost:8081/ | head -5
curl -s http://localhost:8081/api/tasks
```
