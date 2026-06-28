# Edge-Caddy + HTTPS через sslip.io — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить edge-Caddy, который терминирует HTTPS через sslip.io и проксирует внешний трафик на внутренние сервисы (админка, Grafana, MinIO, RabbitMQ).

**Architecture:** Отдельный сервис `caddy` (официальный образ `caddy:2-alpine`) в `docker-compose.infra.yml` — единственный публичный сервис на портах 80/443. По хостнейму (`{$PUBLIC_HOST}` и поддомены `grafana.`/`minio.`/`rabbitmq.`) проксирует на внутренние контейнеры по docker-сети `leadorub`. Внутренний Caddy в `admin_miniapp` не трогаем. Сертификаты Let's Encrypt Caddy получает сам, хранит в именованном volume.

**Tech Stack:** Docker Compose, Caddy 2, sslip.io (wildcard DNS), Let's Encrypt (ACME).

**Спека:** `docs/superpowers/specs/2026-06-28-edge-caddy-https-sslip-design.md`

## Global Constraints

- Все переменные окружения читаются строго из `infra/.env` (compose запускается из `infra/`).
- IP сервера задаётся ОДИН раз через переменную `PUBLIC_HOST` (формат `<IP>.sslip.io`).
- Синтаксис подстановки переменной различается: в `Caddyfile` — `{$PUBLIC_HOST}`, в `docker-compose.infra.yml` — `${PUBLIC_HOST}`.
- Индентация в `Caddyfile` — табами (как в существующем `apps/admin_miniapp/Caddyfile`).
- Комментарии в коде — на русском (стиль проекта).
- Сертификаты должны переживать рестарт → именованные volumes `caddy_data` / `caddy_config`.
- Сопутствующую правку безопасности (закрытие прямых HTTP-портов) НЕ делаем — решение пользователя.
- Все команды валидации запускаются из корня репозитория `/home/misha/code/leadorub`.

---

## File Structure

- **Create:** `infra/caddy/Caddyfile` — конфиг edge-прокси (4 сайта).
- **Modify:** `infra/docker-compose.infra.yml` — сервис `caddy`, volumes `caddy_data`/`caddy_config`, env `GF_SERVER_ROOT_URL` для `grafana`.
- **Modify:** `infra/.env.example` — переменная `PUBLIC_HOST` + пояснение.
- **Modify:** `infra/.env` — переменная `PUBLIC_HOST` (локальный плейсхолдер).
- **Modify:** `infra/README.md` — раздел про edge-Caddy и хостнеймы.

---

### Task 1: Caddyfile и переменная PUBLIC_HOST

**Files:**
- Create: `infra/caddy/Caddyfile`
- Modify: `infra/.env.example`
- Modify: `infra/.env`

**Interfaces:**
- Consumes: ничего (первая задача).
- Produces: файл `infra/caddy/Caddyfile`, который читает env-переменную `PUBLIC_HOST` как `{$PUBLIC_HOST}`; переменную `PUBLIC_HOST` в `infra/.env` (формат `<IP>.sslip.io`). Task 2 монтирует Caddyfile и пробрасывает `PUBLIC_HOST` в контейнер.

- [ ] **Step 1: Создать `infra/caddy/Caddyfile`**

Индентация — табами.

```caddyfile
# ============================================================================
# Leadorub — edge reverse proxy (Caddy).
# Единственный сервис, открытый наружу (порты 80/443). Терминирует HTTPS:
# сертификаты Let's Encrypt Caddy получает и обновляет сам (ACME-challenge
# проходит по портам 80/443, которые открыты на сервере).
#
# PUBLIC_HOST приходит из окружения контейнера (см. docker-compose.infra.yml),
# значение вида <IP>.sslip.io. sslip.io резолвит и поддомены:
# grafana.<IP>.sslip.io, minio.<IP>.sslip.io и т.д. — все в тот же IP.
#
# Внутрь docker-сети `leadorub` Caddy ходит по простому HTTP (там шифровать
# незачем) и обращается к сервисам по их именам контейнеров.
# ============================================================================

# Админ-панель. Внутри admin_miniapp свой Caddy: раздаёт Vue-статику и
# проксирует /api на backend (один origin → нет CORS). Мы просто проксируем
# на него весь хост.
{$PUBLIC_HOST} {
	reverse_proxy admin_miniapp:80
}

# Grafana — дашборды и просмотр логов.
grafana.{$PUBLIC_HOST} {
	reverse_proxy grafana:3000
}

# MinIO — веб-консоль S3-хранилища.
minio.{$PUBLIC_HOST} {
	reverse_proxy minio:9001
}

# RabbitMQ — management UI брокера сообщений.
rabbitmq.{$PUBLIC_HOST} {
	reverse_proxy rabbitmq:15672
}
```

- [ ] **Step 2: Добавить `PUBLIC_HOST` в `infra/.env.example`**

Добавить новый блок (удобно — сразу после шапки файла или рядом с Grafana-блоком):

```dotenv
# ----------------------------------------------------------------------------
# Деплой / edge-Caddy (HTTPS через sslip.io)
# PUBLIC_HOST — публичный хост системы вида <IP>.sslip.io, где <IP> — белый
# (публичный) IP сервера. sslip.io резолвит и поддомены: grafana.<IP>.sslip.io,
# minio.<IP>.sslip.io, rabbitmq.<IP>.sslip.io — все указывают на тот же IP.
# Caddy выпускает TLS-сертификаты Let's Encrypt автоматически (нужны открытые
# порты 80/443). Для локального запуска без белого IP оставь как есть — тогда
# edge-Caddy поднимется, но валидный сертификат не получит.
# ----------------------------------------------------------------------------
PUBLIC_HOST=1.2.3.4.sslip.io
```

- [ ] **Step 3: Добавить `PUBLIC_HOST` в `infra/.env`**

Добавить ту же строку в реальный `.env` (значение пока плейсхолдер — на сервере заменить `1.2.3.4` на белый IP):

```dotenv
PUBLIC_HOST=1.2.3.4.sslip.io
```

- [ ] **Step 4: Провалидировать Caddyfile**

Caddy сам проверяет синтаксис конфига. Подставляем тестовый `PUBLIC_HOST` через env:

Run:
```bash
docker run --rm \
  -e PUBLIC_HOST=1.2.3.4.sslip.io \
  -v "$PWD/infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```
Expected: в выводе есть `Valid configuration` (предупреждения о том, что команда экспериментальна — норм).

- [ ] **Step 5: Commit**

```bash
git add infra/caddy/Caddyfile infra/.env.example infra/.env
git commit -m "feat(infra): add edge-Caddy Caddyfile and PUBLIC_HOST env"
```

---

### Task 2: Сервис caddy в docker-compose.infra.yml

**Files:**
- Modify: `infra/docker-compose.infra.yml`

**Interfaces:**
- Consumes: `infra/caddy/Caddyfile` и переменную `PUBLIC_HOST` из Task 1.
- Produces: запущенный сервис `caddy` на портах 80/443/443udp; volumes `caddy_data`, `caddy_config`; env `GF_SERVER_ROOT_URL` на сервисе `grafana`.

- [ ] **Step 1: Добавить сервис `caddy`**

В секцию `services:` файла `infra/docker-compose.infra.yml` (например, после блока `grafana`) добавить:

```yaml
  # --------------------------------------------------------------------------
  # Caddy — edge reverse proxy. Единственный сервис, открытый наружу (80/443).
  # Терминирует HTTPS (Let's Encrypt через sslip.io) и проксирует по хостнейму
  # на внутренние сервисы. PUBLIC_HOST (<IP>.sslip.io) берётся из infra/.env и
  # пробрасывается в контейнер — Caddyfile читает его как {$PUBLIC_HOST}.
  # depends_on не указываем намеренно: reverse_proxy сам ретраит апстримы,
  # пока они поднимаются (вернёт 502 до готовности), а admin_miniapp вообще из
  # другого compose-файла — зависимость между файлами невозможна.
  # --------------------------------------------------------------------------
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3 (QUIC)
    environment:
      PUBLIC_HOST: ${PUBLIC_HOST}
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data       # сертификаты — переживают рестарт
      - caddy_config:/config
    networks:
      - leadorub
```

- [ ] **Step 2: Добавить `GF_SERVER_ROOT_URL` в сервис `grafana`**

В блоке `grafana:` → `environment:` добавить строку (рядом с существующими `GF_*`):

```yaml
      # Внешний URL за reverse-proxy — иначе редиректы и абсолютные ссылки ломаются.
      GF_SERVER_ROOT_URL: https://grafana.${PUBLIC_HOST}
```

- [ ] **Step 3: Зарегистрировать volumes**

В секции `volumes:` (в конце файла) к существующим добавить:

```yaml
  caddy_data:
  caddy_config:
```

- [ ] **Step 4: Провалидировать compose**

`docker compose config` парсит файл и подставляет переменные из `.env` — ловит синтаксис и опечатки в интерполяции.

Run:
```bash
docker compose --env-file infra/.env -f infra/docker-compose.infra.yml config >/dev/null && echo "compose OK"
```
Expected: `compose OK` без ошибок.

- [ ] **Step 5: Проверить, что в итоговом конфиге подставился хост**

Run:
```bash
docker compose --env-file infra/.env -f infra/docker-compose.infra.yml config | grep -E "GF_SERVER_ROOT_URL|PUBLIC_HOST"
```
Expected: видно `PUBLIC_HOST: 1.2.3.4.sslip.io` (или твой IP) и `GF_SERVER_ROOT_URL: https://grafana.1.2.3.4.sslip.io`.

- [ ] **Step 6: Commit**

```bash
git add infra/docker-compose.infra.yml
git commit -m "feat(infra): add caddy edge service and grafana root_url"
```

---

### Task 3: Документация в infra/README.md

**Files:**
- Modify: `infra/README.md`

**Interfaces:**
- Consumes: всё из Task 1–2 (имена хостов, переменная `PUBLIC_HOST`).
- Produces: ничего (документация).

- [ ] **Step 1: Прочитать текущий README, найти подходящее место**

Run:
```bash
sed -n '1,60p' infra/README.md
```
Цель — найти раздел про сервисы/порты или конец файла, куда логично добавить раздел про edge-Caddy.

- [ ] **Step 2: Добавить раздел про edge-Caddy**

Вставить раздел (адаптируй заголовки под структуру README):

```markdown
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
ACME-challenge). Сертификаты лежат в volume `caddy_data` — не удаляй его, иначе
Caddy будет перевыпускать сертификаты и может упереться в rate limits.

> ⚠️ Прямые HTTP-порты сервисов (Grafana 3000, MinIO 9001, RabbitMQ 15672,
> backend 8000, admin 8080) сейчас остаются опубликованными — при заходе по ним
> напрямую пароли идут открытым текстом. Когда понадобится закрыть: смени их
> публикацию на `127.0.0.1:PORT:PORT` (edge-Caddy достучится по внутренней сети),
> снаружи останется только HTTPS.
```

- [ ] **Step 3: Commit**

```bash
git add infra/README.md
git commit -m "docs(infra): document edge-Caddy and sslip.io HTTPS setup"
```

---

### Task 4 (на сервере): боевая проверка

> Выполняется на сервере с белым IP, НЕ локально (локально Let's Encrypt не выдаст сертификат на sslip.io-хост без публичной доступности по 80/443).

- [ ] **Step 1: Прописать реальный IP**

В `infra/.env` заменить `PUBLIC_HOST=1.2.3.4.sslip.io` на белый IP сервера.

- [ ] **Step 2: Поднять стек**

Run:
```bash
docker compose -f infra/docker-compose.infra.yml -f infra/docker-compose.apps.yml up --build -d
```
Expected: сервис `caddy` в статусе `Up`.

- [ ] **Step 3: Проверить выдачу сертификата в логах**

Run:
```bash
docker compose -f infra/docker-compose.infra.yml logs caddy | grep -iE "certificate|obtain|error"
```
Expected: строки про успешное получение сертификата, без повторяющихся ошибок ACME.

- [ ] **Step 4: Проверить хосты по HTTPS**

Run (подставь свой IP):
```bash
for h in "" grafana. minio. rabbitmq.; do
  echo "== ${h}<IP>.sslip.io =="
  curl -sS -o /dev/null -w "%{http_code}\n" "https://${h}<IP>.sslip.io"
done
```
Expected: коды `200`/`302` (для Grafana/MinIO/RabbitMQ — редирект на их логин), валидный TLS (без `-k`).

- [ ] **Step 5: Проверить HTTP→HTTPS редирект**

Run:
```bash
curl -sS -o /dev/null -w "%{http_code} -> %{redirect_url}\n" "http://<IP>.sslip.io"
```
Expected: `308 -> https://<IP>.sslip.io/` (Caddy редиректит на HTTPS).

---

## Self-Review

**Spec coverage:**
- Цель (HTTPS через sslip.io без домена) → Task 1–2. ✅
- 4 публичных сервиса с поддоменами → Caddyfile в Task 1, проверка в Task 4. ✅
- Один env-var `PUBLIC_HOST` → Task 1 (env), Task 2 (проброс в контейнер). ✅
- edge-Caddy в infra-compose, образ `caddy:2-alpine`, volumes `caddy_data`/`caddy_config` → Task 2. ✅
- Нюанс Grafana `GF_SERVER_ROOT_URL` → Task 2, Step 2. ✅
- Нюанс MinIO `MINIO_BROWSER_REDIRECT_URL` — заложен в спеке как опциональный (включаем только при проблеме редиректа); намеренно НЕ добавлен в базовый конфиг, чтобы не усложнять. Описан в спеке. ✅
- Порты 80/443 (+udp) → Task 2. ✅
- README с пометкой про прямые HTTP-порты → Task 3. ✅
- Критерии готовности (сертификат, 4 хоста, HTTP→HTTPS редирект, persistence) → Task 4. ✅

**Placeholder scan:** плейсхолдеров нет; весь код и команды приведены полностью. `1.2.3.4` — намеренный пример IP, помечен как заменяемый.

**Type consistency:** имена согласованы во всех задачах — переменная `PUBLIC_HOST`, сервис `caddy`, апстримы `admin_miniapp:80` / `grafana:3000` / `minio:9001` / `rabbitmq:15672`, volumes `caddy_data` / `caddy_config`.
