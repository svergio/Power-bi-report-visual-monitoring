# Power BI Report Visual Monitor

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Открытый мониторинг визуальной отдачи отчётов Power BI Report Server и веб-отчётов Power BI. Проект разбит на слои DDD (`domain`, `application`, `infrastructure`, `config`) и использует:

- рендеринг через Selenium с повторами (retry/backoff) и повторной авторизацией;
- визуальное сравнение: quadtree и MSE;
- хранение XOR-дельты с gzip;
- PostgreSQL и пул соединений psycopg3;
- очередь задач в процессе и ограничение нагрузки (backpressure).

## Быстрый старт

### 1) Установка

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

Если в репозитории настроен устанавливаемый пакет (`pyproject.toml` / `setup.cfg`), дополнительно можно выполнить `pip install -e .` из корня репозитория.

### 2) Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

- подключение к PostgreSQL: `PG_HOST`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_SCHEMA`;
- политика схемы: `PG_SCHEMA_ALLOWLIST`; команда `python -m pbimonitor --init-db` выполняет `CREATE SCHEMA IF NOT EXISTS` для `PG_SCHEMA` и накатывает `schema.sql`;
- при необходимости доступ к Power BI: `POWERBI_USERNAME`, `POWERBI_PASSWORD`;
- среда исполнения: `REPORTS_FILE`, число воркеров, пороги, параметры повторов.

### 3) Конфигурация отчётов

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

### 4) Схема БД и запуск

```bash
python -m pbimonitor --init-db
python -m pbimonitor --build
python -m pbimonitor --check daily_sales
python -m pbimonitor --start
```

## Docker

```bash
docker compose up --build -d
```

Сервисы:

- `web` — процесс pbimonitor;
- `db` — PostgreSQL;
- `redis` (опциональный профиль): зарезервирован под будущую распределённую очередь.

## Архитектура DDD

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

## Метрики времени выполнения

Приложение пишет снимок метрик:

- `render_duration_ms`
- `diff_duration_ms`
- `delta_size_bytes`
- `below_diff_threshold_rate` (доля проверок, где процент визуального отличия ниже порога `threshold` отчёта)

## Требования

- Python 3.10+
- PostgreSQL 12+
- Chrome/Chromium, совместимый с Selenium
- Доступ с хоста монитора к Power BI Report Server или размещённым в сети URL отчётов Power BI

## Требования к PostgreSQL

- Пользователь БД должен иметь право создавать схему (или целевую схему) и объекты в `PG_SCHEMA` (таблицы, индексы, представления, функции).
- `schema.sql` применяется командой `python -m pbimonitor --init-db` (при отсутствии схемы она создаётся, затем выполняется DDL).
- Таблицы: `baselines`, `monitoring_checks`.

## Требования к Power BI

- Отчёты должны открываться с машины, где запущен монитор.
- Для сред с интегрированной аутентификацией при необходимости задайте `POWERBI_AUTH_SERVER_WHITELIST`.
- Для простой Basic-auth укажите `POWERBI_USERNAME` и `POWERBI_PASSWORD` в `.env`.

## Безопасность

- Не коммитьте `.env`.
- В продакшене используйте хранилища секретов (Kubernetes Secrets, Vault, облачные хранилища).
- Регулярно меняйте пароли БД и учётные данные отчётов.
- Кеш скриншотов (`Data/`) не включайте в систему контроля версий.

## Устранение неполадок

- Ошибка конфигурации / отсутствуют переменные окружения — заполните обязательные поля в `.env`.
- `PG_SCHEMA '<schema>' is not in allowlist` — добавьте схему в `PG_SCHEMA_ALLOWLIST`.
- Ошибки подключения к БД — проверьте хост, порт, учётные данные, схему и сеть.
- Selenium запускается, снимок пустой — увеличьте `PAGE_LOAD_WAIT`, проверьте загрузку iframe и доступность URL.
- Слишком много ложных срабатываний diff — увеличьте `MSE_THRESHOLD` или `MIN_BLOCK_SIZE`.
- Пропущены визуальные изменения — уменьшите `MSE_THRESHOLD` и проверьте порог `threshold` для отчёта.

## Структура репозитория

- `src/pbimonitor/` — реализация по DDD
- `example_reports.json` — пример конфигурации отчётов
- `tests/` — pytest
- `.github/workflows/ci.yml` — непрерывная интеграция (описание шагов на английском, принято для GitHub Actions)
- `Dockerfile` и `docker-compose.yml` — контейнерный запуск

## Участие в разработке

См. [CONTRIBUTING.md](CONTRIBUTING.md).
