from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Report:
    id: str
    name: str
    url: str
    interval_minutes: int
    start_time: str = "09:00"
    threshold: float = 5.0
    enabled: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RenderResult:
    report_id: str
    screenshot_path: Path
    rendered_at: datetime
    render_duration_ms: int
    screenshot_hash: Optional[str]


@dataclass(frozen=True)
class DiffResult:
    report_id: str
    baseline_hash: Optional[str]
    current_hash: Optional[str]
    hamming_distance: int
    diff_percent: float
    changed_blocks: list[tuple[int, int, int, int, float]]
    delta_bytes: Optional[bytes]
    diff_image_path: Optional[Path]
    diff_duration_ms: int

