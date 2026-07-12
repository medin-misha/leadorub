# Client MiniApp

Telegram Mini App для отправки заявки на консультацию. Приложение собрано на
Vue 3 + Vite и в production раздаётся внутренним Caddy.

## Безопасность запроса

Mini App отправляет заявку на `POST /api/requisitions/public` и передаёт исходную
строку `Telegram.WebApp.initData` в заголовке `X-Telegram-Init-Data`.

Backend:

- проверяет HMAC-подпись Telegram;
- проверяет `auth_date` и TTL;
- извлекает `telegram_id` только из подписанного `user.id`;
- ограничивает частоту заявок по IP и IP+Telegram ID.

`initDataUnsafe` используется только для UI и не считается подтверждением личности.
В теле запроса нет `telegram_id`. Caddy проксирует только точный маршрут заявки,
не добавляет `SERVICE_TOKEN`, а остальные `/api/*` возвращают 404.

## Локальная разработка

```bash
cd apps/client_miniapp
npm ci
npm run dev
```

Production-сборка:

```bash
npm run build
```

Адрес backend не захардкожен: frontend использует относительный `/api`, а Vite
или Caddy отвечает за reverse proxy.

## Docker

Сервис запускается через `infra/docker-compose.apps.yml`. Диагностический порт
доступен только локально на `127.0.0.1:8081`; публичный HTTPS-маршрут обслуживает
edge Caddy на `https://app.<PUBLIC_HOST>`.
