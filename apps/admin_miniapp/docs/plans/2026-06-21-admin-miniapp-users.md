# Admin MiniApp — Users tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `apps/admin_miniapp` Vue 3 SPA admin panel with an extensible tab system; fully implement the Users tab against the backend telegram CRUD API (search, update, delete, create incl. nested profile/stats), and ship it via Docker + Caddy + compose.

**Architecture:** Vite + Vue 3 (`<script setup>`) + Vue Router + Pinia + Axios. A single tab *registry* drives both the nav bar and the router routes — adding a tab is one entry + one view. The API is reached at same-origin `/api` (Vite dev proxy in dev, Caddy reverse proxy in prod), so there is no CORS. Caddy serves the built static SPA and proxies `/api/*` to the backend.

**Tech Stack:** Vue 3, Vite 5, Vue Router 4, Pinia 2, Axios, Caddy 2, Node 20 (build), Docker.

## Global Constraints

- Plain SPA only — **no** Telegram WebApp SDK / initData (out of scope).
- Backend is **unchanged**; consume `/api/telegram/*` as-is.
- List endpoint returns **no total count** → pagination via "returned rows === limit".
- Keep the DB field spelling `is_blocket_bot` verbatim in payloads/columns.
- API base URL is `/api` in all environments (dev proxy + prod Caddy).
- No frontend unit-test framework (spec scoped it out); verification = build + dev/run checks.
- Comments in code: Russian (project style for new module is fine in Russian).
- Docs: `README.md` Russian, `.claude/CLAUDE.md` English.
- Commits are **deferred** — do not `git commit` during execution; batch at the end and only on the user's request. (Plan keeps a "Commit" note per task for completeness.)

---

### Task 1: Vite project scaffold + base config

**Files:**
- Create: `apps/admin_miniapp/package.json`
- Create: `apps/admin_miniapp/vite.config.js`
- Create: `apps/admin_miniapp/index.html`
- Create: `apps/admin_miniapp/.gitignore`
- Create: `apps/admin_miniapp/.env.example`
- Create: `apps/admin_miniapp/src/main.js`
- Create: `apps/admin_miniapp/src/App.vue` (temporary minimal; replaced in Task 2)
- Create: `apps/admin_miniapp/src/styles/tokens.css`

**Interfaces:**
- Produces: a buildable Vite app; `@` alias → `src/`; dev proxy `/api` → `http://localhost:8000`.

- [ ] **Step 1: package.json**

```json
{
  "name": "admin_miniapp",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "pinia": "^2.2.4",
    "vue": "^3.5.12",
    "vue-router": "^4.4.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "vite": "^5.4.10"
  }
}
```

- [ ] **Step 2: vite.config.js**

```js
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev-proxy: запросы фронта на /api уходят на backend (localhost:8000).
// Так в браузере один origin (Vite) → нет CORS. В проде то же делает Caddy.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: index.html**

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Leadorub — Admin</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: .gitignore**

```gitignore
node_modules/
dist/
.env
.env.local
*.log
.DS_Store
```

- [ ] **Step 5: .env.example**

```dotenv
# Цель dev-прокси Vite для /api (по умолчанию http://localhost:8000).
# В docker/Caddy не используется — там /api проксирует Caddy.
VITE_API_PROXY_TARGET=http://localhost:8000
```

- [ ] **Step 6: src/styles/tokens.css**

```css
/* Дизайн-токены: единые CSS-переменные. На них позже можно повесить тему Telegram. */
:root {
  --color-bg: #f5f6f8;
  --color-surface: #ffffff;
  --color-border: #e3e6ea;
  --color-text: #1c1e21;
  --color-text-muted: #6b7280;
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-danger: #dc2626;
  --color-danger-hover: #b91c1c;
  --radius: 8px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: var(--font);
  color: var(--color-text);
  background: var(--color-bg);
}
</style>
```
(Note: the file is `.css`, ignore the stray closing tag — write only the CSS above.)

- [ ] **Step 7: src/main.js**

```js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import App from '@/App.vue'
import '@/styles/tokens.css'

createApp(App).use(createPinia()).use(router).mount('#app')
```

- [ ] **Step 8: src/App.vue (temporary minimal)**

```vue
<script setup></script>
<template>
  <div>scaffold ok</div>
</template>
```

- [ ] **Step 9: Install & verify build**

Run:
```bash
cd apps/admin_miniapp && npm install && npm run build
```
Expected: `npm install` resolves; `npm run build` writes `dist/` with no errors. (`main.js` imports `@/router` which does not exist yet — so do NOT run `npm run build` until Task 2 creates the router. Reorder: in this task, only run `npm install`; defer `npm run build` to Task 2 Step verify.)

- [ ] **Step 10: Commit (deferred — see Global Constraints)**

```bash
# git add apps/admin_miniapp/{package.json,vite.config.js,index.html,.gitignore,.env.example,src}
# git commit -m "feat(admin_miniapp): vite scaffold"
```

---

### Task 2: Tab registry + router + layout + placeholder views

**Files:**
- Create: `apps/admin_miniapp/src/tabs/index.js`
- Create: `apps/admin_miniapp/src/router/index.js`
- Create: `apps/admin_miniapp/src/components/layout/TabBar.vue`
- Create: `apps/admin_miniapp/src/components/ui/Placeholder.vue`
- Create: `apps/admin_miniapp/src/views/UsersView.vue` (stub; filled in Tasks 6–7)
- Create: `apps/admin_miniapp/src/views/NewsletterView.vue`
- Create: `apps/admin_miniapp/src/views/AdminView.vue`
- Create: `apps/admin_miniapp/src/views/ChatView.vue`
- Modify: `apps/admin_miniapp/src/App.vue`

**Interfaces:**
- Produces: `tabs` array `[{ key, label, component }]`; default router export; `/` → first tab; each tab at `/{key}`.
- Consumes: Vite `@` alias, Pinia/router from `main.js`.

- [ ] **Step 1: src/tabs/index.js**

```js
// ⭐ Реестр вкладок — единственный источник правды.
// Добавить вкладку = добавить сюда объект + создать view-компонент.
export const tabs = [
  { key: 'users', label: 'Users', component: () => import('@/views/UsersView.vue') },
  { key: 'newsletter', label: 'Newsletter', component: () => import('@/views/NewsletterView.vue') },
  { key: 'admin', label: 'Admin', component: () => import('@/views/AdminView.vue') },
  { key: 'chat', label: 'Chat', component: () => import('@/views/ChatView.vue') },
]
```

- [ ] **Step 2: src/router/index.js**

```js
import { createRouter, createWebHistory } from 'vue-router'
import { tabs } from '@/tabs'

// Роуты строятся из реестра вкладок: /{key} → lazy-компонент вкладки.
const routes = [
  { path: '/', redirect: `/${tabs[0].key}` },
  ...tabs.map((tab) => ({
    path: `/${tab.key}`,
    name: tab.key,
    component: tab.component,
  })),
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 3: src/components/layout/TabBar.vue**

```vue
<script setup>
import { tabs } from '@/tabs'
</script>

<template>
  <nav class="tabbar">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.key"
      :to="`/${tab.key}`"
      class="tabbar__item"
      active-class="tabbar__item--active"
    >
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.tabbar__item {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--color-text-muted);
  font-weight: 500;
}
.tabbar__item--active {
  background: var(--color-primary);
  color: #fff;
}
</style>
```

- [ ] **Step 4: src/components/ui/Placeholder.vue**

```vue
<script setup>
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <div class="placeholder">
    <h2>{{ title }}</h2>
    <p>Раздел в разработке.</p>
  </div>
</template>

<style scoped>
.placeholder {
  padding: var(--space-5);
  text-align: center;
  color: var(--color-text-muted);
}
</style>
```

- [ ] **Step 5: Placeholder views (Newsletter / Admin / Chat)**

`src/views/NewsletterView.vue`:
```vue
<script setup>
import Placeholder from '@/components/ui/Placeholder.vue'
</script>
<template><Placeholder title="Newsletter" /></template>
```

`src/views/AdminView.vue`:
```vue
<script setup>
import Placeholder from '@/components/ui/Placeholder.vue'
</script>
<template><Placeholder title="Admin" /></template>
```

`src/views/ChatView.vue`:
```vue
<script setup>
import Placeholder from '@/components/ui/Placeholder.vue'
</script>
<template><Placeholder title="Chat" /></template>
```

- [ ] **Step 6: src/views/UsersView.vue (stub)**

```vue
<script setup>
// Наполняется в Tasks 6–7.
</script>
<template>
  <div class="users">Users</div>
</template>
<style scoped>
.users { padding: var(--space-4); }
</style>
```

- [ ] **Step 7: src/App.vue (final layout)**

```vue
<script setup>
import TabBar from '@/components/layout/TabBar.vue'
</script>

<template>
  <div class="app">
    <header class="app__header">
      <span class="app__brand">Leadorub Admin</span>
    </header>
    <TabBar />
    <main class="app__main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app { min-height: 100vh; display: flex; flex-direction: column; }
.app__header {
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  font-weight: 700;
}
.app__main { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: var(--space-4); }
</style>
```

- [ ] **Step 8: Verify build + dev**

Run:
```bash
cd apps/admin_miniapp && npm run build
```
Expected: build succeeds, `dist/` produced.

Run:
```bash
cd apps/admin_miniapp && npm run dev
```
Expected: open http://localhost:5173 → 4 tabs visible; clicking changes URL to `/users`, `/newsletter`, etc.; placeholders render.

- [ ] **Step 9: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): tab registry, router, layout, placeholders"
```

---

### Task 3: API layer (http + users + profiles + stats)

**Files:**
- Create: `apps/admin_miniapp/src/api/http.js`
- Create: `apps/admin_miniapp/src/api/users.js`
- Create: `apps/admin_miniapp/src/api/profiles.js`
- Create: `apps/admin_miniapp/src/api/stats.js`

**Interfaces:**
- Produces:
  - `http` — Axios instance (`baseURL '/api'`).
  - `usersApi.list({ page, limit, search, field })` → `Promise<TelegramUserRead[]>`
  - `usersApi.get(id)` → `Promise<TelegramUserRead>`
  - `usersApi.create(payload)` → `Promise<TelegramUserRead>` (payload = `{ telegram_user, profile?, stats? }`)
  - `usersApi.update(id, patch)` → `Promise<TelegramUserRead>`
  - `usersApi.remove(id)` → `Promise<{ status: string }>`
  - `profilesApi.create(data)`, `profilesApi.patch(id, data)`
  - `statsApi.create(data)`, `statsApi.patch(id, data)`

- [ ] **Step 1: src/api/http.js**

```js
import axios from 'axios'

// Один origin: в dev проксирует Vite, в проде — Caddy. Поэтому baseURL = /api.
export const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Достаём человекочитаемое сообщение из ответа backend (DBErrorHandler шлёт detail).
export function extractError(err) {
  return (
    err?.response?.data?.detail ||
    err?.message ||
    'Неизвестная ошибка'
  )
}
```

- [ ] **Step 2: src/api/users.js**

```js
import { http } from '@/api/http'

const BASE = '/telegram/users'

export const usersApi = {
  list({ page = 1, limit = 10, search = null, field = null } = {}) {
    const params = { page, limit }
    if (search) params.search = search
    if (field) params.field = field
    return http.get(BASE, { params }).then((r) => r.data)
  },
  get(id) {
    return http.get(`${BASE}/${id}`).then((r) => r.data)
  },
  create(payload) {
    return http.post(BASE, payload).then((r) => r.data)
  },
  update(id, patch) {
    return http.patch(`${BASE}/${id}`, patch).then((r) => r.data)
  },
  remove(id) {
    return http.delete(`${BASE}/${id}`).then((r) => r.data)
  },
}
```

- [ ] **Step 3: src/api/profiles.js**

```js
import { http } from '@/api/http'

const BASE = '/telegram/profile'

export const profilesApi = {
  create(data) {
    return http.post(BASE, data).then((r) => r.data)
  },
  patch(id, data) {
    return http.patch(`${BASE}/${id}`, data).then((r) => r.data)
  },
}
```

- [ ] **Step 4: src/api/stats.js**

```js
import { http } from '@/api/http'

const BASE = '/telegram/stats'

export const statsApi = {
  create(data) {
    return http.post(BASE, data).then((r) => r.data)
  },
  patch(id, data) {
    return http.patch(`${BASE}/${id}`, data).then((r) => r.data)
  },
}
```

- [ ] **Step 5: Verify build**

Run: `cd apps/admin_miniapp && npm run build`
Expected: build succeeds (modules import cleanly).

- [ ] **Step 6: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): api layer (users/profiles/stats)"
```

---

### Task 4: Pinia users store

**Files:**
- Create: `apps/admin_miniapp/src/stores/users.js`

**Interfaces:**
- Consumes: `usersApi`, `profilesApi`, `statsApi`, `extractError`.
- Produces: `useUsersStore()` with
  - state: `items`, `page`, `limit`, `search`, `field`, `loading`, `error`, `hasNext`
  - actions: `fetchUsers()`, `setSearch({ search, field })`, `setPage(page)`, `setLimit(limit)`, `createUser(payload)`, `updateUser(id, patch)`, `deleteUser(id)`, `updateProfile(id, data)`, `createProfile(data)`, `updateStats(id, data)`, `createStats(data)`

- [ ] **Step 1: src/stores/users.js**

```js
import { defineStore } from 'pinia'
import { usersApi } from '@/api/users'
import { profilesApi } from '@/api/profiles'
import { statsApi } from '@/api/stats'
import { extractError } from '@/api/http'

export const useUsersStore = defineStore('users', {
  state: () => ({
    items: [],
    page: 1,
    limit: 10,
    search: '',
    field: '', // '' = полнотекстовый поиск по всем строковым полям
    loading: false,
    error: null,
    hasNext: false,
  }),

  actions: {
    async fetchUsers() {
      this.loading = true
      this.error = null
      try {
        const items = await usersApi.list({
          page: this.page,
          limit: this.limit,
          search: this.search || null,
          field: this.field || null,
        })
        this.items = items
        // total бэкенд не отдаёт → "есть следующая страница" = пришла полная страница.
        this.hasNext = items.length === this.limit
      } catch (err) {
        this.error = extractError(err)
        this.items = []
        this.hasNext = false
      } finally {
        this.loading = false
      }
    },

    async setSearch({ search, field }) {
      this.search = search ?? ''
      this.field = field ?? ''
      this.page = 1 // новый запрос — всегда с первой страницы
      await this.fetchUsers()
    },

    async setPage(page) {
      this.page = Math.max(1, page)
      await this.fetchUsers()
    },

    async setLimit(limit) {
      this.limit = Math.max(1, limit)
      this.page = 1
      await this.fetchUsers()
    },

    async createUser(payload) {
      await usersApi.create(payload)
      await this.fetchUsers()
    },

    async updateUser(id, patch) {
      await usersApi.update(id, patch)
    },

    async deleteUser(id) {
      await usersApi.remove(id)
      await this.fetchUsers()
    },

    createProfile(data) {
      return profilesApi.create(data)
    },
    updateProfile(id, data) {
      return profilesApi.patch(id, data)
    },
    createStats(data) {
      return statsApi.create(data)
    },
    updateStats(id, data) {
      return statsApi.patch(id, data)
    },
  },
})
```

- [ ] **Step 2: Verify build**

Run: `cd apps/admin_miniapp && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): pinia users store"
```

---

### Task 5: UI base components

**Files:**
- Create: `apps/admin_miniapp/src/components/ui/BaseButton.vue`
- Create: `apps/admin_miniapp/src/components/ui/BaseInput.vue`
- Create: `apps/admin_miniapp/src/components/ui/BaseSelect.vue`
- Create: `apps/admin_miniapp/src/components/ui/BaseModal.vue`
- Create: `apps/admin_miniapp/src/components/ui/Pagination.vue`

**Interfaces:**
- `BaseButton` props: `variant` ('primary'|'danger'|'ghost', default 'primary'), `type`, `disabled`; emits native click.
- `BaseInput` props: `modelValue`, `placeholder`, `type`, `label`; emits `update:modelValue`.
- `BaseSelect` props: `modelValue`, `options` (`[{ value, label }]`), `label`; emits `update:modelValue`.
- `BaseModal` props: `title`; slots: default, `footer`; emits `close`.
- `Pagination` props: `page`, `hasNext`, `limit`, `limitOptions`; emits `update:page`, `update:limit`.

- [ ] **Step 1: BaseButton.vue**

```vue
<script setup>
defineProps({
  variant: { type: String, default: 'primary' },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
})
</script>

<template>
  <button :type="type" :disabled="disabled" :class="['btn', `btn--${variant}`]">
    <slot />
  </button>
</template>

<style scoped>
.btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius);
  font-weight: 500;
  cursor: pointer;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--primary { background: var(--color-primary); color: #fff; }
.btn--primary:hover:not(:disabled) { background: var(--color-primary-hover); }
.btn--danger { background: var(--color-danger); color: #fff; }
.btn--danger:hover:not(:disabled) { background: var(--color-danger-hover); }
.btn--ghost { background: transparent; color: var(--color-text); border-color: var(--color-border); }
.btn--ghost:hover:not(:disabled) { background: var(--color-bg); }
</style>
```

- [ ] **Step 2: BaseInput.vue**

```vue
<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  label: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field__label">{{ label }}</span>
    <input
      class="field__input"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </label>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: var(--space-1); }
.field__label { font-size: 13px; color: var(--color-text-muted); }
.field__input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
}
.field__input:focus { outline: none; border-color: var(--color-primary); }
</style>
```

- [ ] **Step 3: BaseSelect.vue**

```vue
<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] }, // [{ value, label }]
  label: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field__label">{{ label }}</span>
    <select
      class="field__input"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-for="opt in options" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: var(--space-1); }
.field__label { font-size: 13px; color: var(--color-text-muted); }
.field__input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
  background: var(--color-surface);
}
.field__input:focus { outline: none; border-color: var(--color-primary); }
</style>
```

- [ ] **Step 4: BaseModal.vue**

```vue
<script setup>
defineProps({ title: { type: String, default: '' } })
defineEmits(['close'])
</script>

<template>
  <div class="modal__overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog">
      <header class="modal__header">
        <h3 class="modal__title">{{ title }}</h3>
        <button class="modal__close" @click="$emit('close')">×</button>
      </header>
      <div class="modal__body"><slot /></div>
      <footer class="modal__footer"><slot name="footer" /></footer>
    </div>
  </div>
</template>

<style scoped>
.modal__overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center; padding: var(--space-4); z-index: 50;
}
.modal {
  background: var(--color-surface); border-radius: var(--radius); box-shadow: var(--shadow);
  width: 100%; max-width: 560px; max-height: 90vh; display: flex; flex-direction: column;
}
.modal__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-border);
}
.modal__title { margin: 0; font-size: 16px; }
.modal__close { border: none; background: none; font-size: 22px; cursor: pointer; color: var(--color-text-muted); }
.modal__body { padding: var(--space-4); overflow-y: auto; }
.modal__footer {
  display: flex; justify-content: flex-end; gap: var(--space-2);
  padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-border);
}
</style>
```

- [ ] **Step 5: Pagination.vue**

```vue
<script setup>
defineProps({
  page: { type: Number, required: true },
  hasNext: { type: Boolean, default: false },
  limit: { type: Number, default: 10 },
  limitOptions: { type: Array, default: () => [10, 20, 50] },
})
defineEmits(['update:page', 'update:limit'])
</script>

<template>
  <div class="pager">
    <button class="pager__btn" :disabled="page <= 1" @click="$emit('update:page', page - 1)">←</button>
    <span class="pager__page">Стр. {{ page }}</span>
    <button class="pager__btn" :disabled="!hasNext" @click="$emit('update:page', page + 1)">→</button>
    <select
      class="pager__limit"
      :value="limit"
      @change="$emit('update:limit', Number($event.target.value))"
    >
      <option v-for="opt in limitOptions" :key="opt" :value="opt">{{ opt }} / стр.</option>
    </select>
  </div>
</template>

<style scoped>
.pager { display: flex; align-items: center; gap: var(--space-2); }
.pager__btn {
  padding: var(--space-1) var(--space-3); border: 1px solid var(--color-border);
  border-radius: var(--radius); background: var(--color-surface); cursor: pointer;
}
.pager__btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pager__page { color: var(--color-text-muted); font-size: 14px; }
.pager__limit { padding: var(--space-1) var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius); }
</style>
```

- [ ] **Step 6: Verify build**

Run: `cd apps/admin_miniapp && npm run build`
Expected: build succeeds.

- [ ] **Step 7: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): base UI components"
```

---

### Task 6: Users view — search + table + pagination

**Files:**
- Create: `apps/admin_miniapp/src/components/users/UserSearchBar.vue`
- Create: `apps/admin_miniapp/src/components/users/UsersTable.vue`
- Modify: `apps/admin_miniapp/src/views/UsersView.vue`

**Interfaces:**
- `UserSearchBar` emits `search` with `{ search, field }` (debounced ~300ms).
- `UsersTable` props: `items`, `loading`; emits `edit(user)`, `delete(user)`.
- `UsersView` uses `useUsersStore`, wires search/table/pagination/create button.

- [ ] **Step 1: UserSearchBar.vue**

```vue
<script setup>
import { ref, watch } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'

const emit = defineEmits(['search'])

// '' = полнотекстовый поиск; иначе точное поле модели TelegramUser.
const fieldOptions = [
  { value: '', label: 'Везде' },
  { value: 'telegram_id', label: 'telegram_id' },
  { value: 'username', label: 'username' },
  { value: 'first_name', label: 'first_name' },
  { value: 'last_name', label: 'last_name' },
  { value: 'language_code', label: 'language_code' },
]

const search = ref('')
const field = ref('')
let timer = null

// Debounce: не дёргаем backend на каждый символ.
watch([search, field], () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    emit('search', { search: search.value.trim(), field: field.value })
  }, 300)
})
</script>

<template>
  <div class="searchbar">
    <BaseInput v-model="search" placeholder="Поиск пользователей…" class="searchbar__input" />
    <BaseSelect v-model="field" :options="fieldOptions" />
  </div>
</template>

<style scoped>
.searchbar { display: flex; gap: var(--space-2); align-items: flex-end; }
.searchbar__input { flex: 1; }
</style>
```

- [ ] **Step 2: UsersTable.vue**

```vue
<script setup>
import BaseButton from '@/components/ui/BaseButton.vue'

defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
defineEmits(['edit', 'delete'])

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU')
}
</script>

<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>telegram_id</th>
          <th>username</th>
          <th>Имя</th>
          <th>Язык</th>
          <th>Бот заблокирован</th>
          <th>Создан</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in items" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.telegram_id }}</td>
          <td>{{ u.username || '—' }}</td>
          <td>{{ [u.first_name, u.last_name].filter(Boolean).join(' ') || '—' }}</td>
          <td>{{ u.language_code || '—' }}</td>
          <td>{{ u.is_blocket_bot ? 'да' : 'нет' }}</td>
          <td>{{ fmtDate(u.created_at) }}</td>
          <td class="table__actions">
            <BaseButton variant="ghost" @click="$emit('edit', u)">Изменить</BaseButton>
            <BaseButton variant="danger" @click="$emit('delete', u)">Удалить</BaseButton>
          </td>
        </tr>
        <tr v-if="!loading && !items.length">
          <td colspan="8" class="table__empty">Ничего не найдено</td>
        </tr>
        <tr v-if="loading">
          <td colspan="8" class="table__empty">Загрузка…</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow-x: auto; background: var(--color-surface); border-radius: var(--radius); box-shadow: var(--shadow); }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: var(--space-3); text-align: left; border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.table th { font-size: 13px; color: var(--color-text-muted); }
.table__actions { display: flex; gap: var(--space-2); }
.table__empty { text-align: center; color: var(--color-text-muted); padding: var(--space-5); }
</style>
```

- [ ] **Step 3: UsersView.vue (search + table + pagination + create button; edit/delete wired in Task 7)**

```vue
<script setup>
import { onMounted, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import UserSearchBar from '@/components/users/UserSearchBar.vue'
import UsersTable from '@/components/users/UsersTable.vue'
import Pagination from '@/components/ui/Pagination.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const store = useUsersStore()

// Заполняется в Task 7 (модалки). Здесь — заглушки-обработчики.
const editing = ref(null)
const deleting = ref(null)
const creating = ref(false)

onMounted(() => store.fetchUsers())

function onSearch({ search, field }) {
  store.setSearch({ search, field })
}
</script>

<template>
  <div class="users">
    <div class="users__toolbar">
      <UserSearchBar @search="onSearch" />
      <BaseButton @click="creating = true">+ Пользователь</BaseButton>
    </div>

    <p v-if="store.error" class="users__error">{{ store.error }}</p>

    <UsersTable
      :items="store.items"
      :loading="store.loading"
      @edit="editing = $event"
      @delete="deleting = $event"
    />

    <div class="users__footer">
      <Pagination
        :page="store.page"
        :has-next="store.hasNext"
        :limit="store.limit"
        @update:page="store.setPage($event)"
        @update:limit="store.setLimit($event)"
      />
    </div>
  </div>
</template>

<style scoped>
.users { display: flex; flex-direction: column; gap: var(--space-4); }
.users__toolbar { display: flex; gap: var(--space-3); align-items: flex-end; }
.users__error { color: var(--color-danger); margin: 0; }
.users__footer { display: flex; justify-content: flex-end; }
</style>
```

- [ ] **Step 4: Verify against backend**

Run backend (from repo root, infra up) or `cd apps/backend && uv run uvicorn main:app --reload`.
Run: `cd apps/admin_miniapp && npm run dev` → open `/users`.
Expected: table lists users; typing in search filters (debounced); field selector narrows to a column; prev/next + page-size work; empty-state shows when no rows.

- [ ] **Step 5: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): users search, table, pagination"
```

---

### Task 7: Users view — edit (user+profile+stats), delete, create

**Files:**
- Create: `apps/admin_miniapp/src/components/users/UserEditDialog.vue`
- Create: `apps/admin_miniapp/src/components/users/UserDeleteConfirm.vue`
- Create: `apps/admin_miniapp/src/components/users/UserCreateDialog.vue`
- Modify: `apps/admin_miniapp/src/views/UsersView.vue`

**Interfaces:**
- `UserEditDialog` props: `user`; emits `close`, `saved`. On save: PATCH `/users/{id}`; if profile fields changed → PATCH `/profile/{id}` (or POST create with `telegram_user_id` when no profile exists); same for stats.
- `UserDeleteConfirm` props: `user`; emits `close`, `confirm`.
- `UserCreateDialog` emits `close`, `created`. Builds composite `{ telegram_user, profile, stats }`.

- [ ] **Step 1: UserEditDialog.vue**

```vue
<script setup>
import { reactive, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'saved'])
const store = useUsersStore()

const saving = ref(false)
const error = ref(null)

// Локальные копии, чтобы не мутировать строку таблицы напрямую.
const form = reactive({
  username: props.user.username ?? '',
  first_name: props.user.first_name ?? '',
  last_name: props.user.last_name ?? '',
  language_code: props.user.language_code ?? '',
  is_blocket_bot: !!props.user.is_blocket_bot,
})

const profile = reactive({
  phone: props.user.user_profile?.phone ?? '',
  email: props.user.user_profile?.email ?? '',
  timezone: props.user.user_profile?.timezone ?? '',
  full_name: props.user.user_profile?.full_name ?? '',
  note: props.user.user_profile?.note ?? '',
})

const stats = reactive({
  source: props.user.user_stats?.source ?? '',
  state: props.user.user_stats?.state ?? '',
})

// null-им пустые строки, чтобы не затирать nullable-поля пустотой бессмысленно.
function nullify(obj) {
  const out = {}
  for (const [k, v] of Object.entries(obj)) out[k] = v === '' ? null : v
  return out
}

async function save() {
  saving.value = true
  error.value = null
  try {
    // 1) Основные поля пользователя
    await store.updateUser(props.user.id, {
      username: form.username || null,
      first_name: form.first_name || null,
      last_name: form.last_name || null,
      language_code: form.language_code || null,
      is_blocket_bot: form.is_blocket_bot,
    })

    // 2) Профиль: PATCH если есть, иначе POST с telegram_user_id
    const profilePayload = nullify(profile)
    if (props.user.user_profile?.id) {
      await store.updateProfile(props.user.user_profile.id, profilePayload)
    } else {
      await store.createProfile({ telegram_user_id: props.user.id, ...profilePayload })
    }

    // 3) Статистика: PATCH если есть, иначе POST
    const statsPayload = nullify(stats)
    if (props.user.user_stats?.id) {
      await store.updateStats(props.user.user_stats.id, statsPayload)
    } else {
      await store.createStats({ telegram_user_id: props.user.id, ...statsPayload })
    }

    await store.fetchUsers()
    emit('saved')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal :title="`Пользователь #${user.id}`" @close="emit('close')">
    <div class="form">
      <p class="form__readonly">telegram_id: <b>{{ user.telegram_id }}</b></p>

      <BaseInput v-model="form.username" label="username" />
      <BaseInput v-model="form.first_name" label="Имя" />
      <BaseInput v-model="form.last_name" label="Фамилия" />
      <BaseInput v-model="form.language_code" label="Язык (language_code)" />
      <label class="form__check">
        <input type="checkbox" v-model="form.is_blocket_bot" />
        <span>Бот заблокирован пользователем</span>
      </label>

      <details class="form__section">
        <summary>Профиль</summary>
        <div class="form__group">
          <BaseInput v-model="profile.full_name" label="ФИО" />
          <BaseInput v-model="profile.phone" label="Телефон" />
          <BaseInput v-model="profile.email" label="Email" />
          <BaseInput v-model="profile.timezone" label="Таймзона" />
          <BaseInput v-model="profile.note" label="Заметка" />
        </div>
      </details>

      <details class="form__section">
        <summary>Статистика</summary>
        <div class="form__group">
          <BaseInput v-model="stats.source" label="Источник (source)" />
          <BaseInput v-model="stats.state" label="Состояние (state)" />
        </div>
      </details>

      <p v-if="error" class="form__error">{{ error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton :disabled="saving" @click="save">{{ saving ? 'Сохранение…' : 'Сохранить' }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: var(--space-3); }
.form__readonly { margin: 0; color: var(--color-text-muted); }
.form__check { display: flex; gap: var(--space-2); align-items: center; }
.form__section > summary { cursor: pointer; font-weight: 500; padding: var(--space-2) 0; }
.form__group { display: flex; flex-direction: column; gap: var(--space-3); padding-top: var(--space-2); }
.form__error { color: var(--color-danger); margin: 0; }
</style>
```

- [ ] **Step 2: UserDeleteConfirm.vue**

```vue
<script setup>
import { ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'confirm'])
const store = useUsersStore()

const busy = ref(false)
const error = ref(null)

async function confirm() {
  busy.value = true
  error.value = null
  try {
    await store.deleteUser(props.user.id)
    emit('confirm')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal title="Удаление пользователя" @close="emit('close')">
    <p>
      Удалить пользователя <b>#{{ user.id }}</b>
      (telegram_id {{ user.telegram_id }})? Действие необратимо — профиль и
      статистика будут удалены каскадно.
    </p>
    <p v-if="error" class="del__error">{{ error }}</p>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton variant="danger" :disabled="busy" @click="confirm">
        {{ busy ? 'Удаление…' : 'Удалить' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.del__error { color: var(--color-danger); }
</style>
```

- [ ] **Step 3: UserCreateDialog.vue**

```vue
<script setup>
import { reactive, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import { extractError } from '@/api/http'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const emit = defineEmits(['close', 'created'])
const store = useUsersStore()

const saving = ref(false)
const error = ref(null)

const form = reactive({
  telegram_id: '',
  username: '',
  first_name: '',
  last_name: '',
  language_code: '',
})
const profile = reactive({ full_name: '', phone: '', email: '' })
const stats = reactive({ source: '' })

async function save() {
  if (!form.telegram_id) {
    error.value = 'telegram_id обязателен'
    return
  }
  saving.value = true
  error.value = null
  try {
    // Композитный POST /telegram/users: telegram_user + опц. profile/stats.
    const payload = {
      telegram_user: {
        telegram_id: Number(form.telegram_id),
        username: form.username || null,
        first_name: form.first_name || null,
        last_name: form.last_name || null,
        language_code: form.language_code || null,
      },
      profile: {
        full_name: profile.full_name || null,
        phone: profile.phone || null,
        email: profile.email || null,
      },
      stats: { source: stats.source || null },
    }
    await store.createUser(payload)
    emit('created')
  } catch (err) {
    error.value = extractError(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal title="Новый пользователь" @close="emit('close')">
    <div class="form">
      <BaseInput v-model="form.telegram_id" type="number" label="telegram_id *" />
      <BaseInput v-model="form.username" label="username" />
      <BaseInput v-model="form.first_name" label="Имя" />
      <BaseInput v-model="form.last_name" label="Фамилия" />
      <BaseInput v-model="form.language_code" label="Язык" />

      <details class="form__section">
        <summary>Профиль</summary>
        <div class="form__group">
          <BaseInput v-model="profile.full_name" label="ФИО" />
          <BaseInput v-model="profile.phone" label="Телефон" />
          <BaseInput v-model="profile.email" label="Email" />
        </div>
      </details>

      <details class="form__section">
        <summary>Статистика</summary>
        <div class="form__group">
          <BaseInput v-model="stats.source" label="Источник" />
        </div>
      </details>

      <p v-if="error" class="form__error">{{ error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" @click="emit('close')">Отмена</BaseButton>
      <BaseButton :disabled="saving" @click="save">{{ saving ? 'Создание…' : 'Создать' }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: var(--space-3); }
.form__section > summary { cursor: pointer; font-weight: 500; padding: var(--space-2) 0; }
.form__group { display: flex; flex-direction: column; gap: var(--space-3); padding-top: var(--space-2); }
.form__error { color: var(--color-danger); margin: 0; }
</style>
```

- [ ] **Step 4: Wire dialogs into UsersView.vue**

Replace the `<script setup>` and `<template>` of `UsersView.vue` to mount the dialogs:

```vue
<script setup>
import { onMounted, ref } from 'vue'
import { useUsersStore } from '@/stores/users'
import UserSearchBar from '@/components/users/UserSearchBar.vue'
import UsersTable from '@/components/users/UsersTable.vue'
import UserEditDialog from '@/components/users/UserEditDialog.vue'
import UserDeleteConfirm from '@/components/users/UserDeleteConfirm.vue'
import UserCreateDialog from '@/components/users/UserCreateDialog.vue'
import Pagination from '@/components/ui/Pagination.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const store = useUsersStore()

const editing = ref(null)
const deleting = ref(null)
const creating = ref(false)

onMounted(() => store.fetchUsers())

function onSearch({ search, field }) {
  store.setSearch({ search, field })
}
</script>

<template>
  <div class="users">
    <div class="users__toolbar">
      <UserSearchBar @search="onSearch" />
      <BaseButton @click="creating = true">+ Пользователь</BaseButton>
    </div>

    <p v-if="store.error" class="users__error">{{ store.error }}</p>

    <UsersTable
      :items="store.items"
      :loading="store.loading"
      @edit="editing = $event"
      @delete="deleting = $event"
    />

    <div class="users__footer">
      <Pagination
        :page="store.page"
        :has-next="store.hasNext"
        :limit="store.limit"
        @update:page="store.setPage($event)"
        @update:limit="store.setLimit($event)"
      />
    </div>

    <UserEditDialog
      v-if="editing"
      :user="editing"
      @close="editing = null"
      @saved="editing = null"
    />
    <UserDeleteConfirm
      v-if="deleting"
      :user="deleting"
      @close="deleting = null"
      @confirm="deleting = null"
    />
    <UserCreateDialog
      v-if="creating"
      @close="creating = false"
      @created="creating = false"
    />
  </div>
</template>

<style scoped>
.users { display: flex; flex-direction: column; gap: var(--space-4); }
.users__toolbar { display: flex; gap: var(--space-3); align-items: flex-end; }
.users__error { color: var(--color-danger); margin: 0; }
.users__footer { display: flex; justify-content: flex-end; }
</style>
```

- [ ] **Step 5: Verify against backend**

Run dev + backend. On `/users`:
Expected: Edit opens modal, changes user + profile + stats, saves, table refreshes. Delete asks confirmation then removes the row. Create adds a user (use a fresh `telegram_id`).

- [ ] **Step 6: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): user edit/delete/create dialogs"
```

---

### Task 8: Docker + Caddy + compose

**Files:**
- Create: `apps/admin_miniapp/Dockerfile`
- Create: `apps/admin_miniapp/Caddyfile`
- Create: `apps/admin_miniapp/.dockerignore`
- Modify: `infra/docker-compose.apps.yml`

**Interfaces:**
- Produces: container serving the SPA on `:80`, proxying `/api/*` → `backend:8000`; published on host `:8080`.

- [ ] **Step 1: Dockerfile (multi-stage)**

```dockerfile
# --- Stage 1: сборка статики ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Stage 2: раздача через Caddy ---
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
```

- [ ] **Step 2: Caddyfile**

```caddy
# Локальная раздача без TLS. Для прода замени ":80" на домен (admin.example.com)
# — Caddy сам получит TLS-сертификат.
:80 {
	root * /srv
	encode gzip

	# API проксируем на backend в той же docker-сети (один origin → нет CORS).
	handle /api/* {
		reverse_proxy backend:8000
	}

	# SPA-fallback: любые остальные пути отдаём index.html (client-side routing).
	handle {
		try_files {path} /index.html
		file_server
	}
}
```

- [ ] **Step 3: .dockerignore**

```dockerignore
node_modules
dist
.env
.env.local
.git
*.log
docs
```

- [ ] **Step 4: Add service to infra/docker-compose.apps.yml**

Insert this service block under `services:` (after `tg_user_bot`), keeping the existing `networks:` block at the end:

```yaml
  # --------------------------------------------------------------------------
  # Admin MiniApp — Vue SPA (админка). Caddy раздаёт собранную статику и
  # проксирует /api на backend в общей сети (один origin → нет CORS).
  # Доступна на http://localhost:8080.
  # --------------------------------------------------------------------------
  admin_miniapp:
    build:
      context: ../apps/admin_miniapp
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend
    networks:
      - leadorub
```

- [ ] **Step 5: Verify docker build + run**

Run (from `infra/`, infra already up):
```bash
docker compose -f docker-compose.apps.yml up -d --build admin_miniapp
```
Expected: image builds; container runs. Open http://localhost:8080 → admin loads, Users tab lists data from backend (proxied `/api`).

- [ ] **Step 6: Commit (deferred)**

```bash
# git commit -m "feat(admin_miniapp): dockerfile, caddy, compose service"
```

---

### Task 9: Documentation

**Files:**
- Create: `apps/admin_miniapp/README.md` (Russian)
- Create: `apps/admin_miniapp/.claude/CLAUDE.md` (English)

**Interfaces:** none (docs only).

- [ ] **Step 1: README.md (Russian)**

Cover: назначение (админка-SPA), стек, структура папок, как добавить вкладку (реестр `src/tabs/index.js`), запуск локально (`npm install`, `npm run dev`, backend на :8000), запуск в Docker (порт 8080, Caddy + reverse proxy), переменные окружения (`VITE_API_PROXY_TARGET`), вкладка Users (поиск/пагинация/CRUD + profile/stats), known issue: эндпоинты без авторизации.

- [ ] **Step 2: .claude/CLAUDE.md (English)**

Cover: module purpose, stack, architecture (tab registry → router/nav single source of truth; api layer; pinia store; no-CORS strategy), backend contract consumed (`/api/telegram/users|profile|stats`), how to add a tab, dev vs docker run, env vars, conventions (Russian code comments, `is_blocket_bot` spelling), out-of-scope (Telegram SDK/auth), known issue (no authz).

- [ ] **Step 3: Verify**

Read both files; ensure links/paths correct and consistent with implementation.

- [ ] **Step 4: Commit (deferred)**

```bash
# git commit -m "docs(admin_miniapp): readme + claude module docs"
```

---

## Self-Review

**Spec coverage:**
- Tab architecture / easy to add tabs → Task 2 (registry + router). ✓
- Four tabs Users/Newsletter/Admin/Chat → Task 2 (placeholders) + Tasks 6–7 (Users). ✓
- Connect backend CRUD → Tasks 3–4 (api + store). ✓
- Search → Task 6 (UserSearchBar + store.setSearch). ✓
- Delete → Task 7 (UserDeleteConfirm). ✓
- Update incl. profile/stats → Task 7 (UserEditDialog). ✓
- Create (CRUD completeness) → Task 7 (UserCreateDialog). ✓
- Docker + compose + Caddy → Task 8. ✓
- Docs sync → Task 9. ✓

**Placeholder scan:** No TBD/TODO in code steps; all components have full code. ✓

**Type consistency:** Store actions referenced by dialogs (`updateUser`, `updateProfile`, `createProfile`, `updateStats`, `createStats`, `deleteUser`, `createUser`, `setSearch`, `setPage`, `setLimit`, `fetchUsers`) all defined in Task 4. API method names (`list/get/create/update/remove`, `patch/create`) consistent between Task 3 and consumers. `is_blocket_bot` spelling consistent. ✓

**Note on Task 1 ordering:** `main.js` imports `@/router`, created in Task 2 — so the first successful `npm run build` happens at Task 2 Step 8 (Task 1 only runs `npm install`). Flagged in Task 1 Step 9.
