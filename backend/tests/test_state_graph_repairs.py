import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ContinuityReport,
    Project,
    ReaderCouncilReport,
    ReviewReport,
    Snapshot,
)
from app.services.state_graph_diagnostics import build_state_graph_diagnostics
from app.services.state_graph_repair import attach_state_graph_repair_suggestions, build_state_graph_recovery_plan
from app.services.store import WorkspaceStore


class StateGraphRepairSuggestionTests(unittest.TestCase):
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

    def _add_review_chain(self, chapter: ChapterDraft) -> None:
        self.store.save_review(
            self.project.id,
            ReviewReport(project_id=self.project.id, chapter_number=chapter.chapter_number, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=chapter.chapter_number, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=chapter.chapter_number, chapter_id=chapter.id, status="strong"),
        )

    def test_projection_gap_suggests_recovery_from_problem_chapter(self) -> None:
        chapter = ChapterDraft(
            chapter_number=2,
            title="第二章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter)
        self._add_review_chain(chapter)

        with patch("app.services.state_graph_diagnostics.store", self.store), patch(
            "app.services.state_graph_repair.store",
            self.store,
        ):
            diagnostics = attach_state_graph_repair_suggestions(
                self.project.id,
                build_state_graph_diagnostics(self.project.id),
            )

        target = next(item for item in diagnostics if item.summary == "已批准章节缺少 snapshot")
        self.assertIsNotNone(target.repair_suggestion)
        self.assertEqual(target.repair_suggestion.scheduler_mode, "recovery")
        self.assertEqual(target.repair_suggestion.start_chapter, 2)
        self.assertEqual(target.repair_suggestion.end_chapter, 2)
        self.assertTrue(target.repair_suggestion.can_create_scheduler_task)

    def test_reference_gap_suggests_recovery_window_to_latest_chapter(self) -> None:
        chapter_two = ChapterDraft(
            chapter_number=2,
            title="第二章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        chapter_three = ChapterDraft(
            chapter_number=3,
            title="第三章",
            content="内容",
            summary="摘要",
            status="draft",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter_two)
        self.store.add_chapter(self.project.id, chapter_three)
        self._add_review_chain(chapter_two)
        self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter_two.id,
                chapter_title=chapter_two.title,
                recent_event_ids=["event_missing"],
                summary="坏快照",
            ),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store), patch(
            "app.services.state_graph_repair.store",
            self.store,
        ):
            diagnostics = attach_state_graph_repair_suggestions(
                self.project.id,
                build_state_graph_diagnostics(self.project.id),
            )

        target = next(item for item in diagnostics if item.summary == "Snapshot 存在悬空引用")
        self.assertIsNotNone(target.repair_suggestion)
        self.assertEqual(target.repair_suggestion.recommended_action, "rerun_window")
        self.assertEqual(target.repair_suggestion.start_chapter, 1)
        self.assertEqual(target.repair_suggestion.end_chapter, 3)

    def test_recovery_plan_aggregates_window_from_critical_diagnostics(self) -> None:
        chapter_two = ChapterDraft(
            chapter_number=2,
            title="第二章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        chapter_four = ChapterDraft(
            chapter_number=4,
            title="第四章",
            content="内容",
            summary="摘要",
            status="draft",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter_two)
        self.store.add_chapter(self.project.id, chapter_four)
        self._add_review_chain(chapter_two)
        self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter_two.id,
                chapter_title=chapter_two.title,
                recent_event_ids=["event_missing"],
                summary="坏快照",
            ),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store), patch(
            "app.services.state_graph_repair.store",
            self.store,
        ):
            diagnostics = attach_state_graph_repair_suggestions(
                self.project.id,
                build_state_graph_diagnostics(self.project.id),
            )
            plan = build_state_graph_recovery_plan(diagnostics)

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertTrue(plan.can_create_scheduler_task)
        self.assertEqual(plan.scheduler_mode, "recovery")
        self.assertEqual(plan.start_chapter, 1)
        self.assertEqual(plan.end_chapter, 4)
        self.assertGreaterEqual(plan.critical_issue_count, 1)
        self.assertTrue(plan.summary_lines)


if __name__ == "__main__":
    unittest.main()
