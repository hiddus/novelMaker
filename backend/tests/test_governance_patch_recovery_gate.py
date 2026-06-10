import os
import tempfile
import unittest

from app.core.config import get_settings
from app.schemas.domain import Project, RetconPatch, SchedulerTask
from app.services.governance import evaluate_governance_before_step
from app.services.store import WorkspaceStore


class GovernancePatchRecoveryGateTests(unittest.TestCase):
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
                affected_chapter_numbers=[4, 5],
                removed_chapter_numbers=[4, 5],
                impact_summary=["ch4-5 需重跑"],
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

    def test_patch_bound_recovery_can_pass_patch_gate(self) -> None:
        _, decision = evaluate_governance_before_step(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=4,
                end_chapter=5,
                next_chapter=4,
                mode="recovery",
                patch_id=self.patch.id,
            ),
        )

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")

    def test_unbound_recovery_is_blocked_by_open_patch_gate(self) -> None:
        _, decision = evaluate_governance_before_step(
            self.project.id,
            SchedulerTask(
                project_id=self.project.id,
                start_chapter=4,
                end_chapter=5,
                next_chapter=4,
                mode="recovery",
            ),
        )

        self.assertEqual(decision.action, "pause")
        self.assertEqual(decision.status, "blocked")
        self.assertEqual(decision.signal, "state")
        self.assertIn("Retcon Patch", decision.reason)


if __name__ == "__main__":
    unittest.main()
