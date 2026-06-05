from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from psycopg import Cursor
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool

from pbimonitor.domain.reports.repositories import MonitoringStorageRepository
from pbimonitor.exceptions import StorageError
from pbimonitor.infrastructure.storage.models import CheckRecord


class PostgresStorage(MonitoringStorageRepository):
    def __init__(
        self,
        dsn: str,
        schema: str,
        min_size: int,
        max_size: int,
        logger: logging.Logger,
    ) -> None:
        self._schema = schema
        self._logger = logger
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": False, "row_factory": tuple_row},
            open=False,
        )
        self._pool.open(wait=True)

    def apply_schema_sql(self, sql: str) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self._schema}")
                cursor.execute(f"SET search_path TO {self._schema}")
                cursor.execute(sql)
            connection.commit()

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def _cursor(self) -> Generator[Cursor[tuple], None, None]:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f"SET search_path TO {self._schema}")
                    yield cursor
                    connection.commit()
                except Exception as exc:
                    connection.rollback()
                    raise StorageError("Database operation failed") from exc

    def get_baseline_hash(self, report_id: str) -> Optional[str]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT hash_value FROM baselines WHERE report_id = %s",
                (report_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def upsert_baseline_hash(self, report_id: str, report_name: str, hash_value: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO baselines (report_id, report_name, hash_value)
                VALUES (%s, %s, %s)
                ON CONFLICT (report_id) DO UPDATE
                SET hash_value = EXCLUDED.hash_value, updated_at = CURRENT_TIMESTAMP
                """,
                (report_id, report_name, hash_value),
            )

    def save_check_result(
        self,
        report_id: str,
        report_name: str,
        report_url: str,
        status: str,
        check_time: datetime,
        diff_percent: Optional[float],
        screenshot_hash: Optional[str],
        delta_compressed: Optional[bytes],
        error: Optional[str],
        duration_sec: float,
        next_check_at: Optional[datetime],
    ) -> None:
        record = CheckRecord(
            report_id=report_id,
            report_name=report_name,
            report_url=report_url,
            check_time=check_time,
            status=status,
            diff_percent=diff_percent,
            screenshot_hash=screenshot_hash,
            delta_compressed=delta_compressed,
            error=error,
            duration_sec=duration_sec,
            next_check_at=next_check_at,
        )
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO monitoring_checks (
                    report_id, report_name, report_url, check_time, status,
                    diff_percent, screenshot_hash, delta_compressed, error, duration_sec, next_check_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.report_id,
                    record.report_name,
                    record.report_url,
                    record.check_time,
                    record.status,
                    record.diff_percent,
                    record.screenshot_hash,
                    record.delta_compressed,
                    record.error,
                    record.duration_sec,
                    record.next_check_at,
                ),
            )

    def get_delta(self, check_id: int) -> Optional[bytes]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT delta_compressed FROM monitoring_checks WHERE id = %s",
                (check_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

