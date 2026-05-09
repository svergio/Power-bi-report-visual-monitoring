-- Power BI Monitoring System - PostgreSQL Schema
-- Схема для хранения РЕЗУЛЬТАТОВ мониторинга 96+ Power BI отчетов
-- Конфигурация отчетов хранится в reports.json
--
-- База данных: db_new
-- Схема: sandbox
-- Пользователь: dwh_bi_user

-- Устанавливаем схему sandbox для всех операций
SET search_path TO sandbox;

-- ВАЖНО: Схема sandbox уже существует, не создаем её!
-- Пользователь dwh_bi_user может только создавать таблицы/view внутри sandbox

-- =============================================================================
-- Таблица baseline скриншотов
-- =============================================================================
CREATE TABLE IF NOT EXISTS baselines (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL UNIQUE,  -- ID из reports.json
    report_name VARCHAR(255),                -- Имя для удобства
    hash_value VARCHAR(64) NOT NULL,         -- Perceptual hash last_baseline (dhash)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE baselines IS 'Метаданные baseline (файлы в Data/baselines, Data/changes)';
COMMENT ON COLUMN baselines.report_id IS 'ID отчета из reports.json';
COMMENT ON COLUMN baselines.hash_value IS 'Perceptual hash last_baseline (dhash)';

-- =============================================================================
-- Таблица результатов проверок
-- =============================================================================
CREATE TABLE IF NOT EXISTS monitoring_checks (
    id BIGSERIAL PRIMARY KEY,
    report_id VARCHAR(100) NOT NULL,         -- ID из reports.json
    report_name VARCHAR(255),                -- Имя для удобства
    report_url TEXT,                         -- URL отчета
    check_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,             -- 'changed', 'unchanged', 'error', 'baseline_created'
    diff_percent DECIMAL(5,2),               -- Процент различий
    screenshot_hash VARCHAR(64),             -- Hash текущего скриншота
    delta_compressed BYTEA,                  -- XOR delta (initial XOR current, gzipped)
    error TEXT,                              -- Сообщение об ошибке если есть
    duration_sec DECIMAL(6,2),               -- Длительность проверки
    next_check_at TIMESTAMP                  -- Расчетное время следующей проверки
);

COMMENT ON TABLE monitoring_checks IS 'Лог всех проверок отчетов (файлы в Data/ - кеш)';
COMMENT ON COLUMN monitoring_checks.report_id IS 'ID отчета из reports.json';
COMMENT ON COLUMN monitoring_checks.status IS 'changed | unchanged | error | baseline_created';
COMMENT ON COLUMN monitoring_checks.diff_percent IS 'Процент различий от last_baseline';
COMMENT ON COLUMN monitoring_checks.screenshot_hash IS 'Hash текущего скриншота (dhash)';
COMMENT ON COLUMN monitoring_checks.delta_compressed IS 'XOR delta (initial XOR current, gzipped) для восстановления';

-- =============================================================================
-- Индексы для производительности
-- =============================================================================

-- Быстрый поиск последних проверок конкретного отчета
CREATE INDEX IF NOT EXISTS idx_checks_report_time ON monitoring_checks(report_id, check_time DESC);

-- Поиск по статусу (для алертов)
CREATE INDEX IF NOT EXISTS idx_checks_status ON monitoring_checks(status, check_time DESC);

-- Поиск следующих проверок для scheduler
CREATE INDEX IF NOT EXISTS idx_checks_next_check ON monitoring_checks(next_check_at) WHERE next_check_at IS NOT NULL;

-- =============================================================================
-- Триггер для обновления updated_at
-- =============================================================================
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

-- =============================================================================
-- Полезные view для анализа
-- =============================================================================

-- Последние проверки для каждого отчета
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

COMMENT ON VIEW v_latest_checks IS 'Последняя проверка для каждого отчета';

-- Статистика по отчетам
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

COMMENT ON VIEW v_report_stats IS 'Статистика проверок по каждому отчету';

-- =============================================================================
-- Функция для очистки старых данных
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_checks(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Удаляем проверки старше N дней, но оставляем последнюю для каждого отчета
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

COMMENT ON FUNCTION cleanup_old_checks IS 'Удаление старых проверок (но сохранение последней для каждого отчета)';

-- =============================================================================
-- Примечание
-- =============================================================================
-- Конфигурация отчетов хранится в reports.json, не в БД
-- Эта схема используется только для хранения РЕЗУЛЬТАТОВ мониторинга

