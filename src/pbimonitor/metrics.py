from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from statistics import mean


@dataclass
class MetricsRegistry:
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    render_duration_ms: list[int] = field(default_factory=list)
    diff_duration_ms: list[int] = field(default_factory=list)
    delta_size_bytes: list[int] = field(default_factory=list)
    below_diff_threshold_samples: list[int] = field(default_factory=list)

    def track_render(self, value: int) -> None:
        with self._lock:
            self.render_duration_ms.append(value)

    def track_diff(self, value: int) -> None:
        with self._lock:
            self.diff_duration_ms.append(value)

    def track_delta_size(self, value: int) -> None:
        with self._lock:
            self.delta_size_bytes.append(value)

    def track_below_diff_threshold(self, value: bool) -> None:
        with self._lock:
            self.below_diff_threshold_samples.append(1 if value else 0)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return {
                "render_duration_ms_avg": mean(self.render_duration_ms) if self.render_duration_ms else 0.0,
                "diff_duration_ms_avg": mean(self.diff_duration_ms) if self.diff_duration_ms else 0.0,
                "delta_size_bytes_avg": mean(self.delta_size_bytes) if self.delta_size_bytes else 0.0,
                "below_diff_threshold_rate": (
                    mean(self.below_diff_threshold_samples) if self.below_diff_threshold_samples else 0.0
                ),
            }

    def emit(self, logger: logging.Logger) -> None:
        logger.info("metrics_snapshot", extra=self.snapshot())
