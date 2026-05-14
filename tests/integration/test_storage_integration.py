from __future__ import annotations

import os
import logging
from datetime import datetime

import pytest

from pbimonitor.infrastructure.storage.db import PostgresStorage


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_DSN"),
    reason="Set TEST_DATABASE_DSN and TEST_DATABASE_SCHEMA for integration run",
)
def test_storage_roundtrip() -> None:
    dsn = os.environ["TEST_DATABASE_DSN"]
    schema = os.getenv("TEST_DATABASE_SCHEMA", "public")
    storage = PostgresStorage(
        dsn=dsn,
        schema=schema,
        min_size=1,
        max_size=2,
        logger=logging.getLogger("test-storage"),
    )
    try:
        storage.upsert_baseline_hash("test-report", "Test Report", "abc123")
        assert storage.get_baseline_hash("test-report") == "abc123"
        storage.save_check_result(
            report_id="test-report",
            report_name="Test Report",
            report_url="https://powerbi.example.com/reports/test",
            status="unchanged",
            check_time=datetime.utcnow(),
            diff_percent=0.0,
            screenshot_hash="abc123",
            delta_compressed=b"",
            error=None,
            duration_sec=1.2,
            next_check_at=None,
        )
    finally:
        storage.close()

