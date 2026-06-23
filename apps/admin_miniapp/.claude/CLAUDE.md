# Admin MiniApp — module guide (for AI agents)

Vue 3 SPA admin panel for Leadorub. Currently a plain browser SPA (no Telegram
WebApp SDK / initData — explicitly out of scope). The architecture is built so
adding a tab is a one-line change.

## Stack

Vue 3 (`<script setup>`) + Vite + Vue Router + Pinia + Axios. Served in production
by Caddy (static files + `/api` reverse proxy). Lightweight custom CSS on design
tokens (`src/styles/tokens.css`) — no UI framework, so a Telegram theme can later
bind to the same CSS variables.

## Code conventions

- Code comments are written in **Russian** (this module's established style).
- Keep the DB field spelling `is_blocket_bot` verbatim everywhere (it is a backend
  typo for `is_blocked_bot`, but the API uses this spelling — do not "fix" it here).
- API base URL is `/api` in every environment. Never hardcode host/port: in dev the
  Vite proxy forwards `/api` → backend; in prod Caddy reverse-proxies it. Same origin
  both ways → no CORS.

## Architecture

### Tab registry (single source of truth)

`src/tabs/index.js` exports `tabs = [{ key, label, component }]`. It drives BOTH:
- the nav bar (`src/components/layout/TabBar.vue`), and
- the routes (`src/router/index.js`, which maps each tab to `/{key}` with a
  lazy-loaded component; `/` redirects to the first tab).

**To add a tab:** create a `views/XView.vue` and add one entry to the registry.
Nothing else changes.

### Layers

- `src/api/` — Axios layer. `http.js` exports the configured instance + `extractError`
  (pulls the backend `detail` message). `users.js` / `profiles.js` / `stats.js` wrap
  the endpoints. Keep raw HTTP here, not in components/stores.
- `src/stores/users.js` — Pinia store for the Users tab. Holds list + pagination +
  search state and exposes actions (`fetchUsers`, `setSearch`, `setPage`, `setLimit`,
  `createUser`, `updateUser`, `deleteUser`, `createProfile`/`updateProfile`,
  `createStats`/`updateStats`).
- `src/components/ui/` — reusable primitives (`BaseButton`, `BaseInput`, `BaseSelect`,
  `BaseModal`, `Pagination`, `Placeholder`).
- `src/components/users/` — Users-tab feature components (search bar, table, edit /
  delete / create dialogs).
- `src/views/` — one view per tab.

## Backend contract consumed (unchanged)

Router prefix `/api/telegram`:

- `GET /users?page=&limit=&search=&field=` → `TelegramUserRead[]` (no total count).
- `GET /users/{id}`, `POST /users` (composite `{ telegram_user, profile?, stats? }`),
  `PATCH /users/{id}`, `DELETE /users/{id}` → `{ status }`.
- `PATCH /profile/{id}`, `POST /profile` (needs `telegram_user_id`).
- `PATCH /stats/{id}`, `POST /stats` (needs `telegram_user_id`).

Search semantics: `search` alone = full-text contains over string columns; `search`
+ `field` = that column only (string = contains, others = exact, parsed by type).

**Pagination note:** the list endpoint returns no total, so the store derives
`hasNext` as `items.length === limit`. There is no exact page count by design.

`TelegramUserRead` includes nested `user_profile` and `user_stats`. When editing,
the edit dialog PATCHes the nested entity if it has an `id`, otherwise POSTs it with
`telegram_user_id`.

## Newsletter tab

Compose a broadcast (text + one optional attachment) and pick an audience.

- `views/NewsletterView.vue` — two columns: `AudiencePanel` (left) + `MessageComposer`
  (right), plus `NewsletterConfirmDialog`.
- `components/newsletter/` — `AudiencePanel` (radio `all`/`filter`; reuses
  `UserSearchBar` for the filter inputs), `MessageComposer` (textarea + `BaseFileInput`
  + `KeyboardEditor` + send), `KeyboardEditor` (inline/reply toggle + per-button rows),
  `NewsletterConfirmDialog` (`BaseModal` summary).
- `components/ui/BaseFileInput.vue` — single-file `v-model` picker (name, size, image
  preview, remove).
- `stores/newsletter.js` — Pinia store: `audience {mode,search,field}`, `text`, `file`,
  `keyboard {type,buttons}`, `sending`, `error`, `result`; getters `canSend`,
  `audienceLabel`, `keyboardLabel`, `keyboardValid`, `keyboardError`, `canAddButton`;
  actions `setAudience`/`setText`/`setFile`/`setKeyboardType`/`addButton`/`updateButton`/
  `removeButton`/`send`/`reset`.
- `api/newsletter.js` — `newsletterApi.send(formData)` POSTs `multipart/form-data` to
  `POST /telegram/newsletter`: a single `payload` field (JSON body) + optional `file`.
  Returns `{status, recipients}`.

### Message keyboard (buttons)

`KeyboardEditor` builds an optional message keyboard mirroring Telegram semantics:

- `keyboard.type`: `'inline' | 'reply'`. Each button: `{text, url, callback_data}`
  (reply uses `text` only).
- **Inline** requires `text` + exactly one of `url` / `callback_data` — the two inputs
  are mutually exclusive (typing in one hides the other). **Reply** needs only `text`.
- Vertical list: one button per row; `+` appends a row, disabled until the last button
  is valid (`canAddButton`). Send is blocked while `!keyboardValid` (error shown via
  `keyboardError`).
- **Payload contract:** `store.send()` serializes the whole body into one `payload` JSON
  field: `{filters:{search,field}, text, use_buttons:"INLINE"|"REPLY"|null, buttons|null}`.
  `keyboard.type` maps to `use_buttons` (uppercased); buttons become a flat list. Per
  inline button only the filled key (`url` **or** `callback_data`) is serialized; one
  button = one row backend-side. No buttons → `use_buttons` and `buttons` are `null`.

**Backend wired:** `store.send()` calls `newsletterApi.send(form)` against the real
`POST /telegram/newsletter`. On success the store keeps `{status, recipients}` and the
view shows the recipient count; backend errors (e.g. 404 "no recipients", 400 "no
content") surface via `extractError` as `store.error`.

## Run

- **Dev:** `npm install && npm run dev` (needs backend on :8000; `VITE_API_PROXY_TARGET`
  overrides the proxy target).
- **Docker:** service `admin_miniapp` in `infra/docker-compose.apps.yml`; built via the
  multi-stage `Dockerfile` (node build → `caddy:2-alpine`); published on host `:8080`.
  `Caddyfile` listens on `:80`, SPA-fallback to `index.html`, proxies `/api/*` to
  `backend:8000`. For prod, replace `:80` with a domain to get automatic TLS.

## Out of scope

Telegram WebApp SDK & initData auth; Admin/Chat functionality;
roles/permissions; frontend test framework; any backend changes.

## Known issue

The consumed CRUD endpoints have **no authorization**. Serving this admin exposes
user management to anyone who can reach it. Acceptable only for the local stage; the
follow-up is backend initData validation + an auth gate before any public deploy.
