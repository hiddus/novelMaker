import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import Project, RerunRequest, RetconPatch, SchedulerTaskCreate
from app.services import pipeline as pipeline_service
from app.services import scheduler as scheduler_service
from app.services.store import WorkspaceStore


class PatchRerunWindowTests(unittest.TestCase):
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
        self.patch = self.store.save_retcon_patch(
            self.project.id,
            RetconPatch(
                project_id=self.project.id,
                target_chapter_number=3,
                reason="修正文脉设定",
                affected_chapter_numbers=[4, 5, 6],
                removed_chapter_numbers=[4, 5, 6],
                impact_summary=["ch4-6 需重跑"],
                recommended_rerun_from=4,
                status="replanned",
            ),
        )

    def tearDown(self) -> None:
        if self.original_data_dir is None:
            os.environ.pop("NOVELMAKER_DATA_DIR", None)
        else:
            os.environ["NOVELMAKER_DATA_DIR"] = self.original_data_dir
        get_settings.cache_clear()

    def test_recovery_task_rejects_start_after_patch_window_start(self) -> None:
        with patch.object(scheduler_service, "store", self.store):
            with self.assertRaisesRegex(ValueError, "起点不能晚于补丁建议重跑起点"):
                scheduler_service.create_scheduler_task(
                    self.project,
                    SchedulerTaskCreate(
                        start_chapter=5,
                        end_chapter=6,
                        mode="recovery",
                        writer_mode="mock",
                        patch_id=self.patch.id,
                    ),
                )

    def test_recovery_task_rejects_end_before_patch_window_end(self) -> None:
        with patch.object(scheduler_service, "store", self.store):
            with self.assertRaisesRegex(ValueError, "结束章节不能早于补丁影响窗口末章"):
                scheduler_service.create_scheduler_task(
                    self.project,
                    SchedulerTaskCreate(
                        start_chapter=4,
                        end_chapter=5,
                        mode="recovery",
                        writer_mode="mock",
                        patch_id=self.patch.id,
                    ),
                )

    def test_execute_rerun_returns_failed_result_when_patch_window_incomplete(self) -> None:
        with patch.object(pipeline_service, "store", self.store):
            result = pipeline_service.execute_rerun(
                self.project,
                RerunRequest(
                    patch_id=self.patch.id,
                    from_chapter=4,
                    end_chapter=5,
                    tone="热血升级",
                    writer_mode="mock",
                ),
            )

        self.assertEqual(result.status, "failed")
        self.assertIn("补丁影响窗口末章", result.message)
        saved_patch = next(item for item in self.store.list_retcon_patches(self.project.id) if item.id == self.patch.id)
        self.assertEqual(saved_patch.status, "replanned")


if __name__ == "__main__":
    unittest.main()
