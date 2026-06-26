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
- The message textarea is capped at `MESSAGE_MAX_LENGTH` (1024, from `src/constants.js`) with
  a live counter. This is Telegram's caption limit: when a file is attached the text is sent
  as a caption, and exceeding 1024 makes the bot's send fail silently. The Chat composer uses
  the same constant.
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
- **Inline field validation** (in `stores/newsletter.js`, enforced by `isButtonValid` /
  `keyboardError`, so it blocks both `+ Добавить кнопку` and Send): `url` must parse via
  the `URL` constructor with an `http:` / `https:` / `tg:` scheme (matches Bot API
  `InlineKeyboardButton.url`); for `http(s)` the host must also be a real domain — a dot
  with a ≥2-char TLD (or an IPv4) — because `new URL()` accepts single-label hosts like
  `https://asdasd` that Telegram then rejects with `Wrong HTTP URL`. `callback_data` must
  be ≤ `CALLBACK_DATA_MAX_BYTES` (64,
  from `src/constants.js`) measured in **UTF-8 bytes** (`TextEncoder`), not characters —
  the field also carries a soft `maxlength=64`. This is frontend-only; the backend does
  not yet re-check URL format or callback_data length.
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

## Auth (JWT)

The app is gated behind admin login. Backend issues a single access JWT (no refresh).

- `api/http.js` — request interceptor injects `Authorization: Bearer <token>` from
  `localStorage['admin_token']`; response interceptor calls a runtime-registered handler
  on `401` (set in `main.js`) → `auth.logout()` + redirect to `/login`. The handler is
  registered at runtime (not imported) so `http.js` stays free of store/router cycles.
- `api/auth.js` — `login`, `me`, and admins CRUD (`listAdmins`/`createAdmin`/`updateAdmin`/`removeAdmin`).
- `stores/auth.js` — `token` (persisted in `localStorage`), `admin` (from `/auth/me`),
  getter `isAuthenticated`; actions `login`/`fetchMe`/`logout`.
- `router/index.js` — `/login` is `meta.public`; a global `beforeEach` redirects
  unauthenticated users to `/login?redirect=...` and bounces logged-in users away from `/login`.
- `views/LoginView.vue` — username/password form. `App.vue` shows the current admin +
  "Выйти" and hides the tab bar until authenticated. `main.js` registers the 401 handler
  and calls `fetchMe()` on boot if a token exists (validates it).

Backend endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `GET/POST /api/auth/admins`,
`PATCH/DELETE /api/auth/admins/{id}`.

### Admin tab

`views/AdminView.vue` manages administrators: list (paginated), create, change password,
toggle `is_active`, delete. Actions on your own account (deactivate/delete) are disabled
in the UI and rejected by the backend (prevents self-lockout).

## Chat tab

Two-way support chat. A bot user types `/support` and their messages reach the backend;
the admin sees conversations here and replies on behalf of the bot.

- `views/ChatView.vue` — two panes: `ConversationList` (left) + active thread
  (`ChatThread` + `ChatComposer`) on the right. `onMounted` starts polling;
  `onUnmounted` stops ALL intervals (leak-free).
- `components/chat/` — `ConversationList` (unread badge + last-message preview, `📎 Вложение`
  for media), `ChatThread` (auto-scroll to bottom), `MessageBubble` (admin right / user
  left), `ChatComposer` (textarea + `BaseFileInput`, Enter to send, Shift+Enter newline),
  `MediaAttachment` (fetches the attachment as a blob via `GET /files/{id}` so the auth
  header is sent, then shows an image preview or a download link). The `isImage` regex
  intentionally excludes `.svg`: an SVG opened as a top-level document can run an embedded
  `<script>` in the panel's origin (Stored XSS), so SVGs fall through to the download link
  instead of being rendered. The backend also serves SVGs as `application/octet-stream`
  with `nosniff` (defense-in-depth).
- `stores/chat.js` — Pinia store: `conversations`, `activeUid`, `messages`, `search`;
  actions `fetchConversations`/`setSearch`/`openConversation`/`fetchMessages`/
  `sendReply(text, file)`/`markRead` and the polling lifecycle (`startListPolling`/
  `startThreadPolling`/`stopAllPolling`). **Polling:** open thread every ~4 s (incremental
  `after_id` fetch with id dedupe + `_inFlight` guard), conversation list every ~10 s.
  Switching conversation stops the previous thread interval first.
- `api/chat.js` — `listConversations`, `getMessages(uid,{after_id,limit})`,
  `reply(uid,{text,file})` (multipart), `markRead(uid)`, `fileObjectUrl(fileId)` against
  `/api/chat/*` (`require_admin`).

Media in the support chat = photos & documents (≤10 MB); the bot uploads inbound media to
the backend over HTTP. Real-time is polling by design (no WebSocket/SSE infra). See the
end-to-end design in `docs/specs/2026-06-23-support-chat-design.md`.

## Out of scope

Telegram WebApp SDK & initData auth; roles/permissions (all admins are equal);
frontend test framework.
