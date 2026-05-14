from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger

from pbimonitor.application.dto.report_dto import CheckReportResultDto
from pbimonitor.application.usecases.check_report import CheckReportUseCase
from pbimonitor.application.usecases.diff_report import DiffReportUseCase
from pbimonitor.application.usecases.update_storage import UpdateStorageUseCase
from pbimonitor.config.settings import Settings
from pbimonitor.domain.reports.entities import Report
from pbimonitor.domain.reports.services import DiffPolicy, ReportDiffService
from pbimonitor.infrastructure.queue.scheduler import CheckRunner, InProcessScheduler, WorkerCleanup, WorkerFactory
from pbimonitor.infrastructure.selenium.client import BrowserConfig, RetryPolicy, SeleniumClient
from pbimonitor.infrastructure.storage.db import PostgresStorage
from pbimonitor.metrics import MetricsRegistry


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("pbimonitor")
    logger.setLevel(getattr(logging, level.upper()))
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.handlers = [handler]
    return logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Мониторинг визуальной отдачи отчётов Power BI")
    parser.add_argument("--env-file", default=".env", help="Путь к файлу .env")
    parser.add_argument("--build", action="store_true", help="Построить базовые снимки для всех отчётов")
    parser.add_argument("--check", metavar="REPORT_ID", help="Проверить один отчёт по идентификатору")
    parser.add_argument("--start", action="store_true", help="Запустить цикл планировщика")
    parser.add_argument("--init-db", action="store_true", help="Применить schema.sql к настроенной БД")
    return parser


def create_postgres_storage(settings: Settings, logger: logging.Logger) -> PostgresStorage:
    return PostgresStorage(
        dsn=settings.dsn,
        schema=settings.pg_schema,
        min_size=settings.pg_pool_min_size,
        max_size=settings.pg_pool_max_size,
        logger=logger,
    )


def create_check_bundle(
    settings: Settings,
    logger: logging.Logger,
    storage: PostgresStorage,
    metrics: MetricsRegistry,
) -> tuple[CheckReportUseCase, SeleniumClient]:
    selenium_client = SeleniumClient(
        browser=BrowserConfig(
            width=settings.screenshot_width,
            height=settings.screenshot_height,
            page_load_wait_seconds=settings.page_load_wait,
            auth_server_whitelist=settings.powerbi_auth_server_whitelist,
            username=settings.powerbi_username,
            password=settings.powerbi_password,
            headless=True,
        ),
        retry_policy=RetryPolicy(
            attempts=settings.retry_attempts,
            base_delay_seconds=settings.retry_base_delay_seconds,
            max_delay_seconds=settings.retry_max_delay_seconds,
            jitter_seconds=settings.retry_jitter_seconds,
        ),
        logger=logger,
    )
    diff_service = ReportDiffService()
    check_usecase = CheckReportUseCase(
        selenium_client=selenium_client,
        storage_usecase=UpdateStorageUseCase(storage),
        diff_usecase=DiffReportUseCase(diff_service),
        diff_service=diff_service,
        metrics=metrics,
        screenshots_dir=Path(settings.screenshots_dir),
        logger=logger,
    )
    return check_usecase, selenium_client


def build_worker_factory(
    settings: Settings,
    logger: logging.Logger,
    storage: PostgresStorage,
    metrics: MetricsRegistry,
    policy: DiffPolicy,
) -> WorkerFactory:
    def factory() -> tuple[CheckRunner, WorkerCleanup]:
        check_usecase, selenium_client = create_check_bundle(settings, logger, storage, metrics)

        def run(report: Report) -> CheckReportResultDto:
            return check_usecase.execute(report, policy)

        return run, selenium_client.close

    return factory


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = Settings.from_env_file(args.env_file)
    settings.validate_allowlist()
    logger = configure_logging(settings.log_level)
    reports = settings.load_reports()
    policy = DiffPolicy(
        mse_threshold=settings.mse_threshold,
        min_block_size=settings.min_block_size,
        max_depth=settings.max_depth,
        draw_diff_image=settings.diff_enabled,
    )

    storage = create_postgres_storage(settings, logger)
    try:
        if args.init_db:
            schema_path = Path("schema.sql")
            storage.apply_schema_sql(schema_path.read_text(encoding="utf-8"))
            logger.info("schema_applied")
            return

        metrics = MetricsRegistry()

        if args.start:
            scheduler_holder: list[InProcessScheduler | None] = [None]

            def stop_handler(_sig: int, _frame: object) -> None:
                sched = scheduler_holder[0]
                if sched is not None:
                    sched.request_stop()

            signal.signal(signal.SIGINT, stop_handler)
            signal.signal(signal.SIGTERM, stop_handler)

            scheduler = InProcessScheduler(
                reports=reports,
                worker_count=max(settings.min_worker_threads, min(settings.max_worker_threads, len(reports))),
                worker_factory=build_worker_factory(settings, logger, storage, metrics, policy),
                logger=logger,
                worker_join_timeout_seconds=120.0,
            )
            scheduler_holder[0] = scheduler
            scheduler.run()
            metrics.emit(logger)
            return

        check_usecase, selenium_client = create_check_bundle(settings, logger, storage, metrics)
        try:
            if args.build:
                for report in reports:
                    result = check_usecase.execute(report, policy)
                    logger.info("build_report", extra=result.__dict__)
                metrics.emit(logger)
                return

            if args.check:
                selected_report = next((item for item in reports if item.id == args.check), None)
                if selected_report is None:
                    raise ValueError(f"Report not found: {args.check}")
                result = check_usecase.execute(selected_report, policy)
                logger.info("check_result", extra=result.__dict__)
                metrics.emit(logger)
                return

            parser.print_help()
        finally:
            selenium_client.close()
    finally:
        storage.close()


if __name__ == "__main__":
    main()
