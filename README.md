# Power BI Report Visual Monitoring

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Documentation site (GitHub Pages):** [https://svergio.github.io/Power-bi-report-visual-monitoring/](https://svergio.github.io/Power-bi-report-visual-monitoring/) — bilingual **EN/RU** rationale for visual monitoring, KPI canvas coverage, and an observability cost model (render + diff vs repeated warehouse queries).

**Wiki (hub, EN/RU):** [https://github.com/svergio/Power-bi-report-visual-monitoring/wiki](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki) — expanded hub plus deep pages ([Architecture](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline), [Operations](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning), [Limitations](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons)); Markdown sources live under [`wiki/`](wiki/).

**AI / Cursor maintainer notes (Wiki + Pages):** [`docs/agent/`](docs/agent/) — [`CLAUDE.md`](docs/agent/CLAUDE.md) (general doc agent rules), [`CURSOR.md`](docs/agent/CURSOR.md) (Wiki sync and optional `Co-authored-by` policy for doc-only commits).

**Also:** [Database schema `docs/DATABASE.md` (EN/RU)](docs/DATABASE.md) · [DDL `schema.sql`](schema.sql) · [Roadmap `ROADMAP.md` (EN/RU)](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

## What this is

Open-source **visual monitoring** for Power BI Report Server and published web reports: headless Chrome (Selenium), screenshot baseline, quadtree/MSE-style diff, optional gzip-compressed XOR delta, **PostgreSQL** for history, in-process scheduler with backpressure.

This is **not** a substitute for Microsoft Usage Metrics (consumption analytics) or Performance Analyzer (per-visual timing in Desktop). It answers: *did the rendered report surface drift from an agreed baseline?*

## Features

- Selenium rendering with retries, backoff, and re-authentication when the session expires
- Visual comparison (quadtree + MSE) and perceptual hash (dhash) metadata
- XOR delta storage (gzip) for forensic reconstruction vs the init baseline image
- psycopg3 connection pool to PostgreSQL
- In-process job queue and worker pool with load limits between restarts

## Use cases

- Catch silent regressions (filters, conditional formatting, wrong measure) while refresh stays green
- Scheduled **visual regression** checks for executive dashboards and operational wallboards
- Historical audit trail in `monitoring_checks` for compliance and post-incident review

## Quick start (English)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH=src       # Windows PowerShell: $env:PYTHONPATH = "src"
cp .env.example .env      # edit PG_* and optional POWERBI_*
cp example_reports.json reports.json   # edit URLs
python -m pbimonitor --init-db
python -m pbimonitor --build
python -m pbimonitor --check YOUR_REPORT_ID
python -m pbimonitor --start
```

Docker: `docker compose up --build -d`

For a full Russian walkthrough, Docker service names, metrics, and troubleshooting, see **Russian section** below.

---

## Русская документация

Открытый мониторинг визуальной отдачи отчётов Power BI Report Server и веб-отчётов Power BI. Проект разбит на слои DDD (`domain`, `application`, `infrastructure`, `config`) и использует:

- рендеринг через Selenium с повторами (retry/backoff) и повторной авторизацией;
- визуальное сравнение: quadtree и MSE;
- хранение XOR-дельты с gzip;
- PostgreSQL и пул соединений psycopg3;
- очередь задач в процессе и ограничение нагрузки (backpressure).

**Сайт с обоснованием подхода (GitHub Pages, EN/RU на одной странице):** [https://svergio.github.io/Power-bi-report-visual-monitoring/](https://svergio.github.io/Power-bi-report-visual-monitoring/)

**Вики (хаб, EN/RU):** [https://github.com/svergio/Power-bi-report-visual-monitoring/wiki](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki) — расширенный хаб и отдельные страницы ([Architecture](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline), [Operations](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning), [Limitations](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons)); исходники Markdown в [`wiki/`](wiki/).

**Заметки для агента (Wiki + Pages):** [`docs/agent/`](docs/agent/) — [`CLAUDE.md`](docs/agent/CLAUDE.md), [`CURSOR.md`](docs/agent/CURSOR.md) (синк Wiki и политика `Co-authored-by` только для doc-only коммитов).

**Схема БД (EN/RU):** [docs/DATABASE.md](docs/DATABASE.md) · **DDL:** [schema.sql](schema.sql) · **Дорожная карта (EN/RU):** [ROADMAP.md](ROADMAP.md)

### Команды CLI (`python -m pbimonitor`)

| Флаг | Действие |
|------|----------|
| `--env-file` | Путь к `.env` (по умолчанию `.env`) |
| `--init-db` | Создать схему при необходимости и применить `schema.sql` |
| `--build` | Построить базовые снимки для всех отчётов из конфигурации |
| `--check REPORT_ID` | Одна проверка по идентификатору отчёта |
| `--start` | Запустить цикл планировщика |

Справка по флагам на английском: `python -m pbimonitor --help`.

### Быстрый старт

#### 1) Установка

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Чтобы модуль `pbimonitor` находился при `python -m pbimonitor`, добавьте каталог `src` в `PYTHONPATH`:

```bash
# Linux / macOS
export PYTHONPATH=src
```

```powershell
# Windows PowerShell
$env:PYTHONPATH = "src"
```

При необходимости: `pip install -e .` из корня репозитория.

#### 2) Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

- подключение к PostgreSQL: `PG_HOST`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_SCHEMA`;
- политика схемы: `PG_SCHEMA_ALLOWLIST`; команда `python -m pbimonitor --init-db` выполняет `CREATE SCHEMA IF NOT EXISTS` для `PG_SCHEMA` и накатывает `schema.sql`;
- при необходимости доступ к Power BI: `POWERBI_USERNAME`, `POWERBI_PASSWORD`;
- среда исполнения: `REPORTS_FILE`, число воркеров, пороги, параметры повторов.

#### 3) Конфигурация отчётов

Используйте `reports.json` или скопируйте `example_reports.json` и подставьте свои URL:

```json
{
  "reports": [
    {
      "id": "daily_sales",
      "name": "Daily Sales Overview",
      "url": "https://powerbi.example.com/reports/daily-sales",
      "interval": 15,
      "start_time": "07:00",
      "threshold": 5.0,
      "enabled": true
    }
  ]
}
```

#### 4) Схема БД и запуск

```bash
python -m pbimonitor --init-db
python -m pbimonitor --build
python -m pbimonitor --check daily_sales
python -m pbimonitor --start
```

### Схема базы данных (кратко)

Список отчётов и их URL задаётся в **`reports.json`**, а не в PostgreSQL. В БД хранятся только результаты мониторинга.

- **`baselines`** — по одной строке на отчёт: `report_id`, `report_name`, `hash_value` (dhash последнего базового снимка), метки времени. Файлы снимков лежат в `Data/baselines` и `Data/changes/<report_id>/`.
- **`monitoring_checks`** — журнал каждой проверки: `status` (`changed` | `unchanged` | `error` | `baseline_created`), `diff_percent` (визуальное отличие относительно baseline), `screenshot_hash`, сжатая XOR-дельта к **init**-baseline (`delta_compressed`), `error`, `duration_sec`, `next_check_at`.
- Представления **`v_latest_checks`** и **`v_report_stats`** — последняя строка по отчёту и агрегаты.
- Функция **`cleanup_old_checks(days)`** — удаление старых строк с сохранением последней записи по каждому `report_id`.

Подробные описания колонок и связь с кодом — в [docs/DATABASE.md](docs/DATABASE.md); DDL и комментарии на английском — в [schema.sql](schema.sql).

### Docker

```bash
docker compose up --build -d
```

Сервисы:

- `web` — процесс pbimonitor;
- `db` — PostgreSQL;
- `redis` (опциональный профиль): зарезервирован под будущую распределённую очередь.

### Архитектура DDD

```
src/pbimonitor/
  domain/
    reports/        # сущности, quadtree, XOR-сервисы
    sessions/       # сущности и сервисы сессии авторизации
  infrastructure/
    selenium/       # SeleniumClient, повторы, исключения повторного входа
    storage/        # адаптер пула PostgreSQL
    queue/          # планировщик в процессе, воркеры, backpressure
  application/
    usecases/       # check_report, diff_report, update_storage
    dto/
  config/
    settings.py     # pydantic BaseSettings и проверка reports.json
  main.py           # точка входа CLI
```

### Метрики времени выполнения

Приложение пишет снимок метрик:

- `render_duration_ms`
- `diff_duration_ms`
- `delta_size_bytes`
- `below_diff_threshold_rate` (доля проверок, где процент визуального отличия ниже порога `threshold` отчёта)

### Требования

- Python 3.10+
- PostgreSQL 12+
- Chrome/Chromium, совместимый с Selenium
- Доступ с хоста монитора к Power BI Report Server или размещённым в сети URL отчётов Power BI

### Требования к PostgreSQL

- Пользователь БД должен иметь право создавать схему (или целевую схему) и объекты в `PG_SCHEMA` (таблицы, индексы, представления, функции).
- `schema.sql` применяется командой `python -m pbimonitor --init-db` (при отсутствии схемы она создаётся, затем выполняется DDL).
- Таблицы: `baselines`, `monitoring_checks`.

### Требования к Power BI

- Отчёты должны открываться с машины, где запущен монитор.
- Для сред с интегрированной аутентификацией при необходимости задайте `POWERBI_AUTH_SERVER_WHITELIST`.
- Для простой Basic-auth укажите `POWERBI_USERNAME` и `POWERBI_PASSWORD` в `.env`.

### GitHub Pages

После первого успешного деплоя Actions убедитесь, что в настройках репозитория **Pages** включён источник **GitHub Actions**. Сайт публикуется из артефакта каталога `docs/` (статический `index.html` и сопутствующие файлы).

### Безопасность

- Не коммитьте `.env`.
- В продакшене используйте хранилища секретов (Kubernetes Secrets, Vault, облачные хранилища).
- Регулярно меняйте пароли БД и учётные данные отчётов.
- Кеш скриншотов (`Data/`) не включайте в систему контроля версий.

### Устранение неполадок

- Ошибка конфигурации / отсутствуют переменные окружения — заполните обязательные поля в `.env`.
- `PG_SCHEMA '<schema>' is not in allowlist` — добавьте схему в `PG_SCHEMA_ALLOWLIST`.
- Ошибки подключения к БД — проверьте хост, порт, учётные данные, схему и сеть.
- Selenium запускается, снимок пустой — увеличьте `PAGE_LOAD_WAIT`, проверьте загрузку iframe и доступность URL.
- Слишком много ложных срабатываний diff — увеличьте `MSE_THRESHOLD` или `MIN_BLOCK_SIZE`.
- Пропущены визуальные изменения — уменьшите `MSE_THRESHOLD` и проверьте порог `threshold` для отчёта.

### Структура репозитория

- `src/pbimonitor/` — реализация по DDD
- `example_reports.json` — пример конфигурации отчётов
- `tests/` — pytest
- `.github/workflows/ci.yml` — непрерывная интеграция
- `docs/` — GitHub Pages (`index.html`) и `DATABASE.md`
- `wiki/` — исходники главной Wiki (`Home.md`, `_Sidebar.md`) для синхронизации с `*.wiki.git`
- `Dockerfile` и `docker-compose.yml` — контейнерный запуск

### Участие в разработке

См. [CONTRIBUTING.md](CONTRIBUTING.md).
