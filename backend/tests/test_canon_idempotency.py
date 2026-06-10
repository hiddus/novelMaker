import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import ChapterDraft, ChapterPlan, Character, CharacterState, ContextPack, Project, StoryBible
from app.services import canon as canon_service
from app.services import graph_state as graph_state_service
from app.services.store import WorkspaceStore


class CanonIdempotencyTests(unittest.TestCase):
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

    def test_apply_extracted_update_to_canon_is_idempotent_for_same_chapter(self) -> None:
        lead = Character(name="林渊", role="lead", realm="炼气", core_motivation="突破")
        rival = Character(name="顾寒", role="support", realm="筑基", core_motivation="阻击")
        chapter = ChapterDraft(
            chapter_number=1,
            title="南域遇敌",
            content="林渊来到南域古城，与顾寒成为敌人，并埋下青铜钥匙伏笔。",
            summary="主角转入南域，与顾寒正面冲突。",
            status="approved",
            source="mock",
        )
        self.store.add_character_state(
            self.project.id,
            CharacterState(
                character_id=lead.id,
                chapter_number=0,
                location="北域",
                emotion="平静",
                goal="突破",
                note="前置状态",
            ),
        )
        context_pack = ContextPack(
            project_id=self.project.id,
            chapter_number=1,
            story_bible=StoryBible(),
            active_characters=[lead, rival],
            chapter_plan=ChapterPlan(
                chapter_number=1,
                goal="突破",
                conflict="与顾寒冲突",
                hook="青铜钥匙",
                pov_character_id=lead.id,
            ),
        )

        with (
            patch.object(canon_service, "store", self.store),
            patch.object(graph_state_service, "store", self.store),
        ):
            payload = canon_service.extract_chapter_update(self.project.id, chapter, context_pack)
            canon_service.apply_extracted_update_to_canon(
                self.project.id,
                chapter,
                context_pack,
                *payload,
            )
            first_counts = self._projection_counts()

            canon_service.apply_extracted_update_to_canon(
                self.project.id,
                chapter,
                context_pack,
                *payload,
            )
            second_counts = self._projection_counts()

        self.assertEqual(first_counts, second_counts)
        self.assertEqual(second_counts["events"], 1)
        self.assertEqual(second_counts["character_states"], 2)
        self.assertEqual(second_counts["relationship_edges"], 1)
        self.assertEqual(second_counts["timeline_nodes"], 1)
        self.assertEqual(second_counts["timeline_constraints"], 2)
        self.assertEqual(second_counts["extracted_updates"], 1)
        self.assertEqual(second_counts["snapshots"], 1)
        self.assertEqual(second_counts["versions"], 1)
        self.assertEqual(second_counts["hook_records"], 1)
        self.assertEqual(second_counts["hook_state_changes"], 1)

    def test_apply_extracted_update_to_canon_uses_single_store_write(self) -> None:
        lead = Character(name="林渊", role="lead", realm="炼气", core_motivation="突破")
        rival = Character(name="顾寒", role="support", realm="筑基", core_motivation="阻击")
        chapter = ChapterDraft(
            chapter_number=1,
            title="南域遇敌",
            content="林渊来到南域古城，与顾寒成为敌人，并埋下青铜钥匙伏笔。",
            summary="主角转入南域，与顾寒正面冲突。",
            status="approved",
            source="mock",
        )
        self.store.add_character_state(
            self.project.id,
            CharacterState(
                character_id=lead.id,
                chapter_number=0,
                location="北域",
                emotion="平静",
                goal="突破",
                note="前置状态",
            ),
        )
        context_pack = ContextPack(
            project_id=self.project.id,
            chapter_number=1,
            story_bible=StoryBible(),
            active_characters=[lead, rival],
            chapter_plan=ChapterPlan(
                chapter_number=1,
                goal="突破",
                conflict="与顾寒冲突",
                hook="青铜钥匙",
                pov_character_id=lead.id,
            ),
        )

        with (
            patch.object(canon_service, "store", self.store),
            patch.object(graph_state_service, "store", self.store),
            patch.object(self.store, "_write", wraps=self.store._write) as write_mock,
        ):
            payload = canon_service.extract_chapter_update(self.project.id, chapter, context_pack)
            canon_service.apply_extracted_update_to_canon(
                self.project.id,
                chapter,
                context_pack,
                *payload,
            )

        self.assertEqual(write_mock.call_count, 1)

    def _projection_counts(self) -> dict[str, int]:
        return {
            "events": len(self.store.list_events(self.project.id)),
            "character_states": len(self.store.list_character_states(self.project.id)),
            "relationship_edges": len(self.store.list_relationship_edges(self.project.id)),
            "timeline_nodes": len(self.store.list_timeline_nodes(self.project.id)),
            "timeline_constraints": len(self.store.list_timeline_constraints(self.project.id)),
            "extracted_updates": len(self.store.list_extracted_updates(self.project.id)),
            "snapshots": len(self.store.list_snapshots(self.project.id)),
            "versions": len(self.store.list_versions(self.project.id)),
            "hook_records": len(self.store.list_hook_records(self.project.id)),
            "hook_state_changes": len(self.store.list_hook_state_changes(self.project.id)),
        }


if __name__ == "__main__":
    unittest.main()
