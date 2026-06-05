from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from pbimonitor.application.dto.report_dto import CheckReportResultDto
from pbimonitor.application.usecases.diff_report import DiffReportUseCase
from pbimonitor.application.usecases.update_storage import UpdateStorageUseCase
from pbimonitor.domain.reports.entities import Report
from pbimonitor.domain.reports.services import DiffPolicy, ReportDiffService
from pbimonitor.exceptions import DiffComputationError
from pbimonitor.infrastructure.selenium.client import SeleniumClient
from pbimonitor.metrics import MetricsRegistry


class CheckReportUseCase:
    def __init__(
        self,
        selenium_client: SeleniumClient,
        storage_usecase: UpdateStorageUseCase,
        diff_usecase: DiffReportUseCase,
        diff_service: ReportDiffService,
        metrics: MetricsRegistry,
        screenshots_dir: Path,
        logger: logging.Logger,
    ) -> None:
        self._selenium_client = selenium_client
        self._storage = storage_usecase
        self._diff_usecase = diff_usecase
        self._diff_service = diff_service
        self._metrics = metrics
        self._screenshots_dir = screenshots_dir
        self._logger = logger

    def execute(self, report: Report, policy: DiffPolicy) -> CheckReportResultDto:
        started = time.monotonic()
        report_dir = self._screenshots_dir / "changes" / report.id
        baseline_dir = self._screenshots_dir / "baselines"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        init_baseline = baseline_dir / f"{report.id}_init_baseline.png"
        last_baseline = report_dir / "last_baseline.png"
        current = report_dir / "current_screenshot.png"
        diff_path = report_dir / "current_screenshot_diff.png"
        now = datetime.utcnow()
        next_check_at = now + timedelta(minutes=report.interval_minutes)

        try:
            baseline_exists = (
                self._storage.baseline_hash(report.id) is not None
                and init_baseline.exists()
                and last_baseline.exists()
            )

            render_duration_ms = self._selenium_client.take_screenshot(report.url, current if baseline_exists else init_baseline)
            self._metrics.track_render(render_duration_ms)

            if not baseline_exists:
                shutil.copy2(init_baseline, last_baseline)
                hash_value = self._diff_service.calculate_hash(last_baseline)
                if hash_value is None:
                    raise DiffComputationError("hash_value is empty for baseline")
                self._storage.save_baseline(report.id, report.name, hash_value)
                result = CheckReportResultDto(
                    report_id=report.id,
                    report_name=report.name,
                    report_url=report.url,
                    status="baseline_created",
                    check_time=now,
                    diff_percent=0.0,
                    screenshot_hash=hash_value,
                    error=None,
                    duration_sec=round(time.monotonic() - started, 2),
                    next_check_at=next_check_at,
                    render_duration_ms=render_duration_ms,
                    diff_duration_ms=0,
                    delta_size_bytes=0,
                )
                self._storage.execute(result, None)
                return result

            diff_result = self._diff_usecase.execute(
                report_id=report.id,
                baseline_path=last_baseline,
                current_path=current,
                diff_output_path=diff_path,
                policy=policy,
                delta_encoding_baseline_path=init_baseline,
            )
            self._metrics.track_diff(diff_result.diff_duration_ms)
            delta_size = len(diff_result.delta_bytes) if diff_result.delta_bytes else 0
            self._metrics.track_delta_size(delta_size)
            self._metrics.track_below_diff_threshold(diff_result.diff_percent < report.threshold)

            status = "changed" if diff_result.diff_percent > 0 else "unchanged"
            os_replace_safe(current, last_baseline)
            if diff_result.current_hash:
                self._storage.save_baseline(report.id, report.name, diff_result.current_hash)
            result = CheckReportResultDto(
                report_id=report.id,
                report_name=report.name,
                report_url=report.url,
                status=status,
                check_time=now,
                diff_percent=diff_result.diff_percent,
                screenshot_hash=diff_result.current_hash,
                error=None,
                duration_sec=round(time.monotonic() - started, 2),
                next_check_at=next_check_at,
                render_duration_ms=render_duration_ms,
                diff_duration_ms=diff_result.diff_duration_ms,
                delta_size_bytes=delta_size,
            )
            self._storage.execute(result, diff_result.delta_bytes)
            return result
        except Exception as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            self._logger.error("check_report_failed", extra={"report_id": report.id, "error": str(exc)})
            failure = CheckReportResultDto(
                report_id=report.id,
                report_name=report.name,
                report_url=report.url,
                status="error",
                check_time=now,
                diff_percent=None,
                screenshot_hash=None,
                error=str(exc),
                duration_sec=round(time.monotonic() - started, 2),
                next_check_at=next_check_at,
                render_duration_ms=0,
                diff_duration_ms=0,
                delta_size_bytes=0,
            )
            self._storage.execute(failure, None)
            return failure


def os_replace_safe(current: Path, target: Path) -> None:
    if target.exists():
        target.unlink()
    current.replace(target)

