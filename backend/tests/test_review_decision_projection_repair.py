import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import (
    CharacterRelationshipEdge,
    ChapterDraft,
    Event,
    ExtractedUpdate,
    HookRecord,
    HookStateChange,
    Project,
    ReviewDecisionRequest,
    ReviewReport,
    Snapshot,
    TimelineConstraint,
    TimelineNode,
    VersionRecord,
)
from app.services import pipeline as pipeline_service
from app.services.store import WorkspaceStore


class ReviewDecisionProjectionRepairTests(unittest.TestCase):
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

    def test_approve_rebuilds_projection_when_version_exists_but_projection_incomplete(self) -> None:
        chapter = self.store.add_chapter(
            self.project.id,
            ChapterDraft(
                chapter_number=1,
                title="第一章",
                content="内容",
                summary="摘要",
                status="review_required",
                source="mock",
                is_current=True,
            ),
        )
        review = self.store.save_review(
            self.project.id,
            ReviewReport(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=chapter.id,
                status="review_required",
                decision_reason="待处理",
            ),
        )
        self.store.add_version(
            self.project.id,
            VersionRecord(
                project_id=self.project.id,
                chapter_number=1,
                chapter_id=chapter.id,
                snapshot_id="snapshot_missing",
                extracted_update_id="extract_missing",
                version_label="chapter-1-v1",
            ),
        )

        repaired_update = ExtractedUpdate(project_id=self.project.id, chapter_number=1, summary="repair")
        repaired_snapshot = Snapshot(
            project_id=self.project.id,
            chapter_number=1,
            chapter_id=chapter.id,
            chapter_title=chapter.title,
            summary="snapshot",
        )
        repaired_version = VersionRecord(
            project_id=self.project.id,
            chapter_number=1,
            chapter_id=chapter.id,
            snapshot_id=repaired_snapshot.id,
            extracted_update_id=repaired_update.id,
            version_label="chapter-1-v2",
        )

        with (
            patch.object(pipeline_service, "store", self.store),
            patch.object(pipeline_service, "build_context_pack", return_value=None),
            patch.object(
                pipeline_service,
                "extract_chapter_update",
                return_value=(repaired_update, None, None, [], None, []),
            ),
            patch.object(
                pipeline_service,
                "apply_extracted_update_to_canon",
                return_value=(repaired_update, repaired_snapshot, repaired_version),
            ) as apply_mock,
        ):
            result = pipeline_service.execute_review_decision(
                self.project,
                review.id,
                ReviewDecisionRequest(decision="approve", note="人工通过"),
            )

        self.assertEqual(result.chapter.status, "approved")
        self.assertEqual(result.review.human_decision_status, "approved")
        self.assertEqual(result.snapshot.id, repaired_snapshot.id)
        self.assertEqual(result.version.id, repaired_version.id)
        apply_mock.assert_called_once()

    def test_projection_is_incomplete_when_relationship_timeline_or_hook_chain_is_missing(self) -> None:
        chapter = self.store.add_chapter(
            self.project.id,
            ChapterDraft(
                chapter_number=2,
                title="第二章",
                content="内容",
                summary="摘要",
                status="review_required",
                source="mock",
                is_current=True,
            ),
        )
        timeline_node = self.store.add_timeline_node(
            self.project.id,
            TimelineNode(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter.id,
                label="第二章节点",
            ),
        )
        extract = self.store.add_extracted_update(
            self.project.id,
            ExtractedUpdate(
                project_id=self.project.id,
                chapter_number=2,
                relationship_edge_ids=["rel_missing"],
                timeline_node_ids=[timeline_node.id],
                timeline_constraints=["地点切换必须存在明确转场链路"],
                hook_changes=["青铜钥匙"],
            ),
        )
        snapshot = self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                timeline_node_ids=[timeline_node.id],
                summary="snapshot",
            ),
        )
        self.store.add_version(
            self.project.id,
            VersionRecord(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter.id,
                snapshot_id=snapshot.id,
                extracted_update_id=extract.id,
                version_label="chapter-2-v1",
            ),
        )

        with patch.object(pipeline_service, "store", self.store):
            self.assertFalse(pipeline_service._chapter_projection_is_complete(self.project.id, chapter.id))

    def test_projection_is_complete_when_version_snapshot_graph_timeline_and_hooks_align(self) -> None:
        chapter = self.store.add_chapter(
            self.project.id,
            ChapterDraft(
                chapter_number=3,
                title="第三章",
                content="内容",
                summary="摘要",
                status="review_required",
                source="mock",
                is_current=True,
            ),
        )
        event = self.store.add_event(
            self.project.id,
            Event(
                chapter_number=3,
                summary="事件",
                event_type="chapter_result",
            ),
        )
        relationship = self.store.add_relationship_edge(
            self.project.id,
            CharacterRelationshipEdge(
                project_id=self.project.id,
                chapter_number=3,
                source_character_id="char_a",
                target_character_id="char_b",
                pair_key="char_a::char_b",
                relation_type="ally",
            ),
        )
        timeline_node = self.store.add_timeline_node(
            self.project.id,
            TimelineNode(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                event_id=event.id,
                label="第三章节点",
            ),
        )
        self.store.save_timeline_constraint(
            self.project.id,
            TimelineConstraint(
                project_id=self.project.id,
                chapter_number=3,
                constraint_type="travel",
                related_node_id=timeline_node.id,
                description="地点切换必须存在明确转场链路",
                evidence=["北域", "南域"],
                status="warning",
                recommendation="补转场",
            ),
        )
        hook = self.store.save_hook_record(
            self.project.id,
            HookRecord(
                project_id=self.project.id,
                content="青铜钥匙",
                created_in_chapter=3,
                source_chapter_id=chapter.id,
            ),
        )
        self.store.add_hook_state_change(
            self.project.id,
            HookStateChange(
                project_id=self.project.id,
                hook_id=hook.id,
                chapter_number=3,
                chapter_id=chapter.id,
                action="create",
                content=hook.content,
            ),
        )
        extract = self.store.add_extracted_update(
            self.project.id,
            ExtractedUpdate(
                project_id=self.project.id,
                chapter_number=3,
                event_ids=[event.id],
                relationship_edge_ids=[relationship.id],
                timeline_node_ids=[timeline_node.id],
                timeline_constraints=["地点切换必须存在明确转场链路"],
                hook_changes=["青铜钥匙"],
                new_hooks=["青铜钥匙"],
            ),
        )
        snapshot = self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                relationship_edge_ids=[relationship.id],
                timeline_node_ids=[timeline_node.id],
                active_hook_ids=[hook.id],
                recent_event_ids=[event.id],
                summary="snapshot",
            ),
        )
        self.store.add_version(
            self.project.id,
            VersionRecord(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                snapshot_id=snapshot.id,
                extracted_update_id=extract.id,
                version_label="chapter-3-v1",
            ),
        )

        with patch.object(pipeline_service, "store", self.store):
            self.assertTrue(pipeline_service._chapter_projection_is_complete(self.project.id, chapter.id))


if __name__ == "__main__":
    unittest.main()
