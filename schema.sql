-- PostgreSQL schema for Power BI report visual monitoring.
-- Tables store monitoring results for many reports. Report definitions live in reports.json (not in the DB).
-- Connection and schema name come from .env.
-- PostgresStorage.apply_schema_sql runs CREATE SCHEMA IF NOT EXISTS, sets search_path, then runs this file (python -m pbimonitor --init-db).
-- Do not add SET search_path here: programmatic apply already targets PG_SCHEMA.

CREATE TABLE IF NOT EXISTS baselines (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL UNIQUE,  -- id from reports.json
    report_name VARCHAR(255),                -- display name
    hash_value VARCHAR(64) NOT NULL,         -- perceptual hash (dhash) of last_baseline image
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE baselines IS 'Baseline metadata; image files under Data/baselines and Data/changes';
COMMENT ON COLUMN baselines.report_id IS 'Report id from reports.json';
COMMENT ON COLUMN baselines.hash_value IS 'Perceptual hash (dhash) of the latest baseline screenshot';

CREATE TABLE IF NOT EXISTS monitoring_checks (
    id BIGSERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL,         -- id from reports.json
    report_name VARCHAR(255),                -- display name
    report_url TEXT,                         -- report URL
    check_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,             -- changed | unchanged | error | baseline_created
    diff_percent DECIMAL(5,2),               -- share of canvas area that differs (quadtree/MSE vs baseline)
    screenshot_hash VARCHAR(64),             -- dhash of current screenshot
    delta_compressed BYTEA,                  -- gzip-compressed XOR delta vs init baseline image
    error TEXT,                              -- message when status = error
    duration_sec DECIMAL(6,2),               -- wall-clock check duration in seconds
    next_check_at TIMESTAMP                  -- scheduler: planned next run time
);

COMMENT ON TABLE monitoring_checks IS 'Append-only check log; auxiliary screenshot files under Data/';
COMMENT ON COLUMN monitoring_checks.report_id IS 'Report id from reports.json';
COMMENT ON COLUMN monitoring_checks.status IS 'changed | unchanged | error | baseline_created';
COMMENT ON COLUMN monitoring_checks.diff_percent IS 'Visual difference vs last_baseline (quadtree/MSE pipeline)';
COMMENT ON COLUMN monitoring_checks.screenshot_hash IS 'dhash of the current screenshot';
COMMENT ON COLUMN monitoring_checks.delta_compressed IS 'Compressed XOR delta to init baseline (reconstruct current from baseline + delta)';

-- Latest history per report
CREATE INDEX IF NOT EXISTS idx_checks_report_time ON monitoring_checks(report_id, check_time DESC);

-- Status filters and alerting
CREATE INDEX IF NOT EXISTS idx_checks_status ON monitoring_checks(status, check_time DESC);

-- Scheduler: next due time (partial index excludes NULL)
CREATE INDEX IF NOT EXISTS idx_checks_next_check ON monitoring_checks(next_check_at) WHERE next_check_at IS NOT NULL;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_baselines_updated_at ON baselines;
CREATE TRIGGER update_baselines_updated_at BEFORE UPDATE ON baselines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Latest row per report_id
CREATE OR REPLACE VIEW v_latest_checks AS
SELECT DISTINCT ON (report_id)
    mc.report_id,
    mc.report_name,
    mc.report_url,
    mc.check_time,
    mc.status,
    mc.diff_percent,
    mc.next_check_at
FROM monitoring_checks mc
ORDER BY report_id, check_time DESC;

COMMENT ON VIEW v_latest_checks IS 'Most recent monitoring_checks row for each report';

-- Aggregated stats per report
CREATE OR REPLACE VIEW v_report_stats AS
SELECT
    mc.report_id,
    mc.report_name,
    COUNT(mc.id) AS total_checks,
    COUNT(CASE WHEN mc.status = 'changed' THEN 1 END) AS changes_count,
    COUNT(CASE WHEN mc.status = 'error' THEN 1 END) AS errors_count,
    AVG(mc.duration_sec) AS avg_duration_sec,
    MAX(mc.check_time) AS last_check_time,
    AVG(CASE WHEN mc.status IN ('changed', 'unchanged') THEN mc.diff_percent END) AS avg_diff_percent
FROM monitoring_checks mc
GROUP BY mc.report_id, mc.report_name;

COMMENT ON VIEW v_report_stats IS 'Per-report aggregate statistics over monitoring_checks';

CREATE OR REPLACE FUNCTION cleanup_old_checks(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete rows older than retention but keep the latest row per report for continuity
    WITH latest_checks AS (
        SELECT DISTINCT ON (report_id) id
        FROM monitoring_checks
        ORDER BY report_id, check_time DESC
    )
    DELETE FROM monitoring_checks
    WHERE check_time < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep
      AND id NOT IN (SELECT id FROM latest_checks);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_checks IS 'Delete monitoring_checks older than days_to_keep except the latest row per report';
-- Report configuration remains in reports.json; this schema stores monitoring outcomes only.
