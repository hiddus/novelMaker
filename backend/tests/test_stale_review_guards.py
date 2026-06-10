import os
import tempfile
import unittest

from app.core.config import get_settings
from app.schemas.domain import ChapterDraft, Project, ReviewDecisionRequest, ReviewReport, RewriteChapterRequest, SchedulerTask
from app.services.governance import evaluate_governance_before_step
from app.services.pipeline import execute_review_decision, execute_rewrite
from app.services.store import WorkspaceStore


class StaleReviewGuardTests(unittest.TestCase):
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

    def _stale_review(self) -> ReviewReport:
        old_chapter = ChapterDraft(
            chapter_number=1,
            title="旧稿",
            content="旧内容",
            summary="旧摘要",
            status="review_required",
            source="mock",
            revision_number=1,
            is_current=False,
        )
        current_chapter = ChapterDraft(
            chapter_number=1,
            title="新稿",
            content="新内容",
            summary="新摘要",
            status="review_required",
            source="mock",
            revision_number=2,
            parent_chapter_id=old_chapter.id,
            is_current=True,
        )
        self.store.add_chapter(self.project.id, old_chapter)
        self.store.add_chapter(self.project.id, current_chapter)
        review = ReviewReport(
            project_id=self.project.id,
            chapter_number=1,
            chapter_id=old_chapter.id,
            status="review_required",
            decision_reason="待处理",
        )
        return self.store.save_review(self.project.id, review)

    def test_cannot_approve_stale_review(self) -> None:
        review = self._stale_review()

        with self.assertRaisesRegex(ValueError, "旧版本章节"):
            execute_review_decision(
                self.project,
                review.id,
                ReviewDecisionRequest(decision="approve", note="过期审批"),
            )

    def test_cannot_rewrite_stale_review(self) -> None:
        review = self._stale_review()

        with self.assertRaisesRegex(ValueError, "旧版本章节"):
            execute_rewrite(
                self.project,
                review.id,
                RewriteChapterRequest(writer_mode="mock", tone="热血升级", note="再次重写"),
            )

    def test_stale_pending_review_does_not_block_governance(self) -> None:
        self._stale_review()

        _, decision = evaluate_governance_before_step(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=2,
                end_chapter=3,
                next_chapter=2,
            ),
        )

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")


if __name__ == "__main__":
    unittest.main()
