# Newsletter Tab (frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend of the Newsletter tab in `apps/admin_miniapp` — compose a broadcast (text + one optional attachment), pick an audience (everyone or a Users-style filter), confirm, and "send" via a clearly-stubbed pipeline.

**Architecture:** A two-column Vue view. Left = `AudiencePanel` (radio all/filter, reusing the existing `UserSearchBar`). Right = `MessageComposer` (textarea + new `BaseFileInput` + "Разослать"). A Pinia store holds audience/text/file and runs a mocked `send()`; an `api/newsletter.js` module carries the real (not-yet-called) backend contract. A `NewsletterConfirmDialog` (on `BaseModal`) shows a summary before sending.

**Tech Stack:** Vue 3 (`<script setup>`), Pinia, Axios, custom CSS on `src/styles/tokens.css`. Build tool: Vite only.

## Global Constraints

- **CSS:** colors/spacing/radius/shadow come ONLY from `src/styles/tokens.css` variables — no hardcoded values (add a new token if one is missing).
- **Comments:** code comments in **Russian** (module style).
- **API base:** never hardcode host/port; the API base is `/api` (set in `api/http.js`). New endpoints are paths under it.
- **No new dependencies:** use only what is already in `package.json` (Vue, Pinia, Axios, vue-router).
- **No backend changes** in this plan — the broadcast endpoint is stubbed on the frontend.

### Verification approach (read first)

This module has **no JS test framework and no ESLint** (frontend tests are explicitly out of scope per `apps/admin_miniapp/.claude/CLAUDE.md`). So tasks do not use automated `*.test.js`. Instead:

- **Compile check:** `npm run build` (run from `apps/admin_miniapp/`). Vite/Rollup only compiles files reachable from the entry. The new components become reachable once `NewsletterView` imports them in **Task 6**, so the build is a *full* compile check from Task 6 onward. Before that, rely on the editor's Vue tooling for syntax.
- **Definitive manual verification** lives in **Task 6** as a concrete browser checklist (`npm run dev`).
- Commits are per-task and atomic (matches the user's git preference).

All commands below assume the working directory is `apps/admin_miniapp/`.

---

### Task 1: Data layer — API module + Pinia store

**Files:**
- Create: `apps/admin_miniapp/src/api/newsletter.js`
- Create: `apps/admin_miniapp/src/stores/newsletter.js`

**Interfaces:**
- Consumes: `http` and `extractError` from `@/api/http`.
- Produces:
  - `newsletterApi.send(formData) -> Promise<any>` (real backend contract; NOT called yet).
  - `useNewsletterStore()` Pinia store:
    - state: `audience {mode:'all'|'filter', search:'', field:''}`, `text:''`, `file:File|null`, `sending:false`, `error:null`, `result:null`
    - getters: `canSend:boolean`, `audienceLabel:string`
    - actions: `setAudience({mode,search,field})`, `setText(value)`, `setFile(file)`, `async send()`, `reset()`

- [ ] **Step 1: Create the API module**

`apps/admin_miniapp/src/api/newsletter.js`:

```js
import { http } from '@/api/http'

const BASE = '/telegram/newsletter'

export const newsletterApi = {
  // multipart/form-data — axios сам выставит Content-Type с boundary по FormData.
  // ВНИМАНИЕ: бэкенд этого эндпоинта ещё нет. Модуль готов, но из стора пока не вызывается.
  send(formData) {
    return http.post(BASE, formData).then((r) => r.data)
  },
}
```

- [ ] **Step 2: Create the Pinia store**

`apps/admin_miniapp/src/stores/newsletter.js`:

```js
import { defineStore } from 'pinia'
import { extractError } from '@/api/http'

// Заглушка отправки: бэкенда ещё нет. Имитируем сетевую задержку и успех.
// TODO: удалить mockSend и звать newsletterApi.send(form) из @/api/newsletter,
// когда появится POST /telegram/newsletter.
function mockSend(_form) {
  return new Promise((resolve) => setTimeout(() => resolve({ status: 'ok' }), 800))
}

export const useNewsletterStore = defineStore('newsletter', {
  state: () => ({
    audience: { mode: 'all', search: '', field: '' }, // mode: 'all' | 'filter'
    text: '',
    file: null, // File | null
    sending: false,
    error: null,
    result: null, // { status } после успешной отправки
  }),

  getters: {
    // Слать можно, если есть текст ИЛИ вложение. Пустую рассылку запрещаем.
    canSend: (state) => state.text.trim().length > 0 || state.file !== null,
    // Человекочитаемое описание аудитории для диалога подтверждения.
    audienceLabel: (state) => {
      if (state.audience.mode === 'all') return 'Все пользователи'
      const where = state.audience.field || 'везде'
      const q = state.audience.search || '—'
      return `Фильтр: ${where} ⊇ "${q}"`
    },
  },

  actions: {
    setAudience({ mode, search, field }) {
      this.audience = {
        mode: mode ?? this.audience.mode,
        search: search ?? '',
        field: field ?? '',
      }
    },
    setText(value) {
      this.text = value
    },
    setFile(file) {
      this.file = file
    },

    async send() {
      this.error = null
      if (!this.canSend) {
        this.error = 'Добавьте текст или вложение'
        return
      }
      // FormData — потому что есть бинарный файл (multipart).
      const form = new FormData()
      form.append('text', this.text)
      if (this.file) form.append('file', this.file)
      form.append('mode', this.audience.mode)
      if (this.audience.mode === 'filter') {
        form.append('search', this.audience.search)
        form.append('field', this.audience.field)
      }

      this.sending = true
      try {
        // TODO: заменить mockSend(form) на newsletterApi.send(form), когда будет бэкенд.
        this.result = await mockSend(form)
        // После успеха чистим сообщение, аудиторию оставляем.
        this.text = ''
        this.file = null
      } catch (err) {
        this.error = extractError(err)
      } finally {
        this.sending = false
      }
    },

    reset() {
      this.text = ''
      this.file = null
      this.error = null
      this.result = null
    },
  },
})
```

> Note: `newsletterApi` is intentionally NOT imported here yet (the store uses `mockSend`). `api/newsletter.js` simply has no importer until the backend lands — Vite does not error on an unreferenced module.

- [ ] **Step 3: Compile check**

Run: `npm run build`
Expected: build succeeds (these two files have no syntax errors; they aren't bundled yet because nothing imports them, but the command must still exit 0).

- [ ] **Step 4: Commit**

```bash
git add apps/admin_miniapp/src/api/newsletter.js apps/admin_miniapp/src/stores/newsletter.js
git commit -m "feat(admin_miniapp): newsletter data layer (api stub + pinia store)"
```

---

### Task 2: `BaseFileInput` UI primitive

**Files:**
- Create: `apps/admin_miniapp/src/components/ui/BaseFileInput.vue`

**Interfaces:**
- Consumes: nothing project-specific (pure UI; Vue `ref/watch/onBeforeUnmount`).
- Produces: a component with `v-model` support.
  - Props: `modelValue: File|null` (default `null`), `label: string` (default `''`), `accept: string` (default `''` = any type).
  - Emits: `update:modelValue` with `File | null`.

- [ ] **Step 1: Create the component**

`apps/admin_miniapp/src/components/ui/BaseFileInput.vue`:

```vue
<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: null }, // File | null (File — это объект)
  label: { type: String, default: '' },
  accept: { type: String, default: '' }, // '' = любой тип
})
const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const previewUrl = ref('') // object URL для превью изображения

// При смене файла пересоздаём object URL (для картинок — показываем превью),
// старый обязательно освобождаем, иначе утечёт память.
watch(
  () => props.modelValue,
  (file) => {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
    if (file && file.type.startsWith('image/')) {
      previewUrl.value = URL.createObjectURL(file)
    }
  }
)

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

function onChange(e) {
  const file = e.target.files?.[0] ?? null
  emit('update:modelValue', file)
}

function pick() {
  inputRef.value?.click()
}

function clear() {
  emit('update:modelValue', null)
  // сбрасываем native input, чтобы можно было выбрать тот же файл повторно
  if (inputRef.value) inputRef.value.value = ''
}

// Человекочитаемый размер файла.
function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}
</script>

<template>
  <div class="file">
    <span v-if="label" class="file__label">{{ label }}</span>

    <!-- native input скрыт, открываем его кликом по кнопке -->
    <input
      ref="inputRef"
      type="file"
      class="file__native"
      :accept="accept"
      @change="onChange"
    />

    <div v-if="!modelValue">
      <button type="button" class="file__btn" @click="pick">📎 Прикрепить файл</button>
    </div>

    <div v-else class="file__selected">
      <img v-if="previewUrl" :src="previewUrl" alt="" class="file__thumb" />
      <div class="file__meta">
        <span class="file__name">{{ modelValue.name }}</span>
        <span class="file__size">{{ fmtSize(modelValue.size) }}</span>
      </div>
      <button type="button" class="file__remove" title="Убрать" @click="clear">×</button>
    </div>
  </div>
</template>

<style scoped>
.file {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.file__label {
  font-size: 13px;
  color: var(--color-text-muted);
}
.file__native {
  display: none;
}
.file__btn {
  padding: var(--space-2) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  font: inherit;
  color: var(--color-text);
  cursor: pointer;
}
.file__btn:hover {
  border-color: var(--color-primary);
}
.file__selected {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
}
.file__thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: var(--radius);
}
.file__meta {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.file__name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file__size {
  font-size: 12px;
  color: var(--color-text-muted);
}
.file__remove {
  border: none;
  background: none;
  font-size: 20px;
  line-height: 1;
  color: var(--color-text-muted);
  cursor: pointer;
}
</style>
```

- [ ] **Step 2: Compile check**

Run: `npm run build`
Expected: build succeeds. (Not bundled yet — wired in Task 4 — but must exit 0.)

- [ ] **Step 3: Commit**

```bash
git add apps/admin_miniapp/src/components/ui/BaseFileInput.vue
git commit -m "feat(admin_miniapp): BaseFileInput primitive (name/preview/remove)"
```

---

### Task 3: `AudiencePanel` (left column)

**Files:**
- Create: `apps/admin_miniapp/src/components/newsletter/AudiencePanel.vue`

**Interfaces:**
- Consumes: `useNewsletterStore` (Task 1) → `setAudience`; existing `@/components/users/UserSearchBar.vue` (emits `search` with `{ search, field }`).
- Produces: a self-contained panel; no props/emits (writes straight to the store).

- [ ] **Step 1: Create the component**

`apps/admin_miniapp/src/components/newsletter/AudiencePanel.vue`:

```vue
<script setup>
import { ref, watch } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import UserSearchBar from '@/components/users/UserSearchBar.vue'

const store = useNewsletterStore()

// Локальное состояние панели, инициализируем из стора.
const mode = ref(store.audience.mode) // 'all' | 'filter'
const search = ref(store.audience.search)
const field = ref(store.audience.field)

// Любое изменение режима/фильтра синхронизируем в стор.
watch([mode, search, field], () => {
  store.setAudience({ mode: mode.value, search: search.value, field: field.value })
})

// UserSearchBar уже дебаунсит и отдаёт { search, field }.
function onSearch({ search: s, field: f }) {
  search.value = s
  field.value = f
}
</script>

<template>
  <aside class="audience">
    <h3 class="audience__title">Аудитория</h3>

    <label class="audience__radio">
      <input v-model="mode" type="radio" value="all" />
      <span>Отправить всем</span>
    </label>

    <label class="audience__radio">
      <input v-model="mode" type="radio" value="filter" />
      <span>По фильтру</span>
    </label>

    <div v-if="mode === 'filter'" class="audience__filter">
      <UserSearchBar @search="onSearch" />
    </div>
  </aside>
</template>

<style scoped>
.audience {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
}
.audience__title {
  margin: 0;
  font-size: 16px;
}
.audience__radio {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}
.audience__filter {
  margin-top: var(--space-2);
}
</style>
```

- [ ] **Step 2: Compile check**

Run: `npm run build`
Expected: build succeeds. (Wired in Task 6.)

- [ ] **Step 3: Commit**

```bash
git add apps/admin_miniapp/src/components/newsletter/AudiencePanel.vue
git commit -m "feat(admin_miniapp): newsletter AudiencePanel (all/filter + UserSearchBar)"
```

---

### Task 4: `MessageComposer` (right column)

**Files:**
- Create: `apps/admin_miniapp/src/components/newsletter/MessageComposer.vue`

**Interfaces:**
- Consumes: `useNewsletterStore` (Task 1) → `text`/`setText`, `file`/`setFile`, `canSend`, `sending`; `@/components/ui/BaseFileInput.vue` (Task 2); `@/components/ui/BaseButton.vue`.
- Produces: emits `submit` when the user clicks "Разослать" (the view opens the confirm dialog; the composer never sends directly).

- [ ] **Step 1: Create the component**

`apps/admin_miniapp/src/components/newsletter/MessageComposer.vue`:

```vue
<script setup>
import { computed } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import BaseFileInput from '@/components/ui/BaseFileInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const emit = defineEmits(['submit']) // просим вьюху открыть диалог подтверждения

const store = useNewsletterStore()

// v-model к стору через computed get/set.
const text = computed({
  get: () => store.text,
  set: (v) => store.setText(v),
})
const file = computed({
  get: () => store.file,
  set: (v) => store.setFile(v),
})
</script>

<template>
  <section class="composer">
    <h3 class="composer__title">Сообщение</h3>

    <textarea
      v-model="text"
      class="composer__text"
      rows="8"
      placeholder="Текст рассылки…"
    />

    <BaseFileInput v-model="file" label="Вложение" />

    <div class="composer__actions">
      <BaseButton :disabled="!store.canSend || store.sending" @click="emit('submit')">
        Разослать
      </BaseButton>
    </div>
  </section>
</template>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
}
.composer__title {
  margin: 0;
  font-size: 16px;
}
.composer__text {
  width: 100%;
  resize: vertical;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font: inherit;
}
.composer__text:focus {
  outline: none;
  border-color: var(--color-primary);
}
.composer__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 2: Compile check**

Run: `npm run build`
Expected: build succeeds. (Wired in Task 6.)

- [ ] **Step 3: Commit**

```bash
git add apps/admin_miniapp/src/components/newsletter/MessageComposer.vue
git commit -m "feat(admin_miniapp): newsletter MessageComposer (textarea + file + send)"
```

---

### Task 5: `NewsletterConfirmDialog`

**Files:**
- Create: `apps/admin_miniapp/src/components/newsletter/NewsletterConfirmDialog.vue`

**Interfaces:**
- Consumes: `useNewsletterStore` (Task 1) → `audienceLabel`, `text`, `file`, `error`, `sending`, `send()`; `@/components/ui/BaseModal.vue` (props `title`, emits `close`, slot `footer`); `@/components/ui/BaseButton.vue`.
- Produces: emits `close` (cancel/overlay) and `sent` (after a successful `send()`).

- [ ] **Step 1: Create the component**

`apps/admin_miniapp/src/components/newsletter/NewsletterConfirmDialog.vue`:

```vue
<script setup>
import { useNewsletterStore } from '@/stores/newsletter'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const emit = defineEmits(['close', 'sent'])

const store = useNewsletterStore()

async function confirm() {
  await store.send()
  // send() при ошибке выставит store.error и не очистит сообщение — тогда не закрываем.
  if (!store.error) emit('sent')
}
</script>

<template>
  <BaseModal title="Подтверждение рассылки" @close="emit('close')">
    <div class="confirm">
      <p class="confirm__row"><b>Аудитория:</b> {{ store.audienceLabel }}</p>
      <p class="confirm__row">
        <b>Текст:</b>
        <span v-if="store.text">{{ store.text }}</span>
        <span v-else class="confirm__muted">— без текста —</span>
      </p>
      <p class="confirm__row">
        <b>Вложение:</b>
        <span v-if="store.file">{{ store.file.name }}</span>
        <span v-else class="confirm__muted">— нет —</span>
      </p>
      <p v-if="store.error" class="confirm__error">{{ store.error }}</p>
    </div>

    <template #footer>
      <BaseButton variant="ghost" :disabled="store.sending" @click="emit('close')">
        Отмена
      </BaseButton>
      <BaseButton :disabled="store.sending" @click="confirm">
        {{ store.sending ? 'Отправка…' : 'Разослать' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.confirm {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.confirm__row {
  margin: 0;
  word-break: break-word;
}
.confirm__muted {
  color: var(--color-text-muted);
}
.confirm__error {
  margin: 0;
  color: var(--color-danger);
}
</style>
```

- [ ] **Step 2: Compile check**

Run: `npm run build`
Expected: build succeeds. (Wired in Task 6.)

- [ ] **Step 3: Commit**

```bash
git add apps/admin_miniapp/src/components/newsletter/NewsletterConfirmDialog.vue
git commit -m "feat(admin_miniapp): newsletter confirm dialog with summary"
```

---

### Task 6: Assemble `NewsletterView` + success token (integration)

**Files:**
- Modify: `apps/admin_miniapp/src/styles/tokens.css` (add success colors)
- Modify: `apps/admin_miniapp/src/views/NewsletterView.vue` (replace the Placeholder)

**Interfaces:**
- Consumes: `useNewsletterStore`, `AudiencePanel` (Task 3), `MessageComposer` (Task 4), `NewsletterConfirmDialog` (Task 5).
- Produces: the finished Newsletter tab. No new exports.

- [ ] **Step 1: Add success tokens**

In `apps/admin_miniapp/src/styles/tokens.css`, inside `:root`, add these two lines right after the `--color-danger-hover` line:

```css
  --color-success: #047857;
  --color-success-bg: #ecfdf5;
```

- [ ] **Step 2: Replace the view**

Overwrite `apps/admin_miniapp/src/views/NewsletterView.vue` with:

```vue
<script setup>
import { ref } from 'vue'
import { useNewsletterStore } from '@/stores/newsletter'
import AudiencePanel from '@/components/newsletter/AudiencePanel.vue'
import MessageComposer from '@/components/newsletter/MessageComposer.vue'
import NewsletterConfirmDialog from '@/components/newsletter/NewsletterConfirmDialog.vue'

const store = useNewsletterStore()

const confirming = ref(false)
const sentNotice = ref(false)

function onSubmit() {
  store.error = null
  confirming.value = true
}

function onSent() {
  confirming.value = false
  sentNotice.value = true
  // авто-скрытие уведомления об успехе
  setTimeout(() => (sentNotice.value = false), 4000)
}
</script>

<template>
  <div class="newsletter">
    <p v-if="sentNotice" class="newsletter__notice">Рассылка поставлена в очередь ✓</p>
    <p v-if="store.error && !confirming" class="newsletter__error">{{ store.error }}</p>

    <div class="newsletter__cols">
      <AudiencePanel class="newsletter__left" />
      <MessageComposer class="newsletter__right" @submit="onSubmit" />
    </div>

    <NewsletterConfirmDialog
      v-if="confirming"
      @close="confirming = false"
      @sent="onSent"
    />
  </div>
</template>

<style scoped>
.newsletter {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.newsletter__cols {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
  flex-wrap: wrap;
}
.newsletter__left {
  flex: 0 0 320px;
}
.newsletter__right {
  flex: 1 1 420px;
}
.newsletter__notice {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--color-success-bg);
  color: var(--color-success);
}
.newsletter__error {
  margin: 0;
  color: var(--color-danger);
}
</style>
```

- [ ] **Step 3: Compile check (now full — components are reachable)**

Run: `npm run build`
Expected: build succeeds with no errors. This compiles every new component for the first time.

- [ ] **Step 4: Manual verification**

Run: `npm run dev` and open the Newsletter tab. Verify the checklist:

1. Layout: left "Аудитория" panel + right "Сообщение" composer; columns stack on a narrow window.
2. "Разослать" is **disabled** when text is empty and no file is attached.
3. Type text → button enables.
4. Attach an **image** → its name, size, and a thumbnail appear; ✕ removes it.
5. Attach a **non-image** (e.g. a PDF) → name + size appear, no thumbnail; ✕ removes it.
6. Switch audience to "По фильтру" → `UserSearchBar` appears; type a query.
7. Click "Разослать" → confirm dialog shows the right audience label, text, attachment name.
8. Confirm → button shows "Отправка…" ~0.8s → dialog closes → green "поставлена в очередь ✓" notice → composer text/file cleared, audience kept.
9. Switch back to "Отправить всем" → dialog audience label reads "Все пользователи".
10. Users tab still works unchanged.

- [ ] **Step 5: Commit**

```bash
git add apps/admin_miniapp/src/styles/tokens.css apps/admin_miniapp/src/views/NewsletterView.vue
git commit -m "feat(admin_miniapp): wire Newsletter tab view + success token"
```

---

### Task 7: Sync module docs

**Files:**
- Modify: `apps/admin_miniapp/.claude/CLAUDE.md`
- Modify: `apps/admin_miniapp/README.md`

**Interfaces:** docs only; no code.

- [ ] **Step 1: Update `.claude/CLAUDE.md` (English)**

a) In the **Out of scope** section, remove Newsletter from the list. Change:

```
Telegram WebApp SDK & initData auth; Newsletter/Admin/Chat functionality;
roles/permissions; frontend test framework; any backend changes.
```

to:

```
Telegram WebApp SDK & initData auth; Admin/Chat functionality;
roles/permissions; frontend test framework; any backend changes.
```

b) Add a new section after the "Backend contract consumed (unchanged)" section:

```markdown
## Newsletter tab (frontend only; backend stubbed)

Compose a broadcast (text + one optional attachment) and pick an audience.

- `views/NewsletterView.vue` — two columns: `AudiencePanel` (left) + `MessageComposer`
  (right), plus `NewsletterConfirmDialog`.
- `components/newsletter/` — `AudiencePanel` (radio `all`/`filter`; reuses
  `UserSearchBar` for the filter inputs), `MessageComposer` (textarea + `BaseFileInput`
  + send), `NewsletterConfirmDialog` (`BaseModal` summary).
- `components/ui/BaseFileInput.vue` — single-file `v-model` picker (name, size, image
  preview, remove).
- `stores/newsletter.js` — Pinia store: `audience {mode,search,field}`, `text`, `file`,
  `sending`, `error`, `result`; getters `canSend`, `audienceLabel`; actions
  `setAudience`/`setText`/`setFile`/`send`/`reset`.
- `api/newsletter.js` — `newsletterApi.send(formData)` POSTs `multipart/form-data` to the
  **proposed** `POST /telegram/newsletter` (`text?`, `file?`, `mode`, `search?`, `field?`).

**Stub:** the backend endpoint does not exist yet. `store.send()` calls a local
`mockSend()` (≈800ms → `{status:'ok'}`); swap it for `newsletterApi.send(form)` when the
endpoint ships. No recipient count is shown — the user list endpoint returns no total.
```

- [ ] **Step 2: Update `README.md` (Russian)**

Read `apps/admin_miniapp/README.md`, find where the tabs/functionality are described, and add (in Russian, matching the existing heading style) a Newsletter subsection:

```markdown
### Вкладка «Рассылка»

Композер массовой рассылки (пока только фронтенд — бэкенд-эндпоинт ещё не готов).

- Слева — выбор аудитории: «Отправить всем» или «По фильтру» (тот же поиск, что во
  вкладке «Пользователи»: строка + поле).
- Справа — текст рассылки и одно опциональное вложение (любой тип; для картинок
  показывается превью).
- Кнопка «Разослать» открывает диалог подтверждения со сводкой. Отправка сейчас
  имитируется (мок) и завершается успехом; реальная отправка появится после
  подключения бэкенда.
```

- [ ] **Step 3: Commit**

```bash
git add apps/admin_miniapp/.claude/CLAUDE.md apps/admin_miniapp/README.md
git commit -m "docs(admin_miniapp): document Newsletter tab"
```

---

## Self-Review

**Spec coverage:**
- Two-column layout → Task 6. ✓
- Audience = Users search semantics + all/filter → Task 3 (reuses `UserSearchBar`). ✓
- One optional attachment, any type, name/preview/remove → `BaseFileInput` Task 2. ✓
- Reusable `ui/BaseFileInput.vue` → Task 2. ✓
- Store + api stub, mock send, TODO → Task 1. ✓
- Confirm dialog with textual audience label, no recipient count → Task 5. ✓
- Registry untouched (NewsletterView already registered) → Tasks don't edit `tabs/index.js`. ✓
- Docs sync (CLAUDE.md English, README Russian) → Task 7. ✓

**Placeholder scan:** No "TBD/TODO-as-work" in steps; the only `TODO` strings are the intentional in-code markers for the backend swap (explicitly part of the design). ✓

**Type consistency:** `setAudience({mode,search,field})`, `setText`, `setFile`, `send`, `canSend`, `audienceLabel` used identically across Tasks 1/3/4/5/6. `BaseFileInput` uses `update:modelValue` with `File|null` consumed via `v-model` in Task 4. `MessageComposer` emits `submit`; the view handles `@submit`. `NewsletterConfirmDialog` emits `close`/`sent`; the view handles both. ✓
