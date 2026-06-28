# Edge-Caddy + HTTPS через sslip.io

**Дата:** 2026-06-28
**Статус:** утверждён, готов к плану имплементации

## Цель

Поставить систему Leadorub на сервер с публичным статическим IP и закрыть
весь внешний трафик через HTTPS, не покупая домен. Используем sslip.io как
бесплатный DNS и Caddy как edge-прокси с автоматическими сертификатами
Let's Encrypt.

## Контекст и вводные

- Сервер: публичный статический IP, порты 80/443 открываются.
- Домена нет — используем sslip.io. Любой хостнейм с IP внутри резолвится в
  этот IP, причём префиксы слева разрешены:
  - `1.2.3.4.sslip.io` → `1.2.3.4`
  - `grafana.1.2.3.4.sslip.io` → тоже `1.2.3.4`
  Это даёт бесплатные «поддомены» на одном IP, каждому Caddy выпустит
  отдельный сертификат (ACME-challenge проходит по 80/443).
- Уже есть **внутренний** Caddy внутри образа `admin_miniapp`: раздаёт
  Vue-статику и проксирует `/api` → `backend:8000` (один origin → нет CORS).
  Его НЕ трогаем.
- `tg_user_bot` работает на long polling — публичный вебхук не нужен.
- Backend наружу отдельным хостом не выставляем: админка ходит в `/api`
  через свой origin, бот — по внутренней docker-сети.

## Что публикуем наружу

Решение пользователя — открыть все четыре сервиса:

| Сервис | Внешний хост | Внутренний апстрим |
|---|---|---|
| Админ-панель (`admin_miniapp`) | `https://{$PUBLIC_HOST}` | `admin_miniapp:80` |
| Grafana | `https://grafana.{$PUBLIC_HOST}` | `grafana:3000` |
| MinIO консоль | `https://minio.{$PUBLIC_HOST}` | `minio:9001` |
| RabbitMQ management UI | `https://rabbitmq.{$PUBLIC_HOST}` | `rabbitmq:15672` |

## Архитектура

Отдельный **edge-Caddy** — единственный сервис, опубликованный наружу на
80/443. Он терминирует TLS и по хостнейму проксирует запросы во внутренние
контейнеры по docker-сети `leadorub`. Внутрь сети ходит по простому HTTP.

```
Интернет ──80/443──> edge-Caddy ─┬─> admin_miniapp:80  (внутренний Caddy: SPA + /api→backend)
                                 ├─> grafana:3000
                                 ├─> minio:9001
                                 └─> rabbitmq:15672
```

Роли двух Caddy:
- **edge-Caddy** — «ресепшн всего здания»: TLS, домены, маршрутизация.
- **внутренний Caddy в `admin_miniapp`** — «секретарь отдела»: статика + `/api`.

## Хостнеймы — один env-var

IP пишем один раз, в `infra/.env`:

```
PUBLIC_HOST=1.2.3.4.sslip.io
```

Caddy подставляет переменную текстом в адреса сайтов (`grafana.{$PUBLIC_HOST}`
→ `grafana.1.2.3.4.sslip.io`), поэтому одной переменной хватает на все хосты.

## Размещение и файлы

- Сервис `caddy` добавляем в `infra/docker-compose.infra.yml` (3 из 4
  апстримов — инфраструктурные; `admin_miniapp` из apps-compose проксируется
  через общую внешнюю сеть `leadorub` по имени контейнера).
- Образ — официальный `caddy:2-alpine`, без своего Dockerfile.
- Конфиг — `infra/caddy/Caddyfile`, монтируется в контейнер read-only.
- Порты: `80:80`, `443:443` (плюс `443:443/udp` для HTTP/3).
- Volumes (именованные, критично — переживают рестарт):
  - `caddy_data` → `/data` (сертификаты; иначе зря дёргаем Let's Encrypt и
    упираемся в rate limits)
  - `caddy_config` → `/config`
- Сеть: `leadorub`.

Эскиз `Caddyfile`:

```
{$PUBLIC_HOST} {
	reverse_proxy admin_miniapp:80
}

grafana.{$PUBLIC_HOST} {
	reverse_proxy grafana:3000
}

minio.{$PUBLIC_HOST} {
	reverse_proxy minio:9001
}

rabbitmq.{$PUBLIC_HOST} {
	reverse_proxy rabbitmq:15672
}
```

## Нюансы конфигурации

- **Grafana**: задать `GF_SERVER_ROOT_URL=https://grafana.${PUBLIC_HOST}`
  (через env в compose), иначе редиректы и абсолютные ссылки могут ломаться.
- **MinIO консоль**: при проблемах с редиректом — `MINIO_BROWSER_REDIRECT_URL=https://minio.${PUBLIC_HOST}`.
  Закладываем закомментированным, включаем если понадобится.
- **Синтаксис подстановки** (важно не перепутать): в `Caddyfile` переменная
  окружения берётся как `{$PUBLIC_HOST}` (фигурная скобка, потом `$`); в
  `docker-compose.infra.yml` — как `${PUBLIC_HOST}` (compose-интерполяция).
- **WebSocket** (Grafana Live, MinIO, RabbitMQ): Caddy `reverse_proxy`
  проксирует их автоматически, отдельная настройка не нужна.
- **HTTP→HTTPS**: Caddy редиректит 80→443 автоматически.
- **ACME email**: опционально (Caddy работает и без него). Можно добавить
  глобальный `email` позже.

## Что НЕ делаем (отклонённые альтернативы)

- **Правка безопасности с портами** — пользователь решил пока оставить
  Grafana/MinIO/RabbitMQ/backend/admin доступными напрямую по их HTTP-портам.
  В README оставляем пометку: при прямом заходе пароли идут открытым текстом;
  на будущее их можно закрыть за edge-Caddy, переключив публикацию портов на
  `127.0.0.1:PORT:PORT`.
- **TLS прямо во внутреннем Caddy `admin_miniapp`** — смешивает фронтенд-образ
  с edge/ops-задачами, требует пересборки фронта для смены прокси и тащит
  сертификаты в тот контейнер. Отклонено.
- **Пути вместо поддоменов** (`/grafana`, `/minio`) — требуют переписывания
  путей, часто ломают ассеты и вебсокеты. Поддомены через sslip.io чище и
  бесплатны. Отклонено.

## Изменения в файлах

- `infra/docker-compose.infra.yml` — новый сервис `caddy` + volumes
  `caddy_data`, `caddy_config`; env `GF_SERVER_ROOT_URL` для `grafana`.
- `infra/caddy/Caddyfile` — новый файл.
- `infra/.env` и `infra/.env.example` — новая переменная `PUBLIC_HOST`.
- `infra/README.md` — раздел про edge-Caddy, sslip.io, хостнеймы и пометка
  про прямые HTTP-порты.

## Критерии готовности

1. `docker compose ... up -d` поднимает сервис `caddy`.
2. По `https://<IP>.sslip.io` открывается админка с валидным сертификатом.
3. `https://grafana.<IP>.sslip.io`, `https://minio.<IP>.sslip.io`,
   `https://rabbitmq.<IP>.sslip.io` открывают свои панели по HTTPS.
4. HTTP-запросы редиректятся на HTTPS.
5. Сертификаты сохраняются в volume `caddy_data` и переживают рестарт.
