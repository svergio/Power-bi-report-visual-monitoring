from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CheckRecord:
    report_id: str
    report_name: str
    report_url: str
    check_time: datetime
    status: str
    diff_percent: Optional[float]
    screenshot_hash: Optional[str]
    delta_compressed: Optional[bytes]
    error: Optional[str]
    duration_sec: float
    next_check_at: Optional[datetime]

