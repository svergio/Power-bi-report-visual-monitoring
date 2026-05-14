from __future__ import annotations

from pbimonitor.application.dto.report_dto import CheckReportResultDto
from pbimonitor.domain.reports.repositories import MonitoringStorageRepository


class UpdateStorageUseCase:
    def __init__(self, storage: MonitoringStorageRepository) -> None:
        self._storage = storage

    def execute(self, result: CheckReportResultDto, delta_compressed: bytes | None) -> None:
        self._storage.save_check_result(
            report_id=result.report_id,
            report_name=result.report_name,
            report_url=result.report_url,
            status=result.status,
            check_time=result.check_time,
            diff_percent=result.diff_percent,
            screenshot_hash=result.screenshot_hash,
            delta_compressed=delta_compressed,
            error=result.error,
            duration_sec=result.duration_sec,
            next_check_at=result.next_check_at,
        )

    def save_baseline(self, report_id: str, report_name: str, hash_value: str) -> None:
        self._storage.upsert_baseline_hash(
            report_id=report_id,
            report_name=report_name,
            hash_value=hash_value,
        )

    def baseline_hash(self, report_id: str) -> str | None:
        return self._storage.get_baseline_hash(report_id)

