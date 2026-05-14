from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from pbimonitor.application.dto.report_dto import CheckReportResultDto
from pbimonitor.domain.reports.entities import Report

WorkerCleanup = Callable[[], None]
CheckRunner = Callable[[Report], CheckReportResultDto]
WorkerFactory = Callable[[], tuple[CheckRunner, WorkerCleanup]]


@dataclass
class ScheduledJob:
    report: Report
    due_at: datetime
    last_duration_ms: int = 0
    failures: int = 0


class InProcessScheduler:
    """Планировщик в процессе с очередью и ограничением нагрузки между перезапусками."""

    def __init__(
        self,
        reports: list[Report],
        worker_count: int,
        worker_factory: WorkerFactory,
        logger: logging.Logger,
        worker_join_timeout_seconds: float = 120.0,
    ) -> None:
        self._reports = reports
        self._worker_count = max(1, worker_count)
        self._worker_factory = worker_factory
        self._logger = logger
        self._worker_join_timeout_seconds = worker_join_timeout_seconds
        self._stop_event = threading.Event()
        self._jobs = queue.PriorityQueue[tuple[float, int, ScheduledJob]]()
        self._workers: list[threading.Thread] = []
        self._job_seq = 0

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        now = datetime.now(timezone.utc)
        for report in self._reports:
            self._enqueue(ScheduledJob(report=report, due_at=now))

        self._workers = [
            threading.Thread(target=self._worker_loop, name=f"worker-{idx}", daemon=True)
            for idx in range(1, self._worker_count + 1)
        ]
        for worker in self._workers:
            worker.start()

        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop_event.set()
        for worker in self._workers:
            worker.join(timeout=self._worker_join_timeout_seconds)

    def _enqueue(self, job: ScheduledJob) -> None:
        self._job_seq += 1
        self._jobs.put((job.due_at.timestamp(), self._job_seq, job))

    def _worker_loop(self) -> None:
        run_check, cleanup = self._worker_factory()
        try:
            while not self._stop_event.is_set():
                try:
                    due_ts, _seq, job = self._jobs.get(timeout=1)
                except queue.Empty:
                    continue

                delay = due_ts - datetime.now(timezone.utc).timestamp()
                if delay > 0:
                    time.sleep(min(delay, 1))
                    self._enqueue(job)
                    self._jobs.task_done()
                    continue

                try:
                    result = run_check(job.report)
                    duration_ms = result.render_duration_ms
                    interval = self._next_interval(job.report.interval_minutes, duration_ms, 0)
                    next_due = datetime.now(timezone.utc) + timedelta(minutes=interval)
                    self._enqueue(
                        ScheduledJob(
                            report=job.report,
                            due_at=next_due,
                            last_duration_ms=duration_ms,
                            failures=0,
                        )
                    )
                except Exception:
                    self._logger.error(
                        "worker_check_failed",
                        exc_info=True,
                        extra={
                            "report_id": job.report.id,
                            "pipeline_exception": True,
                            "hint": (
                                "Обычно сценарий записывает ошибки в monitoring_checks; "
                                "здесь неперехваченное исключение в воркере."
                            ),
                        },
                    )
                    interval = self._next_interval(job.report.interval_minutes, job.last_duration_ms, job.failures + 1)
                    self._enqueue(
                        ScheduledJob(
                            report=job.report,
                            due_at=datetime.now(timezone.utc) + timedelta(minutes=interval),
                            last_duration_ms=job.last_duration_ms,
                            failures=job.failures + 1,
                        )
                    )
                finally:
                    self._jobs.task_done()
        finally:
            cleanup()

    def _next_interval(self, base_minutes: int, duration_ms: int, failures: int) -> int:
        multiplier = 1
        if duration_ms > 120_000:
            multiplier = 2
        if duration_ms > 300_000:
            multiplier = 3
        if failures > 0:
            multiplier += min(3, failures)
        return max(1, base_minutes * multiplier)
