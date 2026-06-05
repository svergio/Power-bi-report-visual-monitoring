# Operations and tuning

---

## English

### First-time bootstrap

1. Create a PostgreSQL database user that may `CREATE SCHEMA` (or already owns the target schema) and matches `PG_*` in `.env`.
2. Put `PG_SCHEMA` inside `PG_SCHEMA_ALLOWLIST` to satisfy the safety check in `Settings.validate_allowlist`.
3. Install Python dependencies, export `PYTHONPATH=src` (Windows: `$env:PYTHONPATH="src"`), copy `.env.example` to `.env` and fill secrets.
4. Author `reports.json` (start from `example_reports.json`): stable `id`, reachable `url`, sensible `interval`, realistic `threshold` for metrics.
5. Run `python -m pbimonitor --init-db` once per environment.
6. Run `python -m pbimonitor --build` to seed baselines; inspect `Data/` for images.
7. Run `python -m pbimonitor --check <id>` for a single smoke test; watch JSON logs for `check_result`.
8. Run `python -m pbimonitor --start` under a process supervisor in production.

### Docker path

`docker compose up --build -d` starts `web` (monitor) and `db` (PostgreSQL). Mount or inject `.env` and `reports.json` as you would on bare metal. The optional `redis` service is a placeholder for future work; the current scheduler does not require it.

### Environment knobs that affect behaviour

| Variable group | Effect |
|----------------|--------|
| `PAGE_LOAD_WAIT` | Too low yields blank captures on slow iframes; too high slows every check. |
| `SCREENSHOT_*` | Larger viewports cost more render time and disk; keep aligned with what humans actually see. |
| `MSE_THRESHOLD`, `MIN_BLOCK_SIZE`, `MAX_DEPTH` | Directly change quadtree sensitivity; tune together, not one at a time in large jumps. |
| `DIFF_ENABLED` | Controls whether diff overlay images are written (helpful for debugging, costs IO). |
| `RETRY_*` | Increase attempts or delays when the service sits behind flaky VPNs or rotating gateways. |
| `POWERBI_*` | Basic auth only covers a subset of enterprise setups; integrated auth may need extra engineering. |

### Interpreting statuses in operations

- **`baseline_created`** after deploy means the monitor never saw this report before, or baseline files were wiped. Expect the next run to hit the diff path.
- **`unchanged` streak** with suspicious business events usually means the visual did not change enough under current thresholds, or the wrong URL/credentials show a static shell page.
- **`changed` spikes** after model deploys are normal; correlate with release calendar.
- **`error` rows** with Selenium timeouts: verify network, headless Chrome version, and `PAGE_LOAD_WAIT`.

### Incident checklist

1. Confirm `python -m pbimonitor --help` runs with expected flags (English strings).
2. Tail logs for `check_report_failed` vs persisted `error` rows.
3. Open `current_screenshot_diff.png` when diff rendering is enabled.
4. Query `v_latest_checks` for quick health.
5. If disk grows, plan `cleanup_old_checks` (SQL function) with retention aligned to compliance.

### metrics snapshot

The process emits `render_duration_ms`, `diff_duration_ms`, `delta_size_bytes`, and `below_diff_threshold_rate`. Use them to see whether you are CPU-bound in diff, IO-bound in PNG writes, or simply scheduling too aggressively.

---

## Русский

### Первый запуск

1. Создать пользователя PostgreSQL с правом `CREATE SCHEMA` (или владельца целевой схемы), совпадающего с `PG_*` в `.env`.
2. Включить `PG_SCHEMA` в `PG_SCHEMA_ALLOWLIST`, иначе `validate_allowlist` завершит процесс при старте.
3. Установить зависимости, `PYTHONPATH=src`, скопировать `.env.example` в `.env`, заполнить секреты.
4. Подготовить `reports.json` (от `example_reports.json`): стабильный `id`, доступный `url`, разумный `interval`, `threshold` для метрик.
5. Один раз: `python -m pbimonitor --init-db`.
6. `python -m pbimonitor --build` &mdash; построить baseline; проверить `Data/`.
7. `python -m pbimonitor --check <id>` &mdash; дымовый тест; смотреть JSON-логи `check_result`.
8. В проде: `python -m pbimonitor --start` под systemd / NSSM / k8s job.

### Docker

`docker compose up --build -d` поднимает `web` и `db`. Прокинуть `.env` и `reports.json` как на железе. Сервис `redis` &mdash; задел под будущее, текущий планировщик его не требует.

### Переменные, влияющие на поведение

| Группа | Эффект |
|--------|--------|
| `PAGE_LOAD_WAIT` | Слишком мало &mdash; пустые снимки на тяжёлых iframe; слишком мало &mdash; каждая проверка дольше. |
| `SCREENSHOT_*` | Больше разрешение &mdash; дороже рендер и диск; держите ближе к реальному виду пользователя. |
| `MSE_THRESHOLD`, `MIN_BLOCK_SIZE`, `MAX_DEPTH` | Чувствительность quadtree; крутите согласованно, без огромных скачков одного параметра. |
| `DIFF_ENABLED` | Писать ли overlay diff (отладка vs IO). |
| `RETRY_*` | Нестабильная сеть или шлюз &mdash; больше попыток или задержек. |
| `POWERBI_*` | Basic-auth не покрывает все enterprise-сценарии; интегрированный вход может потребовать доработок. |

### Статусы в эксплуатации

- **`baseline_created`** после выката &mdash; первый контакт или снесли файлы baseline.
- Длинная серия **`unchanged`** при подозрительных бизнес-событиях &mdash; проверьте URL/учётку и пороги: возможно, рисуется &laquo;пустая оболочка&raquo;.
- Всплески **`changed`** после релиза модели &mdash; норма; сверяйте с календарём.
- **`error`** с таймаутом Selenium &mdash; сеть, версия Chrome, `PAGE_LOAD_WAIT`.

### Чеклист инцидента

1. `python -m pbimonitor --help` отрабатывает (тексты на английском).
2. Логи: `check_report_failed` vs запись `error` в БД.
3. Открыть `current_screenshot_diff.png`, если diff включён.
4. `SELECT * FROM v_latest_checks` (в вашей схеме) для обзора.
5. Рост диска &mdash; политика `cleanup_old_checks` и срок хранения.

### Метрики

Процесс отдаёт `render_duration_ms`, `diff_duration_ms`, `delta_size_bytes`, `below_diff_threshold_rate`. По ним видно, упираетесь ли в diff, в запись PNG или в слишком частый schedule.
