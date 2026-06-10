import os
import tempfile
import unittest

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ContinuityReport,
    Project,
    ReaderCouncilReport,
    ReviewReport,
    SchedulerTask,
)
from app.services.governance import evaluate_governance_after_chapter, evaluate_governance_before_step
from app.services.store import WorkspaceStore


class GovernanceStateGraphTests(unittest.TestCase):
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

    def _critical_projection_gap(self, chapter_number: int = 1) -> ChapterDraft:
        chapter = ChapterDraft(
            chapter_number=chapter_number,
            title=f"第{chapter_number}章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter)
        self.store.save_review(
            self.project.id,
            ReviewReport(project_id=self.project.id, chapter_number=chapter_number, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=chapter_number, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=chapter_number, chapter_id=chapter.id, status="strong"),
        )
        return chapter

    def test_blocks_before_step_when_critical_state_graph_issue_exists(self) -> None:
        self._critical_projection_gap()

        _, decision = evaluate_governance_before_step(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=2,
                end_chapter=3,
                next_chapter=2,
                mode="write",
            ),
        )

        self.assertEqual(decision.action, "pause")
        self.assertEqual(decision.status, "blocked")
        self.assertEqual(decision.signal, "state")
        self.assertIn("状态图谱断链", decision.reason)
        self.assertTrue(any("建议 recovery 窗口" in item for item in decision.details))

    def test_recovery_task_can_pass_before_step_state_graph_gate(self) -> None:
        self._critical_projection_gap()

        _, decision = evaluate_governance_before_step(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=1,
                end_chapter=2,
                next_chapter=1,
                mode="recovery",
            ),
        )

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")

    def test_blocks_after_chapter_for_write_task_when_critical_state_graph_issue_exists(self) -> None:
        self._critical_projection_gap()

        _, decision = evaluate_governance_after_chapter(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=1,
                end_chapter=1,
                next_chapter=2,
                mode="write",
            ),
            1,
        )

        self.assertEqual(decision.action, "pause")
        self.assertEqual(decision.status, "blocked")
        self.assertEqual(decision.signal, "state")
        self.assertIn("状态图谱断链", decision.reason)

    def test_recovery_task_only_blocks_on_finish_when_state_graph_issue_remains(self) -> None:
        self._critical_projection_gap()

        _, intermediate = evaluate_governance_after_chapter(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=1,
                end_chapter=3,
                next_chapter=2,
                mode="recovery",
            ),
            1,
        )
        self.assertEqual(intermediate.action, "continue")
        self.assertEqual(intermediate.status, "clear")

        _, final = evaluate_governance_after_chapter(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=1,
                end_chapter=1,
                next_chapter=2,
                mode="recovery",
            ),
            1,
        )
        self.assertEqual(final.action, "pause")
        self.assertEqual(final.status, "blocked")
        self.assertEqual(final.signal, "state")
        self.assertIn("恢复任务", final.reason)


if __name__ == "__main__":
    unittest.main()
