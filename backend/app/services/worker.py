from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from app.services.scheduler import process_scheduler_step
from app.services.store import store


class SchedulerWorker:
    def __init__(self, poll_interval_seconds: float = 1.0) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.started_at: datetime | None = None
        self.last_tick_at: datetime | None = None
        self.cycles: int = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
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

    def snapshot(self) -> dict[str, object]:
        return {
            "is_running": self.is_running(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "cycles": self.cycles,
            "poll_interval_seconds": self.poll_interval_seconds,
        }

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.poll_interval_seconds)

    def run_once(self) -> None:
        self.cycles += 1
        self.last_tick_at = datetime.now(UTC)
        for project in store.list_projects():
            for task in store.list_scheduler_tasks(project.id):
                if task.status != "running":
                    continue
                process_scheduler_step(project, task.id)


scheduler_worker = SchedulerWorker()
