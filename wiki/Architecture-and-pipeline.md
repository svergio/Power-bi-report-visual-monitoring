# Architecture and pipeline

---

## English

### High-level shape

The codebase follows a **layered DDD layout**: `domain` holds report and session entities plus pure services (image hash, quadtree/MSE diff, XOR delta encoding); `application` orchestrates use cases (`check_report`, `diff_report`, `update_storage`); `infrastructure` wraps Selenium, PostgreSQL, and the in-process scheduler; `config` loads `Settings` from the environment and validates `reports.json`.

### Where configuration lives

- **reports.json** (or `REPORTS_FILE`) is the source of truth for *which* URLs to open, how often, and per-report `threshold` for metrics. It is not mirrored as rows inside PostgreSQL.
- **.env** (or `--env-file`) supplies infrastructure: DSN, schema allowlist, screenshot dimensions, diff policy numbers, retry backoff, optional Power BI credentials.

### Files under `Data/`

All screenshot artifacts sit under the configured `screenshots_dir` (default `./Data`):

1. **`Data/baselines/<report_id>_init_baseline.png`** &mdash; frozen first capture. XOR deltas in the database are computed relative to this image so you can reason about "how far did we drift from day zero" even as `last_baseline` rolls forward.
2. **`Data/changes/<report_id>/last_baseline.png`** &mdash; rolling reference for the *next* comparison.
3. **`Data/changes/<report_id>/current_screenshot.png`** &mdash; scratch file for the render just taken.
4. **`Data/changes/<report_id>/current_screenshot_diff.png`** &mdash; optional heatmap/overlay when diff rendering is enabled.

If any of the baseline trio is missing while a DB row still exists, the use case rebuilds baselines on the next successful path.

### Check pipeline (logical order)

1. Resolve directories and whether `baseline_exists` (DB hash + both baseline files).
2. **Selenium** loads the report URL, waits (`PAGE_LOAD_WAIT`), captures either into `init_baseline` (first run) or `current` (subsequent).
3. **First run:** copy init to `last_baseline`, compute dhash, upsert `baselines`, insert `monitoring_checks` with `baseline_created`.
4. **Later runs:** run `DiffReportUseCase` comparing `last_baseline` vs `current` with `DiffPolicy` (`mse_threshold`, `min_block_size`, `max_depth`, optional diff image). Encode XOR delta vs `init_baseline` when bytes are produced.
5. Decide `changed` vs `unchanged` from `diff_percent > 0` vs zero, atomically replace `last_baseline` with the new capture, update `baselines.hash_value`, insert `monitoring_checks` including optional `delta_compressed`.
6. On exception, log and insert `error` row with message, leaving diff fields null.

### PostgreSQL role

Tables `baselines` and `monitoring_checks` (plus views `v_latest_checks`, `v_report_stats`, function `cleanup_old_checks`) persist what happened across hosts. The pool uses **psycopg3** with explicit `search_path` per transaction to target `PG_SCHEMA`.

### Scheduler

`InProcessScheduler` enqueues enabled reports, spawns worker threads up to the configured min/max bounds, reapplies factory-created Selenium clients per worker, and backs off using last render duration and failure counts. This is **not** a distributed queue yet; Redis in compose is reserved.

### Check row statuses (authoritative behaviour)

These strings are written to `monitoring_checks.status` by `CheckReportUseCase` in the shipped code:

| Status | When |
|--------|------|
| `baseline_created` | No prior baseline: `baseline_hash` was missing **or** either `init_baseline` / `last_baseline` PNG was missing; after a successful capture the init image is copied to `last_baseline`, dhash is stored in `baselines`, `diff_percent` is `0`, no delta. |
| `unchanged` | Baseline existed; diff returned `diff_percent == 0`; the new capture replaces `last_baseline.png` on success. |
| `changed` | Baseline existed; diff returned `diff_percent > 0`; same promotion of the new capture to `last_baseline.png` on success. |
| `error` | Any exception in the check path; stored row clears `diff_percent` and screenshot hash, `error` holds the message. |

The per-report `threshold` in `reports.json` feeds **metrics** (`diff_percent < threshold` rate), not the `changed` vs `unchanged` branch (that branch uses strict `> 0` vs zero).

### Mini glossary

- **Init baseline** — `Data/baselines/<id>_init_baseline.png`; stable anchor for XOR delta bytes.
- **Last baseline** — `Data/changes/<id>/last_baseline.png`; rolling compare target.
- **diff_percent** — fraction of canvas area flagged different by the quadtree / MSE policy.
- **dhash** — perceptual hash stored in `baselines.hash_value` / check rows for fingerprinting.
- **XOR delta** — optional gzip-compressed payload versus the init baseline for forensics.

### Further reading

- [docs/DATABASE.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md) for column-level commentary.
- [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/) for the long narrative on *why* visual monitoring complements warehouse checks.

---

## Русский

### Общая форма

Код организован в **слоях DDD**: в `domain` &mdash; сущности отчётов и сессий и чистые сервисы (хеш изображения, quadtree/MSE, XOR-дельта); в `application` &mdash; сценарии (`check_report`, `diff_report`, `update_storage`); в `infrastructure` &mdash; Selenium, PostgreSQL, планировщик в процессе; в `config` &mdash; `Settings` из окружения и валидация `reports.json`.

### Где лежит конфигурация

- **reports.json** (или `REPORTS_FILE`) &mdash; источник правды: *какие* URL, как часто, порог `threshold` для метрик. В PostgreSQL это не дублируется строками отчётов.
- **.env** (`--env-file`) &mdash; инфраструктура: DSN, allowlist схемы, размер снимка, числа политики diff, backoff повторов, опционально учётные данные Power BI.

### Файлы в `Data/`

Все снимки &mdash; под `screenshots_dir` (по умолчанию `./Data`):

1. **`Data/baselines/<report_id>_init_baseline.png`** &mdash; &laquo;нулевой&raquo; эталон; XOR-дельты в БД считаются относительно него, пока `last_baseline` скользит вперёд.
2. **`Data/changes/<report_id>/last_baseline.png`** &mdash; опорный кадр для *следующего* сравнения.
3. **`Data/changes/<report_id>/current_screenshot.png`** &mdash; только что снятый кадр.
4. **`Data/changes/<report_id>/current_screenshot_diff.png`** &mdash; опциональная картинка отличий.

Если в БД есть baseline, а файлы потеряны, при следующем успешном проходе цепочка восстановится заново.

### Пайплайн проверки (логический порядок)

1. Подготовка каталогов и проверка `baseline_exists` (хеш в БД + оба baseline-файла).
2. **Selenium** открывает URL, ждёт (`PAGE_LOAD_WAIT`), пишет в `init_baseline` (первый раз) или в `current`.
3. **Первый запуск:** копия init в `last_baseline`, dhash, upsert `baselines`, строка `baseline_created` в `monitoring_checks`.
4. **Дальше:** `DiffReportUseCase` сравнивает `last_baseline` и `current` с `DiffPolicy`; XOR к `init_baseline` при наличии байт.
5. Ветка `changed` / `unchanged` по `diff_percent > 0`, замена `last_baseline`, обновление хеша в `baselines`, вставка в `monitoring_checks` с опциональным `delta_compressed`.
6. Исключение &mdash; лог и строка `error` с текстом, без diff-полей.

### Роль PostgreSQL

Таблицы `baselines`, `monitoring_checks`, представления и `cleanup_old_checks` хранят историю между хостами. Пул **psycopg3**, `search_path` на каждую транзакцию к `PG_SCHEMA`.

### Планировщик

`InProcessScheduler` ставит в очередь включённые отчёты, поднимает воркеры в пределах min/max, создаёт клиентов Selenium на воркер, учитывает длительность рендера и число сбоев. Это **не** распределённая очередь; Redis в compose зарезервирован.

### Статусы строки проверки (как в коде)

Строка `monitoring_checks.status` заполняется в `CheckReportUseCase`:

| Статус | Когда |
|--------|-------|
| `baseline_created` | Не было baseline: нет хеша в БД **или** отсутствует один из файлов `init_baseline` / `last_baseline`; после успешного снимка init копируется в `last_baseline`, dhash в `baselines`, `diff_percent` = 0, дельты нет. |
| `unchanged` | Baseline был; diff дал `diff_percent == 0`; при успехе новый кадр становится `last_baseline.png`. |
| `changed` | Baseline был; `diff_percent > 0`; при успехе тот же перенос нового кадра в `last_baseline.png`. |
| `error` | Исключение в цепочке; в записи обнуляются `diff_percent` и хеш снимка, текст в `error`. |

Поле `threshold` в `reports.json` участвует в **метриках** (доля случаев `diff_percent < threshold`), а не в ветвлении `changed` / `unchanged` (там сравнение с нулём).

### Мини-глоссарий

- **Init baseline** — `Data/baselines/<id>_init_baseline.png`; опора для XOR-дельты.
- **Last baseline** — `Data/changes/<id>/last_baseline.png`; скользящий эталон сравнения.
- **diff_percent** — доля площади канваса, помеченная отличной при текущей политике diff.
- **dhash** — перцептивный хеш в `baselines` / строках проверок.
- **XOR-дельта** — опциональный gzip-блок относительно init baseline.

### Дальше

- [docs/DATABASE.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md) &mdash; колонки и комментарии.
- [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/) &mdash; длинное обоснование визуального мониторинга рядом с SQL-проверками.
