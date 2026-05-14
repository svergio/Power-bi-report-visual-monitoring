-- Схема PostgreSQL для системы мониторинга отчётов Power BI
-- Таблицы хранят результаты мониторинга десятков и сотен отчётов
-- Список отчётов задаётся в reports.json (не в БД)
-- Параметры БД и схемы задаются в .env
-- CREATE SCHEMA (при необходимости) и search_path выставляет PostgresStorage.apply_schema_sql
--   при выполнении: python -m pbimonitor --init-db
-- Не добавляйте сюда SET search_path: при программном применении это перезапишет PG_SCHEMA

CREATE TABLE IF NOT EXISTS baselines (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL UNIQUE,  -- идентификатор из reports.json
    report_name VARCHAR(255),                -- имя для удобства
    hash_value VARCHAR(64) NOT NULL,         -- перцептивный хеш last_baseline (dhash)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE baselines IS 'Метаданные базового снимка (каталоги Data/baselines, Data/changes)';
COMMENT ON COLUMN baselines.report_id IS 'Идентификатор отчёта из reports.json';
COMMENT ON COLUMN baselines.hash_value IS 'Перцептивный хеш последнего базового снимка (dhash)';

CREATE TABLE IF NOT EXISTS monitoring_checks (
    id BIGSERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL,         -- идентификатор из reports.json
    report_name VARCHAR(255),                -- имя для удобства
    report_url TEXT,                         -- URL отчёта
    check_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,             -- changed | unchanged | error | baseline_created
    diff_percent DECIMAL(5,2),               -- доля изменённой площади (визуальное отличие)
    screenshot_hash VARCHAR(64),             -- хеш текущего скриншота (dhash)
    delta_compressed BYTEA,                  -- XOR-дельта (относительно init-базового, с gzip)
    error TEXT,                              -- текст ошибки при status = error
    duration_sec DECIMAL(6,2),               -- длительность проверки, с
    next_check_at TIMESTAMP                  -- плановое время следующей проверки
);

COMMENT ON TABLE monitoring_checks IS 'Журнал всех проверок (вспомогательные файлы в Data/)';
COMMENT ON COLUMN monitoring_checks.report_id IS 'Идентификатор отчёта из reports.json';
COMMENT ON COLUMN monitoring_checks.status IS 'changed | unchanged | error | baseline_created';
COMMENT ON COLUMN monitoring_checks.diff_percent IS 'Процент отличия относительно last_baseline (quadtree/MSE)';
COMMENT ON COLUMN monitoring_checks.screenshot_hash IS 'Хеш текущего скриншота (dhash)';
COMMENT ON COLUMN monitoring_checks.delta_compressed IS 'Сжатая XOR-дельта к init-базовому снимку (восстановление текущего)';

-- Индекс: последняя история по отчёту
CREATE INDEX IF NOT EXISTS idx_checks_report_time ON monitoring_checks(report_id, check_time DESC);

-- Индекс: выборки по статусу и алерты
CREATE INDEX IF NOT EXISTS idx_checks_status ON monitoring_checks(status, check_time DESC);

-- Индекс: планировщик по времени следующей проверки
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

-- Последняя проверка по каждому отчёту
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

COMMENT ON VIEW v_latest_checks IS 'Последняя проверка для каждого отчёта';

-- Сводная статистика по отчёту
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

COMMENT ON VIEW v_report_stats IS 'Сводная статистика проверок по каждому отчёту';

CREATE OR REPLACE FUNCTION cleanup_old_checks(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Удаляем записи старше срока, но сохраняем последнюю запись по каждому отчёту для восстановления
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

COMMENT ON FUNCTION cleanup_old_checks IS 'Удаление устаревших проверок с сохранением последней записи по каждому отчёту';
-- Конфигурация отчётов задаётся в reports.json; эта схема хранит только результаты мониторинга
