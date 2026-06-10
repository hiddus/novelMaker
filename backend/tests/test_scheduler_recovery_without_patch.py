import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import GovernanceDecision, Project, RetconPatch, SchedulerTaskCreate
from app.services import scheduler as scheduler_service
from app.services.store import WorkspaceStore


class SchedulerRecoveryWithoutPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_data_dir = os.environ.get("NOVELMAKER_DATA_DIR")
        os.environ["NOVELMAKER_DATA_DIR"] = self.temp_dir.name
        get_settings.cache_clear()
        self.store = WorkspaceStore()
        self.project = self.store.create_project(
            Project(
                title="test",
                premise="premise",
                genre="玄幻",
                target_words=100000,
                target_chapters=100,
                tone="热血升级",
            )
        )

    def tearDown(self) -> None:
        if self.original_data_dir is None:
            os.environ.pop("NOVELMAKER_DATA_DIR", None)
        else:
            os.environ["NOVELMAKER_DATA_DIR"] = self.original_data_dir
        get_settings.cache_clear()

    def test_recovery_task_can_be_created_without_patch(self) -> None:
        with patch.object(scheduler_service, "store", self.store):
            task = scheduler_service.create_scheduler_task(
                self.project,
                SchedulerTaskCreate(
                    start_chapter=5,
                    end_chapter=6,
                    mode="recovery",
                    writer_mode="mock",
                ),
            )

        self.assertEqual(task.mode, "recovery")
        self.assertIsNone(task.patch_id)
        self.assertEqual(task.stage, "rerunning")
        self.assertEqual(task.next_chapter, 5)

    def test_recovery_task_without_patch_can_finish_rerun_step(self) -> None:
        with patch.object(scheduler_service, "store", self.store):
            task = scheduler_service.create_scheduler_task(
                self.project,
                SchedulerTaskCreate(
                    start_chapter=5,
                    end_chapter=5,
                    mode="recovery",
                    writer_mode="mock",
                ),
            )

        with (
            patch.object(scheduler_service, "store", self.store),
            patch.object(
                scheduler_service,
                "evaluate_governance_before_step",
                return_value=(None, GovernanceDecision()),
            ),
            patch.object(
                scheduler_service,
                "evaluate_governance_after_chapter",
                return_value=(None, GovernanceDecision()),
            ),
            patch.object(
                scheduler_service,
                "execute_write",
                return_value={"chapter": {"status": "approved"}},
            ),
        ):
            updated = scheduler_service.process_scheduler_step(self.project, task.id)

        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.stage, "completed")
        self.assertEqual(updated.completed_chapters, [5])

    def test_recovery_task_without_patch_is_rejected_when_open_patch_exists(self) -> None:
        self.store.save_retcon_patch(
            self.project.id,
            RetconPatch(
                project_id=self.project.id,
                target_chapter_number=3,
                reason="修正文脉设定",
                affected_chapter_numbers=[4, 5],
                removed_chapter_numbers=[4, 5],
                impact_summary=["ch4-5 需重跑"],
                recommended_rerun_from=4,
                status="replanned",
            ),
        )

        with patch.object(scheduler_service, "store", self.store):
            with self.assertRaisesRegex(ValueError, "未消化的 Retcon Patch"):
                scheduler_service.create_scheduler_task(
                    self.project,
                    SchedulerTaskCreate(
                        start_chapter=5,
                        end_chapter=6,
                        mode="recovery",
                        writer_mode="mock",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
