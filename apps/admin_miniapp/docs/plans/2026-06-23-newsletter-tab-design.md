# Admin MiniApp — Newsletter tab (design)

Date: 2026-06-23
Status: approved

## Goal

Build the **frontend** of the Newsletter tab in `apps/admin_miniapp`. The tab lets an
admin compose a broadcast message (text + one optional attachment) and choose its
audience (everyone, or a filtered subset reusing the Users search semantics), then
"send" it. The backend broadcast endpoint does **not** exist yet, so the send path is
a clearly-marked stub that simulates success. Wiring the real backend is a separate
follow-up task.

`NewsletterView.vue` is currently a `Placeholder`; this design replaces its contents.
The tab is already registered in `src/tabs/index.js` — the registry is **not** touched.

## Decisions (from brainstorming)

- **Audience = Users search semantics.** The left panel reuses the same `search` +
  `field` model as the Users tab (and the existing `UserSearchBar` component) rather
  than inventing new segment filters. A radio toggle switches between two modes:
  - `all` — send to everyone ("Отправить всем").
  - `filter` — send to users matching `search` (+ optional `field`).
- **One optional attachment, any type.** A single file (image OR document). The UI
  shows the file name, an image preview when the file is an image, and a remove (✕)
  control. Sending text-only or file-only is allowed; sending nothing is not.
- **Send is a stub now.** A Pinia store (`stores/newsletter.js`) + an API module
  (`api/newsletter.js`) are created with the real contract, but the store's `send()`
  calls a local `mockSend()` (artificial delay → `{ status: 'ok' }`) with a `TODO` to
  swap in `newsletterApi.send` once the backend ships.
- **New reusable UI primitive `ui/BaseFileInput.vue`.** The file field is extracted
  into the `Base*` family (consistent with `BaseInput` / `BaseSelect`), not inlined in
  the composer.
- **No recipient count for now.** The Users list endpoint returns no total count
  (documented limitation), so the confirm dialog shows a textual audience description
  instead of "~N recipients". A count is a later enhancement that needs a backend
  count/estimate endpoint.

## Stack & conventions (unchanged from the module)

Vue 3 (`<script setup>`) + Pinia + Axios. Custom CSS on `src/styles/tokens.css` —
no UI framework. Code comments in **Russian** (module style). API base URL is `/api`
everywhere (Vite proxy in dev, Caddy in prod) — never hardcode host/port.

## Backend contract (proposed, NOT yet implemented)

Router prefix `/api/telegram` (consistent with the rest of the module).

- `POST /telegram/newsletter` — `multipart/form-data`:
  - `text: string` (optional if `file` present)
  - `file: binary` (optional if `text` present)
  - `mode: "all" | "filter"`
  - `search: string` (only when `mode = filter`, optional)
  - `field: string` (only when `mode = filter`, optional)
  - → `{ "status": "ok" }` (recipient count / job id may be added later).

This is the contract `api/newsletter.js` is written against. The store does not call it
yet (uses `mockSend`).

## Architecture

### New / changed files

```
apps/admin_miniapp/src/
├── api/newsletter.js                 # NEW — newsletterApi.send(formData)
├── stores/newsletter.js              # NEW — Pinia store (audience/text/file/send)
├── views/NewsletterView.vue          # CHANGED — Placeholder → real two-column layout
└── components/
    ├── ui/BaseFileInput.vue          # NEW — single-file picker (name/preview/remove)
    └── newsletter/
        ├── AudiencePanel.vue         # NEW — mode toggle + reused UserSearchBar
        ├── MessageComposer.vue       # NEW — textarea + BaseFileInput + send button
        └── NewsletterConfirmDialog.vue  # NEW — BaseModal summary + confirm/cancel
```

### Layout (`NewsletterView.vue`)

Two columns inside a flex container that wraps on narrow screens:

- **Left (~320px):** `AudiencePanel`.
- **Right (flex: 1):** `MessageComposer`.

A view-level error line (store `error`) and a success notice (store `result`) render
above/below the columns, mirroring the Users view's `users__error` pattern.

### Component contracts

- **`ui/BaseFileInput.vue`**
  - Props: `modelValue: File | null`, `label?: string`, `accept?: string` (default `''`
    = any type).
  - Emits: `update:modelValue` (the `File` or `null`).
  - Renders: a styled "Прикрепить файл" button (hides the native ugly input), and when a
    file is selected — its name, size, a thumbnail if `file.type` starts with `image/`
    (via `URL.createObjectURL`, revoked on change/unmount), and a ✕ remove button.
  - Self-contained: knows nothing about newsletters.

- **`newsletter/AudiencePanel.vue`**
  - Local `mode` ref (`'all' | 'filter'`), two radios.
  - In `filter` mode renders `UserSearchBar` (existing component) and listens to its
    `@search` event.
  - Writes the audience into the store via `store.setAudience({ mode, search, field })`.

- **`newsletter/MessageComposer.vue`**
  - `<textarea>` bound to `store.text` (via `setText`), `BaseFileInput` bound to
    `store.file` (via `setFile`).
  - "Разослать" `BaseButton`, disabled while `!canSend` (no text AND no file) or while
    `store.sending`.
  - Click opens `NewsletterConfirmDialog` (does not send directly).

- **`newsletter/NewsletterConfirmDialog.vue`**
  - Props: audience description string, text preview, attachment name (or pulls them
    from the store).
  - `BaseModal` with a summary body and a footer: "Отмена" (ghost) / "Разослать"
    (primary). Confirm calls `store.send()`; shows `sending` state; on success emits
    `sent` and closes; on error shows `store.error` inside the dialog.

### State — `stores/newsletter.js`

```
state:
  audience: { mode: 'all', search: '', field: '' }
  text: ''
  file: null            // File | null
  sending: false
  error: null
  result: null          // { status } on success

getters:
  canSend  -> text.trim().length > 0 || file !== null
  audienceLabel -> "Все пользователи" | `Фильтр: ${field || 'везде'} ⊇ "${search}"`

actions:
  setAudience({ mode, search, field })
  setText(value)
  setFile(file)
  async send()          // validates canSend, builds FormData, calls mockSend (TODO: newsletterApi.send)
  reset()               // clears text/file/result/error after a successful send
```

`send()`:
1. Guard on `canSend` (set `error` and return if empty).
2. Build `FormData` (`text`, `file`, `mode`, `search`, `field`).
3. `sending = true`; `await mockSend()` (≈800ms artificial delay → `{ status: 'ok' }`).
   `// TODO: заменить mockSend на newsletterApi.send(form), когда появится бэкенд.`
4. On success: `result = { status: 'ok' }`, then `reset()` keeps the audience but clears
   the message.
5. On error: `error = extractError(err)`.
6. `finally`: `sending = false`.

### API — `api/newsletter.js`

```js
import { http } from '@/api/http'
export const newsletterApi = {
  send(formData) {
    // multipart/form-data — axios выставит заголовок сам по FormData
    return http.post('/telegram/newsletter', formData).then((r) => r.data)
  },
}
```

Ready for the backend; not invoked by the store yet.

### Validation & error handling

- "Разослать" disabled unless `canSend` (text or file present).
- Store-level `error` reuses `extractError` (same as Users) for the eventual real call;
  for the mock path errors are not expected but the structure is in place.
- Success surfaces a transient notice ("Рассылка поставлена в очередь" / "Отправлено")
  in the view.

## Testing

The module has **no frontend test framework** (explicitly out of scope per the module
`CLAUDE.md`). Verification is manual via `npm run dev` (Users tab still works; Newsletter
tab: audience toggle, text entry, attach/preview/remove a file, send → confirm dialog →
mock success → form clears). Adding Vitest is a possible later task, not part of this work.

## Out of scope (YAGNI)

Real backend broadcast endpoint and delivery; recipient count/estimate; multiple
attachments; scheduling/queuing UI; per-user send status; rich-text/markdown editor;
frontend tests.

## Documentation deliverables

After implementation, sync (per project rules):
- `apps/admin_miniapp/.claude/CLAUDE.md` (English) — remove Newsletter from "Out of
  scope", document the new store/api/components and the stubbed `POST /telegram/newsletter`
  contract.
- `apps/admin_miniapp/README.md` (Russian) — describe the Newsletter tab for users.
