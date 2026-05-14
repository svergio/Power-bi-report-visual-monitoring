from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pbimonitor.domain.reports.entities import Report


class ReportRepository(ABC):
    @abstractmethod
    def list_enabled_reports(self) -> list[Report]:
        raise NotImplementedError


class MonitoringStorageRepository(ABC):
    @abstractmethod
    def get_baseline_hash(self, report_id: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def upsert_baseline_hash(self, report_id: str, report_name: str, hash_value: str) -> None:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

