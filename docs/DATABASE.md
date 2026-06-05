# Database schema (PostgreSQL)

This project stores **monitoring outcomes** in PostgreSQL. The **list of reports** (URLs, intervals, thresholds) is defined in `reports.json` (or path from `REPORTS_FILE` in `.env`), not in the database.

DDL lives in the repository root: [`schema.sql`](../schema.sql). Apply it with:

```bash
python -m pbimonitor --init-db
```

That command creates `PG_SCHEMA` if needed, sets `search_path`, and executes `schema.sql` via `PostgresStorage.apply_schema_sql`.

## Tables

### `baselines`

One row per monitored report.

| Column | Description |
|--------|-------------|
| `report_id` | Unique id from `reports.json`. |
| `report_name` | Human-readable name. |
| `hash_value` | Perceptual hash (dhash) of the latest baseline screenshot (`last_baseline.png` on disk). |
| `created_at` / `updated_at` | Timestamps; `updated_at` is maintained by trigger. |

Image files are stored under `Data/baselines` and `Data/changes/<report_id>/` (see application use case `check_report`).

### `monitoring_checks`

Append-only log of every check attempt.

| Column | Description |
|--------|-------------|
| `report_id`, `report_name`, `report_url` | Report identity and URL at check time. |
| `check_time` | UTC timestamp of the check. |
| `status` | One of: `changed`, `unchanged`, `error`, `baseline_created`. |
| `diff_percent` | Visual difference vs baseline (quadtree / MSE pipeline); `NULL` on `error`. |
| `screenshot_hash` | dhash of current screenshot when available. |
| `delta_compressed` | gzip-compressed XOR delta vs the **init** baseline image (optional payload). |
| `error` | Error message when `status = error`. |
| `duration_sec` | Wall-clock duration of the check. |
| `next_check_at` | Scheduler hint for the next planned run. |

Indexes support history by report, filtering by status, and scheduler queries on `next_check_at`.

## Views

- **`v_latest_checks`**: latest `monitoring_checks` row per `report_id` (DISTINCT ON).
- **`v_report_stats`**: aggregates per report: total checks, change/error counts, average duration, last check time, average diff where applicable.

## Functions

- **`cleanup_old_checks(days_to_keep DEFAULT 30)`**: deletes rows older than the retention window **except** the latest row per `report_id`, so each report always keeps at least one history row.

## Related code

- Inserts / updates: [`src/pbimonitor/infrastructure/storage/db.py`](../src/pbimonitor/infrastructure/storage/db.py)
- Orchestration: [`src/pbimonitor/application/usecases/check_report.py`](../src/pbimonitor/application/usecases/check_report.py)
