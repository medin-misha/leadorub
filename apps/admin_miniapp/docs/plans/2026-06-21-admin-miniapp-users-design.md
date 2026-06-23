# Admin MiniApp — Users tab (design)

Date: 2026-06-21
Status: approved

## Goal

Build the `apps/admin_miniapp` Vue SPA admin panel for Leadorub. The architecture
must make it trivial to add new tabs. Four tabs ship initially: **Users**,
**Newsletter**, **Admin**, **Chat**. Only **Users** is fully implemented and wired
to the backend user CRUD API (search, update, delete; create included for CRUD
completeness). Newsletter / Admin / Chat are placeholders.

## Decisions (from brainstorming)

- **Plain SPA, no Telegram SDK** for now. A Telegram WebApp adapter + initData auth
  is explicitly out of scope (separate future task; backend does not validate
  initData yet).
- **Edit everything**: full CRUD on `TelegramUser` plus editing of nested
  `profile` and `stats` via their own endpoints.
- **Deploy now via Docker + compose + Caddy**: containerized, served by Caddy,
  registered in `infra/docker-compose.apps.yml`.

## Stack

Vue 3 (`<script setup>`) + Vite + Pinia + Vue Router + Axios. Lightweight custom
CSS on design tokens (CSS variables) — no heavy UI framework, so a Telegram theme
can later bind to the same variables.

## Backend contract (existing, unchanged)

Router prefix `/api/telegram`.

- `GET /users?page=&limit=&search=&field=` → `list[TelegramUserRead]` (no total count).
- `GET /users/{id}` → `TelegramUserRead`.
- `POST /users` → composite `TelegramUserRegister` `{ telegram_user, profile?, stats? }`.
- `PATCH /users/{id}` → `TelegramUserPatch`.
- `DELETE /users/{id}` → `{ "status": "ok" }`.
- `PATCH /profile/{id}`, `POST /profile` (`UserProfileCreate` needs `telegram_user_id`).
- `PATCH /stats/{id}`, `POST /stats` (`UserStatsCreate` needs `telegram_user_id`).

`TelegramUserRead` fields: `id`, `telegram_id`, `username`, `first_name`,
`last_name`, `is_blocket_bot` (DB spelling kept as-is), `language_code`,
`created_at`, `updated_at`, `user_profile` (nested), `user_stats` (nested).

Search semantics:
- `search` only → full-text contains across all string columns.
- `search` + `field` → search a specific column (string = contains; other types =
  exact, parsed by column type). `field=telegram_id` does exact match.

## Architecture

### Directory layout

```
apps/admin_miniapp/
├── Dockerfile             # multi-stage: node build → Caddy serves static
├── Caddyfile             # SPA fallback + reverse_proxy /api → backend:8000
├── .dockerignore
├── .gitignore
├── vite.config.js        # dev proxy /api → localhost:8000 (no CORS)
├── package.json
├── index.html
├── README.md             # Russian
├── docs/plans/           # this design doc
├── .claude/CLAUDE.md     # English module docs
└── src/
    ├── main.js
    ├── App.vue                  # layout: TabBar + <router-view>
    ├── router/index.js          # routes generated from the tab registry
    ├── tabs/index.js            # ⭐ TAB REGISTRY — single source of truth
    ├── api/{http,users,profiles,stats}.js
    ├── stores/users.js          # Pinia store
    ├── views/{Users,Newsletter,Admin,Chat}View.vue
    ├── components/
    │   ├── layout/TabBar.vue
    │   ├── users/{UsersTable,UserSearchBar,UserEditDialog,UserDeleteConfirm}.vue
    │   └── ui/{BaseButton,BaseModal,BaseInput,BaseSelect,Pagination,Placeholder}.vue
    └── styles/tokens.css
```

### Tab registry (extensibility core)

`src/tabs/index.js` exports an array of tab descriptors:

```js
export const tabs = [
  { key: 'users',      label: 'Users',      component: () => import('@/views/UsersView.vue') },
  { key: 'newsletter', label: 'Newsletter', component: () => import('@/views/NewsletterView.vue') },
  { key: 'admin',      label: 'Admin',      component: () => import('@/views/AdminView.vue') },
  { key: 'chat',       label: 'Chat',       component: () => import('@/views/ChatView.vue') },
]
```

- `TabBar.vue` renders navigation from `tabs`.
- `router/index.js` builds routes from the same array (`/` redirects to the first
  tab; each tab → `/{key}`; lazy-loaded component).
- Adding a tab = one entry in the registry + one view component.

### API layer & no-CORS strategy

- `api/http.js`: Axios instance, `baseURL: '/api'`.
- Dev: Vite dev-server proxies `/api` → `http://localhost:8000`.
- Prod: Caddy serves the SPA and reverse-proxies `/api/*` → `backend:8000`
  (same origin both ways → no CORS).
- `api/users.js`: `listUsers({page,limit,search,field})`, `getUser(id)`,
  `createUser(payload)`, `updateUser(id, patch)`, `deleteUser(id)`.
- `api/profiles.js` / `api/stats.js`: `patch(id, data)`, `create(data)`.

### Pinia store (`stores/users.js`)

State: `items`, `page`, `limit`, `search`, `field`, `loading`, `error`, `hasNext`.
Actions: `fetchUsers`, `updateUser`, `deleteUser`, `createUser`, `updateProfile`,
`updateStats`. `hasNext` is derived as "returned rows === limit" because the list
endpoint returns no total count.

### Users tab UI

- **Search** (`UserSearchBar`): text input (→ `search`) + field selector (→ `field`:
  All / telegram_id / username / first_name / last_name / language_code), ~300ms
  debounce. Changing search resets to page 1.
- **Table** (`UsersTable`): columns id, telegram_id, username, name, language,
  blocked flag, created_at, + Edit / Delete actions.
- **Pagination** (`Pagination`): prev / next + page size; next disabled when fewer
  than `limit` rows returned.
- **Edit** (`UserEditDialog`): form over `TelegramUser` fields + collapsible
  **Profile** and **Stats** sections (editable). Save sends PATCH `/users/{id}`
  and, when changed, PATCH `/profile/{id}` / `/stats/{id}`; if a nested entity is
  missing, POST it with `telegram_user_id`.
- **Delete** (`UserDeleteConfirm`): confirmation → DELETE `/users/{id}`.
- **Create**: form over the composite `POST /users` (telegram_user + optional
  profile/stats). Included for CRUD completeness.

### Error & loading handling

Store-level `loading` and `error`. API errors surface the backend `detail` message
(404/400/503/500 mapped by backend `DBErrorHandler`). Mutations refetch the current
page on success. Empty results show an empty-state.

### Docker + Caddy + compose

- **Dockerfile**: stage 1 `node:20-alpine` runs `npm ci && npm run build` → `/dist`;
  stage 2 `caddy:2-alpine` copies `dist` to `/srv` + the `Caddyfile`.
- **Caddyfile**: listens on `:80`; `try_files {path} /index.html` SPA fallback;
  `reverse_proxy /api/* backend:8000`. HTTP only for local; domain/TLS noted in a
  comment for production.
- **compose**: new `admin_miniapp` service in `infra/docker-compose.apps.yml` —
  build context `../apps/admin_miniapp`, `restart: unless-stopped`,
  `depends_on: backend`, network `leadorub`, port `8080:80`.

## Out of scope (YAGNI)

Telegram WebApp SDK & initData auth; real Newsletter/Admin/Chat functionality;
roles/permissions; frontend tests (unless requested); any backend changes.

## Known issue surfaced

The user CRUD endpoints have **no authorization**. Serving the admin via Caddy
exposes user management to anyone who can reach it. Acceptable for this local-only
stage; the follow-up task is backend initData validation + an auth gate.

## Documentation deliverables

After implementation, sync `apps/admin_miniapp/.claude/CLAUDE.md` (English) and
`apps/admin_miniapp/README.md` (Russian) per project rules.
