# Leadorub

## Описание проекта

Уневерсальная система для сбора лидов в телеграмме. Основные клиенты - инфлюенсеры.
Преимущество системы в том, что она из коробки имеет следующий функционал:
- Сбор и управление лидами в телеграм боте
- Сбор статистики по каждому отдельному пользователю
- Чат встроенный модуль чата от имени бота через админ панель
- Массовая рассылка

## Кто ты 

Ты программист, пишущий продакшен код в проекте, на python (бекенд и телеграм боты), и JavaScript (VueJS)

## Архитектура и стек
Система состоит из следующих функциональных модулей:
- Бекенд (управляет всеми данными системы.)
- Админ-панель (позволяет управлять и просматривать данные бекенда.)
- Админ-бот (телеграм бот MiniApp которого админ панель. Его функция уведомление администраторов о событии)
- Пользовательский бот (телеграм бот с которым взаимодействует конечный пользователь)

Стек: 
- Python: Uv, FastAPI, SQLAlchemy, Pydantic, Aiogramm, Aio-http, Botocore, Aiopika, Taskiq
- JavaScript: VueJS, Axios
- Ifrastructure: Caddy, PostgreSQL, RabbitMQ, Redis, Grafana

Структура папок и файлов следующая:
- `apps/` - сами сервисы# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#   Usually these files are written by a python script from a template
#   before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py.cover
*.lcov
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
# Pipfile.lock

# UV
#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
# uv.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
# poetry.lock
# poetry.toml

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#   pdm recommends including project-wide configuration in pdm.toml, but excluding .pdm-python.
#   https://pdm-project.org/en/latest/usage/project/#working-with-version-control
# pdm.lock
# pdm.toml
.pdm-python
.pdm-build/

# pixi
#   Similar to Pipfile.lock, it is generally recommended to include pixi.lock in version control.
# pixi.lock
#   Pixi creates a virtual environment in the .pixi directory, just like venv module creates one
#   in the .venv directory. It is recommended not to include this directory in version control.
.pixi/*
!.pixi/config.toml

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule*
celerybeat.pid

# Redis
*.rdb
*.aof
*.pid

# RabbitMQ
mnesia/
rabbitmq/
rabbitmq-data/

# ActiveMQ
activemq-data/

# SageMath parsed files
*.sage.py

# Environments
.env
.envrc
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#   JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#   be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#   and can be added to the global gitignore or merged into this file.  For a more nuclear
#   option (not recommended) you can uncomment the following to ignore the entire idea folder.
# .idea/

# Abstra
#   Abstra is an AI-powered process automation framework.
#   Ignore directories containing user credentials, local state, and settings.
#   Learn more at https://abstra.io/docs
.abstra/

# Visual Studio Code
#   Visual Studio Code specific template is maintained in a separate VisualStudioCode.gitignore 
#   that can be found at https://github.com/github/gitignore/blob/main/Global/VisualStudioCode.gitignore
#   and can be added to the global gitignore or merged into this file. However, if you prefer, 
#   you could uncomment the following to ignore the entire vscode folder
# .vscode/
# Temporary file for partial code execution
tempCodeRunnerFile.py

# Ruff stuff:
.ruff_cache/

# PyPI configuration file
.pypirc

# Marimo
marimo/_static/
marimo/_lsp/
__marimo__/

# Streamlit
.streamlit/secrets.toml
- `infra/` - инфраструктура
- `infra/docker-compose.apps.yml` - запуск сервисов `apps/`
- `infra/docker-compose.infra.yml` - запуск инфраструктуры 

Все переменные окружения читаються строго из `infra/.env`
В каждом модулей сервиса есть свой `.claude/CLAUDE.md` в котором храниться исчерпывающая документация по сервису.

## Команды и пути
Сдесь пока ничего нет

## Правила
1. Ты не можешь менять `.claude/CLAUDE.md` и `README.md` в корне проекта не посоветывавшись зарание со мной
2. После написания кода который как либо меняет логику API, или добавляет новый функционал, синхронизируй новый функционал с `apps/<module>/.claude/CLAUDE.md` а так же `apps/<module>/README.md`. CLAUDE.md каждого отдельного сервиса можешь менять самостоятельно
3. Пиши в коде комментарии и\или документацию
4. Используй аннотации типов
5. Используй логирование
6. Придерживайся модульной архитектуры проекта
7. Перед коммитами используй `ruff format`

## Контекст принятия решений
1. Если встаёт выбор читаемость или эффективность выбирай эффективность, но незабудь писать комментарии
2. Если встаёт выбор гибкости или эффективности выбирай гибкость

@include .claude/skills/*/SKILL.md
@include apps/*/.claude/CLAUDE.md