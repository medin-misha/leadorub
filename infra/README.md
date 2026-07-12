# Инфраструктура Leadorub

Здесь живут два compose-файла и конфиги вспомогательных сервисов.

- `docker-compose.infra.yml` — внешние зависимости (БД, брокер, кэш, хранилище, мониторинг).
- `docker-compose.apps.yml` — сами приложения из `apps/` (backend, telegram-боты).
- `.env` — единый файл окружения для всего проекта (не коммитится). Шаблон — `.env.example`.

## Состав инфраструктуры

| Сервис | Назначение | Порты (host) | Web/UI |
|---|---|---|---|
| `postgres` | основная БД (бэкенд) | — | — |
| `redis` | result backend и расписания taskiq | — | — |
| `rabbitmq` | брокер сообщений (aio-pika, taskiq) | 127.0.0.1:15672 | http://localhost:15672 |
| `minio` | S3-хранилище для file_module | 127.0.0.1:9001 | http://localhost:9001 |
| `minio-init` | одноразовое создание бакета | — | — |
| `loki` | хранилище логов | — | — |
| `alloy` | сбор логов контейнеров → Loki | — | — |
| `grafana` | дашборды и просмотр логов | 127.0.0.1:3000 | http://localhost:3000 |

Логины/пароли для UI берутся из `.env` (RabbitMQ — `RABBITMQ_DEFAULT_*`, MinIO — `MINIO_ROOT_*`, Grafana — `GRAFANA_ADMIN_*`).

## Подготовка

```bash
cp .env.example .env
# затем заполни значения в .env (как минимум токены ботов user_bot/admin_bot)
```

Для дополнительной защиты инфраструктурных панелей сгенерируй отдельный пароль:

```bash
docker run --rm caddy:2.11.4-alpine caddy hash-password --plaintext 'strong-password'
```

Запиши логин в `EDGE_ADMIN_USER`, а результат команды — в
`EDGE_ADMIN_PASSWORD_HASH`. В `.env` каждый символ `$` в хеше нужно удвоить
(`$` → `$$`), иначе Compose воспримет его как подстановку переменной. Это Basic
Auth на edge-Caddy; после него Grafana, MinIO или RabbitMQ всё равно запросят
свои учётные данные.

> **Важно про `.env`.** Docker Compose ищет `.env` в текущей директории, а не рядом
> с compose-файлом. Поэтому запускай команды **из папки `infra/`** (как ниже) либо
> добавляй флаг `--env-file infra/.env`. Иначе переменные окажутся пустыми.

## Запуск

Инфраструктуру поднимаем **первой** — она создаёт общую сеть `leadorub`, к которой
подключаются приложения.

```bash
# 1. Инфраструктура
docker compose -f docker-compose.infra.yml up -d

# 2. Приложения (сборка образов при первом запуске)
docker compose -f docker-compose.apps.yml up -d --build
```

Остановка:

```bash
docker compose -f docker-compose.apps.yml down
docker compose -f docker-compose.infra.yml down
# с удалением данных (volumes):
docker compose -f docker-compose.infra.yml down -v
```

## Сеть

`docker-compose.infra.yml` создаёт bridge-сеть с фиксированным именем `leadorub`.
`docker-compose.apps.yml` подключается к ней как `external`. Если запускаешь apps
без infra, создай сеть вручную:

```bash
docker network create leadorub
```

## Edge-Caddy и HTTPS (sslip.io)

Внешний трафик идёт через edge-Caddy — единственный сервис, открытый наружу
(порты 80/443). Он терминирует HTTPS и по хостнейму проксирует на внутренние
сервисы. Сертификаты Let's Encrypt Caddy получает и обновляет сам.

Домен не нужен — используем sslip.io: хостнейм с IP внутри резолвится в этот
IP, причём поддомены тоже (`grafana.<IP>.sslip.io` → `<IP>`).

**Настройка:** в `infra/.env` задай `PUBLIC_HOST=<белый-IP>.sslip.io`.

**Хостнеймы после запуска:**

| Сервис | URL |
|---|---|
| Админ-панель | `https://<IP>.sslip.io` |
| Grafana | `https://grafana.<IP>.sslip.io` |
| MinIO консоль | `https://minio.<IP>.sslip.io` |
| RabbitMQ UI | `https://rabbitmq.<IP>.sslip.io` |

**Требования:** публичный IP, открытые порты 80/443 (нужны Let's Encrypt для
ACME-challenge), для HTTP/3 — также UDP/443. Сертификаты лежат в volume
`caddy_data` — не удаляй его, иначе Caddy будет перевыпускать сертификаты при
каждом пересоздании контейнера.

**Про rate limits sslip.io:** sslip.io — общий публичный домен, и Let's Encrypt
считает весь `sslip.io` за один зарегистрированный домен с общим (на всех
пользователей) лимитом выпуска. То есть изредка выпуск сертификата может не
пройти не по твоей вине. Это смягчается тем, что Caddy 2 по умолчанию пробует
двух удостоверяющих центра (Let's Encrypt и ZeroSSL) и сам переключается на
запасного. Для настоящего прода надёжнее купить дешёвый домен
(`PUBLIC_HOST=admin.example.com`) — тогда и лимиты, и доступность DNS только твои.

**MinIO консоль за поддоменом:** если после логина консоль редиректит не туда
(на http или на чужой хост), раскомментируй `MINIO_BROWSER_REDIRECT_URL` в
сервисе `minio` (см. `docker-compose.infra.yml`). Также учти: образ
`minio/minio:latest` — «плавающий» тег, и в свежих community-сборках веб-консоль
может быть урезана по функционалу.

Прямые HTTP-порты сервисов привязаны к `127.0.0.1`: они удобны для диагностики
на самом сервере, но недоступны извне. Edge-Caddy продолжает обращаться к ним
по общей Docker-сети. Публично compose открывает только TCP 80/443 и UDP 443.

Если локальный UI нужен на другом адресе, не ослабляй основной compose-файл:
создай локальный override с нужным bind либо используй SSH-туннель, например
`ssh -L 3000:127.0.0.1:3000 user@server`. Публикация на `0.0.0.0` обходит TLS и
дополнительный Basic Auth, поэтому подходит только для явно доверенной сети.

## Мониторинг логов

`alloy` читает логи всех docker-контейнеров через docker-сокет и отправляет их в
`loki`. В Grafana (http://localhost:3000) источник данных Loki и дашборд логов
подключаются автоматически (provisioning).

Два способа смотреть логи:

- **Дашборд «Логи контейнеров»** (папка **Leadorub**) — выбор контейнера, фильтр
  по уровню (`info/warn/error/debug`), график объёма логов и общая лента. Ниже —
  секция «Логи по контейнерам»: отдельное окно на каждый выбранный контейнер
  (repeat-панель по `$container`, по 2 в ряд; при `All` — по всем). Обновляется
  каждые 5с (автоrefresh), интервал и окно времени меняются в правом верхнем углу.
  Файлы: `grafana/provisioning/dashboards/`.
- **Explore → Loki** — произвольные LogQL-запросы и режим **Live** (настоящий
  live-tail, стрим без перезапросов). Фильтры по лейблам `container`,
  `compose_service`, `compose_project`.

> **Real-time на дашборде vs Live tail.** Дашборд обновляется периодическим
> перезапросом (автоrefresh 5с) — это «почти реальное время». Настоящий потоковый
> live-tail есть только в **Explore → Loki → Live**: это ограничение Grafana, на
> дашбордах режима Live нет.

> **Если логи перестали идти после простоя/скачка системного времени.** Loki в
> single-binary режиме держит кольцо ингестеров в памяти и проверяет здоровье по
> heartbeat. При резком скачке часов кольцо «протухает», и `push` от `alloy` начинает
> отбиваться `HTTP 500 empty ring` (видно в `docker logs <loki>`). Лечится чистым
> перезапуском с очисткой состояния:
> ```bash
> docker compose -f docker-compose.infra.yml -f docker-compose.apps.yml rm -sf loki alloy
> docker volume rm leadorub-apps_loki_data   # удаляет старые логи
> docker compose -f docker-compose.infra.yml -f docker-compose.apps.yml up -d loki alloy
> ```

## Нюансы

- **Дублирование кред в `.env`.** Пароли заданы дважды: как параметры сервисов
  (`POSTGRES_PASSWORD` и т.п.) и внутри строк подключения приложений
  (`database_url` и т.п.). При смене пароля меняй оба места.
  Исключение — Redis: единый `redis_password`, бэкенд сам собирает `redis_url`
  (дублирования нет).
- **Хосты в строках подключения** — это имена docker-сервисов (`postgres`,
  `rabbitmq`, ...), а не `localhost`. Если запускаешь приложение на хосте вне
  docker, переопредели соответствующие переменные на `localhost`.
- **Миграции БД** автоматически не применяются. Накатить вручную:
  ```bash
  docker compose -f docker-compose.apps.yml exec backend uv run alembic upgrade head
  ```
