# Client MiniApp — Claude Code Context

## Purpose and stack

Vue 3 + Vite Telegram WebApp that collects consultation data and submits it to
the backend. Production Caddy serves the SPA and proxies only the exact public
requisition endpoint.

## Security contract

- `window.Telegram.WebApp.initDataUnsafe` may be used for display only.
- Identity is proven by raw `window.Telegram.WebApp.initData`, sent in the
  `X-Telegram-Init-Data` header to `POST /api/requisitions/public`.
- Do not send `telegram_id` in the request body and never add `SERVICE_TOKEN` to
  the public proxy.
- Client-side validation is UX only. Backend schemas, signed initData validation,
  and rate limiting remain authoritative.
- Caddy must return 404 for every other `/api/*` route on this origin.

## Local checks

```bash
npm ci
npm run build
```

The app currently has no separate lint or unit-test dependency. Do not manually
edit `package-lock.json`; dependency changes must keep `npm ci` reproducible.

## Change rules

- Preserve the established Russian code-comment style.
- Keep API paths relative (`/api/...`) and do not hardcode backend hosts.
- When the request contract changes, update this file, the backend requisition
  module documentation, and the Russian README relevant to the user flow.
