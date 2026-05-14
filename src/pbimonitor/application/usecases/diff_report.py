from __future__ import annotations

from pathlib import Path

from pbimonitor.domain.reports.entities import DiffResult
from pbimonitor.domain.reports.services import DiffPolicy, ReportDiffService


class DiffReportUseCase:
    def __init__(self, diff_service: ReportDiffService) -> None:
        self._diff_service = diff_service

    def execute(
        self,
        report_id: str,
        baseline_path: Path,
        current_path: Path,
        diff_output_path: Path,
        policy: DiffPolicy,
        *,
        delta_encoding_baseline_path: Path | None = None,
    ) -> DiffResult:
        return self._diff_service.compare(
            report_id=report_id,
            baseline_path=baseline_path,
            current_path=current_path,
            diff_output_path=diff_output_path,
            policy=policy,
            delta_encoding_baseline_path=delta_encoding_baseline_path,
        )

