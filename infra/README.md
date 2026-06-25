# Инфраструктура Leadorub

Здесь живут два compose-файла и конфиги вспомогательных сервисов.

- `docker-compose.infra.yml` — внешние зависимости (БД, брокер, кэш, хранилище, мониторинг).
- `docker-compose.apps.yml` — сами приложения из `apps/` (backend, telegram-боты).
- `.env` — единый файл окружения для всего проекта (не коммитится). Шаблон — `.env.example`.

## Состав инфраструктуры

| Сервис | Назначение | Порты (host) | Web/UI |
|---|---|---|---|
| `postgres` | основная БД (бэкенд) | 5432 | — |
| `redis` | result backend и расписания taskiq | 6379 | — |
| `rabbitmq` | брокер сообщений (aio-pika, taskiq) | 5672, 15672 | http://localhost:15672 |
| `mongo` | хранилище модуля чата/сообщений | 27017 | — |
| `minio` | S3-хранилище для file_module | 9000, 9001 | http://localhost:9001 |
| `minio-init` | одноразовое создание бакета | — | — |
| `loki` | хранилище логов | 3100 | — |
| `alloy` | сбор логов контейнеров → Loki | 12345 | http://localhost:12345 |
| `grafana` | дашборды и просмотр логов | 3000 | http://localhost:3000 |

Логины/пароли для UI берутся из `.env` (RabbitMQ — `RABBITMQ_DEFAULT_*`, MinIO — `MINIO_ROOT_*`, Grafana — `GRAFANA_ADMIN_*`).

## Подготовка

```bash
cp .env.example .env
# затем заполни значения в .env (как минимум токены ботов user_bot/admin_bot)
```

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

## Мониторинг логов

`alloy` читает логи всех docker-контейнеров через docker-сокет и отправляет их в
`loki`. В Grafana (http://localhost:3000) источник данных Loki подключается
автоматически (provisioning) — открой **Explore → Loki** и фильтруй по лейблам
`container`, `compose_service`, `compose_project`.

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
