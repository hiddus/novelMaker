import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ContinuityIssue,
    ContinuityReport,
    Project,
    ReaderCouncilReport,
    SchedulerTask,
)
from app.services import memory as memory_service
from app.services.governance import evaluate_governance_after_chapter
from app.services.store import WorkspaceStore


class StaleDerivedReportTests(unittest.TestCase):
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

    def _revision_pair(self, chapter_number: int = 1) -> tuple[ChapterDraft, ChapterDraft]:
        old_chapter = ChapterDraft(
            chapter_number=chapter_number,
            title="旧稿",
            content="旧内容",
            summary="旧摘要",
            status="review_required",
            source="mock",
            revision_number=1,
            is_current=False,
        )
        current_chapter = ChapterDraft(
            chapter_number=chapter_number,
            title="新稿",
            content="新内容",
            summary="新摘要",
            status="approved",
            source="mock",
            revision_number=2,
            parent_chapter_id=old_chapter.id,
            is_current=True,
        )
        self.store.add_chapter(self.project.id, old_chapter)
        self.store.add_chapter(self.project.id, current_chapter)
        return old_chapter, current_chapter

    def _task(self, chapter_number: int = 1) -> SchedulerTask:
        return SchedulerTask(
            project_id=self.project.id,
            start_chapter=chapter_number,
            end_chapter=chapter_number,
            next_chapter=chapter_number,
        )

    def test_stale_continuity_report_does_not_block_governance(self) -> None:
        old_chapter, _ = self._revision_pair()
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=old_chapter.id,
                status="review_required",
                overall_risk="high",
                judges_triggered=["timeline"],
                summary="旧稿连续性冲突",
                issues=[
                    ContinuityIssue(
                        judge="timeline",
                        severity="high",
                        title="旧稿时间线冲突",
                        detail="该报告属于旧 revision",
                    )
                ],
            ),
        )

        with patch("app.services.governance.store", self.store):
            _, decision = evaluate_governance_after_chapter(self.project.id, self._task(), 1)

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")

    def test_stale_reader_report_does_not_block_governance(self) -> None:
        old_chapter, _ = self._revision_pair()
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=old_chapter.id,
                status="weak",
                overall_score=1.0,
                chase_score=1.0,
                payoff_score=1.0,
                pace_score=1.0,
                summary="旧稿读者反馈偏弱",
                concerns=["该报告属于旧 revision"],
            ),
        )

        with patch("app.services.governance.store", self.store):
            _, decision = evaluate_governance_after_chapter(self.project.id, self._task(), 1)

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")

    def test_long_term_memory_only_indexes_current_derived_reports(self) -> None:
        old_chapter, current_chapter = self._revision_pair()
        stale_continuity = self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=old_chapter.id,
                status="review_required",
                overall_risk="high",
                judges_triggered=["timeline"],
                summary="旧稿连续性冲突",
            ),
        )
        current_continuity = self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=current_chapter.id,
                status="clear",
                overall_risk="low",
                judges_triggered=["timeline"],
                summary="当前稿连续性正常",
            ),
        )
        stale_reader = self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=old_chapter.id,
                status="weak",
                overall_score=1.0,
                chase_score=1.0,
                payoff_score=1.0,
                pace_score=1.0,
                summary="旧稿读者反馈偏弱",
            ),
        )
        current_reader = self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=current_chapter.id,
                status="strong",
                overall_score=8.6,
                chase_score=8.3,
                payoff_score=8.7,
                pace_score=8.5,
                summary="当前稿读者反馈稳定",
            ),
        )

        with (
            patch.object(memory_service, "store", self.store),
            patch.object(memory_service, "rebuild_memory_index", lambda project_id, records: None),
        ):
            records = memory_service.rebuild_long_term_memory(self.project.id)

        continuity_records = [item for item in records if item.source_type == "continuity"]
        reader_records = [item for item in records if item.source_type == "reader"]

        self.assertEqual([item.source_id for item in continuity_records], [current_continuity.id])
        self.assertEqual([item.source_id for item in reader_records], [current_reader.id])
        self.assertNotIn(stale_continuity.id, [item.source_id for item in continuity_records])
        self.assertNotIn(stale_reader.id, [item.source_id for item in reader_records])


if __name__ == "__main__":
    unittest.main()
