import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ContinuityReport,
    LLMStatus,
    Project,
    ReaderCouncilReport,
    ReviewReport,
)
from app.services.ops import build_run_ops_summary
from app.services.store import WorkspaceStore


class OpsStateGraphSummaryTests(unittest.TestCase):
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

    def test_ops_summary_includes_state_graph_recovery_plan(self) -> None:
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

        with patch("app.services.ops.store", self.store), patch(
            "app.services.state_graph_diagnostics.store",
            self.store,
        ), patch(
            "app.services.state_graph_repair.store",
            self.store,
        ), patch(
            "app.services.ops.get_llm_status",
            return_value=LLMStatus(readiness="blocked", writer_route="mock", detail="mock"),
        ):
            summary = build_run_ops_summary(self.project.id)

        self.assertIsNotNone(summary.state_graph_recovery_plan)
        assert summary.state_graph_recovery_plan is not None
        self.assertEqual(summary.state_graph_recovery_plan.start_chapter, 2)
        self.assertEqual(summary.state_graph_recovery_plan.end_chapter, 2)
        self.assertTrue(
            any(summary.state_graph_recovery_plan.title in item for item in summary.warnings)
        )


if __name__ == "__main__":
    unittest.main()
