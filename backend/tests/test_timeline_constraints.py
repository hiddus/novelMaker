import os
import tempfile
import unittest

from app.core.config import get_settings
from app.schemas.domain import TimelineConstraint
from app.services.store import WorkspaceStore


class TimelineConstraintStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_data_dir = os.environ.get("NOVELMAKER_DATA_DIR")
        os.environ["NOVELMAKER_DATA_DIR"] = self.temp_dir.name
        get_settings.cache_clear()
        self.store = WorkspaceStore()
        self.project_id = "proj_test"

    def tearDown(self) -> None:
        if self.original_data_dir is None:
            os.environ.pop("NOVELMAKER_DATA_DIR", None)
        else:
            os.environ["NOVELMAKER_DATA_DIR"] = self.original_data_dir
        get_settings.cache_clear()

    def _constraint(
        self,
        *,
        chapter_number: int,
        status: str = "warning",
        constraint_type: str = "travel",
        description: str = "地点切换必须存在明确转场链路",
        related_character_id: str | None = "char_1",
        evidence: list[str] | None = None,
    ) -> TimelineConstraint:
        return TimelineConstraint(
            project_id=self.project_id,
            chapter_number=chapter_number,
            constraint_type=constraint_type,  # type: ignore[arg-type]
            severity="high",
            related_node_id=f"timeline_{chapter_number}",
            related_character_id=related_character_id,
            description=description,
            evidence=evidence or ["old", "new"],
            status=status,  # type: ignore[arg-type]
            recommendation="补充转场。",
        )

    def test_sync_builds_evolution_chain_for_continued_risk(self) -> None:
        first = self.store.sync_timeline_constraints(
            self.project_id,
            3,
            [self._constraint(chapter_number=3, status="warning")],
        )[0]

        second = self.store.sync_timeline_constraints(
            self.project_id,
            4,
            [self._constraint(chapter_number=4, status="warning")],
        )[0]

        all_constraints = {item.id: item for item in self.store.list_timeline_constraints(self.project_id)}
        self.assertEqual(second.previous_constraint_id, first.id)
        self.assertTrue(second.is_current)
        self.assertEqual(all_constraints[first.id].status, "warning")
        self.assertFalse(all_constraints[first.id].is_current)

    def test_resolve_stale_only_resolves_current_constraint(self) -> None:
        self.store.sync_timeline_constraints(
            self.project_id,
            3,
            [self._constraint(chapter_number=3, status="warning")],
        )
        current = self.store.sync_timeline_constraints(
            self.project_id,
            4,
            [self._constraint(chapter_number=4, status="warning")],
        )[0]

        resolved_count = self.store.resolve_stale_timeline_constraints(self.project_id, 7)
        constraints = self.store.list_timeline_constraints(self.project_id)
        historical = next(item for item in constraints if item.id == current.previous_constraint_id)
        latest = next(item for item in constraints if item.id == current.id)

        self.assertEqual(resolved_count, 1)
        self.assertEqual(historical.status, "warning")
        self.assertFalse(historical.is_current)
        self.assertEqual(latest.status, "resolved")
        self.assertEqual(latest.resolved_in_chapter, 7)

    def test_resolve_patch_constraint_uses_rerun_end_chapter(self) -> None:
        patch_constraint = self._constraint(
            chapter_number=5,
            constraint_type="patch",
            description="开放补丁尚未消化，继续推进时间线存在风险",
            evidence=["retcon_1"],
        )
        self.store.sync_timeline_constraints(self.project_id, 5, [patch_constraint])

        resolved_count = self.store.resolve_patch_timeline_constraints(
            self.project_id,
            "retcon_1",
            resolved_in_chapter=9,
        )

        resolved = self.store.list_timeline_constraints(self.project_id)[0]
        self.assertEqual(resolved_count, 1)
        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.resolved_in_chapter, 9)
        self.assertFalse(resolved.is_current)

    def test_truncate_restores_previous_constraint_as_current(self) -> None:
        first = self.store.sync_timeline_constraints(
            self.project_id,
            3,
            [self._constraint(chapter_number=3, status="warning")],
        )[0]
        self.store.sync_timeline_constraints(
            self.project_id,
            4,
            [self._constraint(chapter_number=4, status="warning")],
        )

        removed = self.store.truncate_project_from_chapter(self.project_id, 4)
        constraints = self.store.list_timeline_constraints(self.project_id)

        self.assertEqual(removed["timeline_constraints"], 1)
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].id, first.id)
        self.assertTrue(constraints[0].is_current)
        self.assertIsNone(constraints[0].previous_constraint_id)


if __name__ == "__main__":
    unittest.main()
