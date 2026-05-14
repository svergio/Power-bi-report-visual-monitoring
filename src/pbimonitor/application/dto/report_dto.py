from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CheckReportResultDto:
    report_id: str
    report_name: str
    report_url: str
    status: str
    check_time: datetime
    diff_percent: Optional[float]
    screenshot_hash: Optional[str]
    error: Optional[str]
    duration_sec: float
    next_check_at: Optional[datetime]
    render_duration_ms: int
    diff_duration_ms: int
    delta_size_bytes: int

