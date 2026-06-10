from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import get_settings
from app.services.scheduler import process_scheduler_step
from app.services.store import store


class SchedulerWorker:
    def __init__(self, poll_interval_seconds: float | None = None, lease_seconds: int | None = None) -> None:
        settings = get_settings()
        self.poll_interval_seconds = poll_interval_seconds or settings.worker_poll_interval_seconds
        self.lease_seconds = lease_seconds or settings.worker_lease_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.worker_id = f"worker_{uuid4().hex[:8]}"
        self.mode = "embedded"
        self.started_at: datetime | None = None
        self.last_tick_at: datetime | None = None
        self.last_claimed_job_id: str | None = None
        self.active_job_id: str | None = None
        self.processed_jobs: int = 0
        self.failed_jobs: int = 0

    def start(self, *, mode: str = "embedded") -> None:
        if self._thread and self._thread.is_alive():
            return
        self.mode = mode
        self._stop_event.clear()
        self.started_at = datetime.now(UTC)
        self._thread = threading.Thread(target=self._loop, name="novelmaker-scheduler-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def run_forever(self, *, mode: str = "standalone") -> None:
        self.mode = mode
        self._stop_event.clear()
        self.started_at = datetime.now(UTC)
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.poll_interval_seconds)

    def snapshot(self):  # type: ignore[no-untyped-def]
        settings = get_settings()
        return store.build_worker_snapshot(
            {
                "worker_id": self.worker_id,
                "mode": self.mode,
                "is_running": self.is_running() or self.mode == "standalone",
                "embedded_worker_enabled": settings.embedded_worker_enabled,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
                "last_claimed_job_id": self.last_claimed_job_id,
                "active_job_id": self.active_job_id,
                "processed_jobs": self.processed_jobs,
                "failed_jobs": self.failed_jobs,
                "poll_interval_seconds": self.poll_interval_seconds,
            }
        )

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.poll_interval_seconds)

    def run_once(self) -> None:
        self.last_tick_at = datetime.now(UTC)
        job = store.claim_next_queue_job(self.worker_id, self.lease_seconds)
        if job is None:
            self.active_job_id = None
            return
        self.last_claimed_job_id = job.id
        self.active_job_id = job.id
        try:
            self._process_job(job.project_id, job.id, job.task_id)
        finally:
            self.active_job_id = None

    def _process_job(self, project_id: str, job_id: str, task_id: str) -> None:
        project = store.get_project(project_id)
        if project is None:
            self.failed_jobs += 1
            store.finish_queue_job(project_id, job_id, status="failed", last_error="project not found")
            return

        task = store.get_scheduler_task(project_id, task_id)
        if task is None:
            self.failed_jobs += 1
            store.finish_queue_job(project_id, job_id, status="failed", last_error="scheduler task not found")
            return

        try:
            updated_task = process_scheduler_step(project, task_id)
        except Exception as exc:  # pragma: no cover - safety net
            self.failed_jobs += 1
            store.finish_queue_job(project_id, job_id, status="failed", last_error=str(exc))
            return

        summary = updated_task.stage_message or f"任务状态={updated_task.status}"
        if updated_task.status in {"completed", "paused"}:
            store.finish_queue_job(project_id, job_id, status="completed", result_summary=summary)
            self.processed_jobs += 1
            return

        if updated_task.status == "failed":
            store.finish_queue_job(
                project_id,
                job_id,
                status="failed",
                result_summary=summary,
                last_error=updated_task.last_error,
            )
            self.failed_jobs += 1
            return

        store.finish_queue_job(project_id, job_id, status="completed", result_summary=summary)
        store.enqueue_scheduler_task_job(project_id, updated_task, f"续跑任务 {updated_task.id} / 下一章 {updated_task.next_chapter}")
        self.processed_jobs += 1


def run_standalone_worker() -> None:
    worker = SchedulerWorker()
    worker.run_forever(mode="standalone")


scheduler_worker = SchedulerWorker()
