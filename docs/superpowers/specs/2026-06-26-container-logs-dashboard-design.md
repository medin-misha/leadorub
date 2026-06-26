# Container logs dashboard — design spec

Дата: 2026-06-26
Слой: `infra/` (Grafana provisioning, без изменений в коде приложений)

## Цель

Дать одним кликом просмотр логов всех docker-контейнеров в Grafana, близкий к
реальному времени, без ручной сборки запросов в Explore каждый раз. Делаем
провижн-дашборд «Логи контейнеров» с выбором контейнера, фильтром по уровню и
авто-обновлением.

## Контекст: пайплайн логов уже существует

Сбор логов был настроен ранее и работает:

```
alloy (docker socket) ──push──► loki (3100) ◄──query── grafana (datasource Loki, provisioning)
```

- `alloy` (`infra/alloy/config.alloy`) тейлит логи всех контейнеров через docker-сокет
  и проставляет лейблы `container`, `compose_service`, `compose_project`.
- `loki` (`infra/loki/config.yml`) хранит логи (tsdb v13, retention 168h).
- `grafana` подключает Loki как datasource автоматически
  (`infra/grafana/provisioning/datasources/loki.yml`).

Лейбл уровня `detected_level` Loki проставляет автоматически как **structured
metadata** (не индексный лейбл): он виден в стримах, но `label_values(detected_level)`
его не перечисляет. Поэтому фильтр по уровню делаем через pipeline
`| detected_level=~"$level"`, а список уровней задаём кастомной переменной.

## Что добавляем

Папка целиком уже примонтирована в Grafana (`./grafana/provisioning:ro`), поэтому
docker-compose **не меняем** — только кладём 2 файла:

```
infra/grafana/provisioning/dashboards/
├── provider.yml          # провайдер: грузить JSON-дашборды из этой папки
└── container-logs.json   # дашборд
```

### `provider.yml`

Провайдер дашбордов: `type: file`, `path: /etc/grafana/provisioning/dashboards`,
папка в Grafana «Leadorub», `allowUiUpdates: true` (можно докручивать руками),
`foldersFromFilesStructure: false`.

### `container-logs.json` (`uid: leadorub-container-logs`)

**Переменные:**

| Переменная | Тип | Значения | Назначение |
|---|---|---|---|
| `datasource` | datasource (loki) | текущий Loki | Не привязывать дашборд к конкретному uid; скрытая |
| `container` | query | `label_values(compose_service)` | Мультивыбор + All (`allValue=.+`) |
| `level` | custom | `info, warn, error, debug` | Мультивыбор + All (`allValue=.*`) |

Нюанс `allValue`:
- `container` → `.+` (контейнер всегда есть).
- `level` → `.*` — чтобы при «All» не отсеять строки **без** уровня (отсутствующий
  structured-metadata-лейбл матчится только `.*`, но не `.+`).

**Панели:**

1. **График объёма логов** (timeseries, бары, накопление по уровням):
   `sum by (detected_level) (count_over_time({compose_service=~"$container"} | detected_level=~"$level" [$__auto]))`
2. **Логи** (panel `logs`, новые сверху, время + перенос строк, раскрытие деталей):
   `{compose_service=~"$container"} | detected_level=~"$level"`

**Настройки:** окно `now-15m → now`, авто-обновление **5s** (опции 5s/10s/30s/1m),
таймзона браузера, `tags: [leadorub, logs]`.

## Реальное время

Real-time на дашборде = периодическое авто-обновление (перезапрос раз в 5s).
Настоящий Live tail (websocket-стрим) есть только в **Explore → Loki → Live** —
ограничение Grafana, фиксируем в README оба способа.

## Приложение: инцидент с кольцом Loki (починен по ходу работы)

При проверке выяснилось, что сбор логов фактически стоял. Причина — окружение
скачком ушло во времени вперёд (контейнеры стартовали 19 июня, «сейчас» — 26-е).
Loki в single-binary режиме держит кольцо ингестеров в памяти (`kvstore: inmemory`)
и проверяет здоровье по heartbeat; после скачка часов heartbeat «протух», ингестер
выпал из кольца → каждый `push` отбивался `HTTP 500 empty ring`.

Починка (выбор пользователя — чистый перезапуск с потерей устаревших логов):
1. `stop` + `rm` контейнеров `loki`/`alloy`.
2. `docker volume rm leadorub-apps_loki_data` (там только старые dev-логи, всё равно
   отвергаемые как «too far behind»).
3. Удаление orphan-дублей `leadorub-infra-loki-1` / `-alloy-1` (статус `Created`).
4. Пересоздание `loki`/`alloy` под проектом `leadorub-apps` обоими compose-файлами.

После этого ингестер `ACTIVE`, свежие логи принимаются и читаются.

**Сопутствующая находка (вне скоупа этой задачи):** коллизия имён compose-проектов
— `name: leadorub-apps` из `apps.yml` перебивает `name: leadorub-infra` из
`infra.yml` при совместном запуске. Из-за этого существует второй, почти полностью
мёртвый набор контейнеров `leadorub-infra-*` (в основном `Created`). Стоит вынести
отдельной задачей.

## Вне скоупа

- Алерты по логам.
- Изменение конфигов `alloy`/`loki`/datasource.
- Разбор коллизии имён проектов `leadorub-apps` vs `leadorub-infra`.
