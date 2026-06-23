# Admin MiniApp

Веб-админка Leadorub — SPA на Vue 3. Сейчас это обычное браузерное приложение
(без Telegram WebApp SDK). Архитектура заточена под лёгкое добавление новых
вкладок: всё управляется одним реестром.

## Стек

- **Vue 3** (`<script setup>`)
- **Vite** — сборка и dev-сервер
- **Vue Router** — навигация по вкладкам
- **Pinia** — состояние
- **Axios** — HTTP-клиент к backend
- **Caddy** — раздача статики и reverse-proxy `/api` в проде

## Вкладки

В системе четыре вкладки: **Users**, **Newsletter**, **Admin**, **Chat**.
Полностью реализованы **Users** (подключена к CRUD API пользователя) и
**Newsletter** (подключена к бэкенду `POST /telegram/newsletter`).
**Admin** и **Chat** — заглушки «Раздел в разработке».

### Вкладка Users

- Список пользователей с пагинацией (prev/next + размер страницы).
- Поиск: свободный текст по всем строковым полям **или** по конкретному полю
  (`telegram_id`, `username`, `first_name`, `last_name`, `language_code`).
- Создание пользователя (композитный эндпоинт: основные данные + профиль + статистика).
- Редактирование основных полей `TelegramUser`, а также вложенных `profile` и `stats`.
- Удаление пользователя (с подтверждением; профиль и статистика удаляются каскадно на backend).

> ⚠️ **Важно про пагинацию.** Backend не возвращает общее число записей, поэтому
> «есть следующая страница» определяется эвристикой: пришла ровно полная страница
> (`items.length === limit`). Точного счётчика страниц нет — это сознательное
> ограничение под текущий API.

### Вкладка «Рассылка»

Композер массовой рассылки, подключённый к бэкенду (`POST /telegram/newsletter`).

- Слева — выбор аудитории: «Отправить всем» или «По фильтру» (тот же поиск, что во
  вкладке «Пользователи»: строка + поле).
- Справа — текст рассылки и одно опциональное вложение (любой тип; для картинок
  показывается превью).
- Под вложением — настройка кнопок сообщения. Переключатель типа клавиатуры
  **Inline / Reply** и список кнопок (одна кнопка = одна строка, добавляются по «+»):
  - **Reply** — у кнопки только текст;
  - **Inline** — текст плюс ровно одно из `URL` / `callback_data`. Поля
    взаимоисключающие: как только заполняешь одно, второе скрывается.
  - «+ Добавить кнопку» недоступна, пока последняя кнопка не заполнена корректно.
- Кнопка «Разослать» открывает диалог подтверждения со сводкой (включая число
  кнопок и их тип). Подтверждение отправляет всё одним `multipart`-запросом
  (`payload` с JSON-телом + опциональный `file`) на бэкенд; после успеха показывается
  число получателей, ошибки бэкенда (нет получателей / пустая рассылка) выводятся в форме.

## Структура

```text
admin_miniapp/
├── Dockerfile            # multi-stage: node build → Caddy раздаёт статику
├── Caddyfile             # SPA-fallback + reverse_proxy /api → backend:8000
├── vite.config.js        # dev-proxy /api → localhost:8000
├── index.html
├── package.json
└── src/
    ├── main.js
    ├── App.vue                  # шапка + TabBar + <router-view>
    ├── router/index.js          # роуты строятся из реестра вкладок
    ├── tabs/index.js            # ⭐ РЕЕСТР ВКЛАДОК — единый источник правды
    ├── api/{http,users,profiles,stats,newsletter}.js
    ├── stores/{users,newsletter}.js   # Pinia-сторы вкладок Users и Newsletter
    ├── views/{Users,Newsletter,Admin,Chat}View.vue
    ├── components/
    │   ├── layout/TabBar.vue
    │   ├── users/{UserSearchBar,UsersTable,UserEditDialog,UserDeleteConfirm,UserCreateDialog}.vue
    │   ├── newsletter/{AudiencePanel,MessageComposer,KeyboardEditor,NewsletterConfirmDialog}.vue
    │   └── ui/{BaseButton,BaseInput,BaseSelect,BaseModal,BaseFileInput,Pagination,Placeholder}.vue
    └── styles/tokens.css        # дизайн-токены (CSS-переменные)
```

## Как добавить новую вкладку

1. Создай view-компонент в `src/views/`, например `ReportsView.vue`.
2. Добавь одну строку в реестр `src/tabs/index.js`:

   ```js
   { key: 'reports', label: 'Reports', component: () => import('@/views/ReportsView.vue') },
   ```

Из реестра автоматически появятся и пункт навигации (`TabBar`), и роут (`/reports`).
Больше ничего трогать не нужно.

## Запуск локально (dev)

Нужен запущенный backend на `http://localhost:8000` (или поправь цель прокси).

```bash
cd apps/admin_miniapp
npm install
npm run dev
```

Откроется `http://localhost:5173`. Запросы на `/api` Vite проксирует на backend —
поэтому CORS не нужен.

Переменные окружения (`.env`, по примеру `.env.example`):

- `VITE_API_PROXY_TARGET` — куда проксировать `/api` в dev (по умолчанию `http://localhost:8000`).

## Запуск в Docker

Сервис `admin_miniapp` входит в `infra/docker-compose.apps.yml`. Из папки `infra/`
(инфраструктура уже поднята):

```bash
docker compose -f docker-compose.apps.yml up -d --build admin_miniapp
```

Админка будет доступна на `http://localhost:8080`. Внутри контейнера Caddy
раздаёт собранную статику и проксирует `/api/*` на сервис `backend` в сети
`leadorub` — один origin, без CORS.

Для прода в `Caddyfile` замени `:80` на свой домен — Caddy сам выпустит TLS.

## Известное ограничение

CRUD-эндпоинты backend (`/api/telegram/*`) **не имеют авторизации**. Раздавая
админку наружу, ты открываешь управление пользователями всем, у кого есть доступ
к адресу. На текущем (локальном) этапе это допустимо, но перед публичным
развёртыванием нужно добавить проверку (например, валидацию Telegram `initData`
на backend и гейт на фронте).
