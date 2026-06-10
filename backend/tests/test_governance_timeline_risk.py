import os
import tempfile
import unittest

from app.core.config import get_settings
from app.schemas.domain import GovernancePolicy, SchedulerTask, TimelineConstraint
from app.services.governance import evaluate_governance_before_step
from app.services.store import WorkspaceStore


class GovernanceTimelineRiskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_data_dir = os.environ.get("NOVELMAKER_DATA_DIR")
        os.environ["NOVELMAKER_DATA_DIR"] = self.temp_dir.name
        get_settings.cache_clear()
        self.store = WorkspaceStore()
        self.project_id = "proj_gov"

    def tearDown(self) -> None:
        if self.original_data_dir is None:
            os.environ.pop("NOVELMAKER_DATA_DIR", None)
        else:
            os.environ["NOVELMAKER_DATA_DIR"] = self.original_data_dir
        get_settings.cache_clear()

    def _constraint(self, *, chapter_number: int, status: str = "warning") -> TimelineConstraint:
        return TimelineConstraint(
            project_id=self.project_id,
            chapter_number=chapter_number,
            constraint_type="travel",
            severity="high",
            related_node_id=f"timeline_{chapter_number}",
            related_character_id="char_1",
            description="地点切换必须存在明确转场链路",
            evidence=["旧地点", "新地点"],
            status=status,  # type: ignore[arg-type]
            recommendation="补充转场。",
        )

    def _task(self, *, mode: str = "write") -> SchedulerTask:
        return SchedulerTask(
            project_id=self.project_id,
            start_chapter=5,
            end_chapter=8,
            next_chapter=5,
            mode=mode,  # type: ignore[arg-type]
        )

    def test_blocks_before_step_when_continuing_timeline_risk_reaches_threshold(self) -> None:
        policy = self.store.get_governance_policy(self.project_id).model_copy(
            update={
                "pause_on_continuing_timeline_risk": True,
                "max_continuing_timeline_risks": 1,
            }
        )
        self.store.save_governance_policy(self.project_id, policy)

        self.store.sync_timeline_constraints(
            self.project_id,
            3,
            [self._constraint(chapter_number=3)],
        )
        self.store.sync_timeline_constraints(
            self.project_id,
            4,
            [self._constraint(chapter_number=4)],
        )

        _, decision = evaluate_governance_before_step(self.project_id, self._task())

        self.assertEqual(decision.action, "pause")
        self.assertEqual(decision.status, "blocked")
        self.assertEqual(decision.signal, "continuity")
        self.assertIn("时间线风险链", decision.reason)

    def test_recovery_task_can_pass_continuing_timeline_risk_gate(self) -> None:
        policy = GovernancePolicy(
            project_id=self.project_id,
            pause_on_continuing_timeline_risk=True,
            max_continuing_timeline_risks=1,
        )
        self.store.save_governance_policy(self.project_id, policy)

        self.store.sync_timeline_constraints(
            self.project_id,
            3,
            [self._constraint(chapter_number=3)],
        )
        self.store.sync_timeline_constraints(
            self.project_id,
            4,
            [self._constraint(chapter_number=4)],
        )

        _, decision = evaluate_governance_before_step(self.project_id, self._task(mode="recovery"))

        self.assertEqual(decision.action, "continue")
        self.assertEqual(decision.status, "clear")


if __name__ == "__main__":
    unittest.main()
