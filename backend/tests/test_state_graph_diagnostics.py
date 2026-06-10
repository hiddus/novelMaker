import os
import tempfile
import unittest
from unittest.mock import patch

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    CharacterRelationshipEdge,
    ContinuityReport,
    Event,
    Project,
    ReaderCouncilReport,
    ReviewReport,
    Snapshot,
    TimelineConstraint,
    TimelineNode,
    VersionRecord,
)
from app.services.state_graph_diagnostics import build_state_graph_diagnostics
from app.services.store import WorkspaceStore


class StateGraphDiagnosticsTests(unittest.TestCase):
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

    def test_reports_missing_current_projection_for_approved_chapter(self) -> None:
        chapter = ChapterDraft(
            chapter_number=1,
            title="第一章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter)
        self.store.save_review(
            self.project.id,
            ReviewReport(project_id=self.project.id, chapter_number=1, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=1, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=1, chapter_id=chapter.id, status="strong"),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store):
            diagnostics = build_state_graph_diagnostics(self.project.id)

        summaries = {item.summary for item in diagnostics}
        self.assertIn("已批准章节缺少 snapshot", summaries)
        self.assertIn("已批准章节缺少 version", summaries)
        self.assertIn("已批准章节缺少 timeline node", summaries)

    def test_reports_dangling_references_and_multiple_current_heads(self) -> None:
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
            ReviewReport(project_id=self.project.id, chapter_number=2, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=2, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=2, chapter_id=chapter.id, status="strong"),
        )
        self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                recent_event_ids=["event_missing"],
                relationship_edge_ids=["rel_missing"],
                timeline_node_ids=["timeline_missing"],
                active_hook_ids=["hook_missing"],
                summary="坏快照",
            ),
        )
        self.store.add_version(
            self.project.id,
            VersionRecord(
                project_id=self.project.id,
                chapter_number=2,
                chapter_id=chapter.id,
                snapshot_id="snapshot_missing",
                extracted_update_id="extract_missing",
                version_label="chapter-2-v1",
            ),
        )
        self.store.save_timeline_constraint(
            self.project.id,
            TimelineConstraint(
                project_id=self.project.id,
                chapter_number=2,
                constraint_type="travel",
                evolution_key="travel::hero",
                previous_constraint_id="missing_prev",
                is_current=True,
                severity="high",
                related_node_id="timeline_missing",
                description="地点切换必须存在明确转场链路",
                evidence=["北域", "南域"],
                status="warning",
                recommendation="补转场",
            ),
        )
        self.store.save_timeline_constraint(
            self.project.id,
            TimelineConstraint(
                project_id=self.project.id,
                chapter_number=2,
                constraint_type="travel",
                evolution_key="travel::hero",
                is_current=True,
                severity="high",
                related_node_id="timeline_missing",
                description="地点切换必须存在明确转场链路",
                evidence=["北域", "南域"],
                status="violated",
                recommendation="补转场",
            ),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store):
            diagnostics = build_state_graph_diagnostics(self.project.id)

        summaries = {item.summary for item in diagnostics}
        self.assertIn("Snapshot 存在悬空引用", summaries)
        self.assertIn("VersionRecord 存在悬空引用", summaries)
        self.assertIn("时间线约束 previous_constraint_id 断链", summaries)
        self.assertIn("同一时间线演化链存在多条 current constraint", summaries)

    def test_reports_missing_relationship_current_head_and_timeline_node_dangling(self) -> None:
        chapter = ChapterDraft(
            chapter_number=3,
            title="第三章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter)
        self.store.save_review(
            self.project.id,
            ReviewReport(project_id=self.project.id, chapter_number=3, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=3, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=3, chapter_id=chapter.id, status="strong"),
        )
        self.store.add_relationship_edge(
            self.project.id,
            CharacterRelationshipEdge(
                project_id=self.project.id,
                chapter_number=1,
                source_character_id="char_a",
                target_character_id="char_b",
                pair_key="char_a::char_b",
                relation_type="ally",
                is_current=False,
            ),
        )
        self.store.add_timeline_node(
            self.project.id,
            TimelineNode(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                event_id="event_missing",
                label="坏节点",
                predecessor_node_ids=["timeline_missing"],
            ),
        )
        self.store.add_snapshot(
            self.project.id,
            Snapshot(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                timeline_node_ids=[],
                summary="坏快照",
            ),
        )
        self.store.add_version(
            self.project.id,
            VersionRecord(
                project_id=self.project.id,
                chapter_number=3,
                chapter_id=chapter.id,
                snapshot_id=self.store.list_snapshots(self.project.id)[0].id,
                extracted_update_id="extract_missing",
                version_label="chapter-3-v1",
            ),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store):
            diagnostics = build_state_graph_diagnostics(self.project.id)

        summaries = {item.summary for item in diagnostics}
        self.assertIn("关系链存在历史边但缺少 current relationship edge", summaries)
        self.assertIn("时间线节点 event_id 断链", summaries)
        self.assertIn("时间线节点 predecessor_node_ids 断链", summaries)

    def test_reports_cross_chapter_chain_order_regressions(self) -> None:
        chapter = ChapterDraft(
            chapter_number=4,
            title="第四章",
            content="内容",
            summary="摘要",
            status="approved",
            source="mock",
            is_current=True,
        )
        self.store.add_chapter(self.project.id, chapter)
        self.store.save_review(
            self.project.id,
            ReviewReport(project_id=self.project.id, chapter_number=4, chapter_id=chapter.id, status="approved"),
        )
        self.store.save_continuity_report(
            self.project.id,
            ContinuityReport(project_id=self.project.id, chapter_number=4, chapter_id=chapter.id, status="clear"),
        )
        self.store.save_reader_council_report(
            self.project.id,
            ReaderCouncilReport(project_id=self.project.id, chapter_number=4, chapter_id=chapter.id, status="strong"),
        )

        late_edge = self.store.add_relationship_edge(
            self.project.id,
            CharacterRelationshipEdge(
                project_id=self.project.id,
                chapter_number=5,
                source_character_id="char_a",
                target_character_id="char_b",
                pair_key="char_a::char_b",
                relation_type="ally",
                is_current=False,
            ),
        )
        self.store.add_relationship_edge(
            self.project.id,
            CharacterRelationshipEdge(
                project_id=self.project.id,
                chapter_number=4,
                source_character_id="char_a",
                target_character_id="char_b",
                pair_key="char_a::char_b",
                relation_type="enemy",
                previous_edge_id=late_edge.id,
                is_current=True,
            ),
        )

        future_node = self.store.add_timeline_node(
            self.project.id,
            TimelineNode(
                project_id=self.project.id,
                chapter_number=5,
                label="未来节点",
            ),
        )
        event = self.store.add_event(
            self.project.id,
            Event(
                chapter_number=5,
                summary="未来事件",
                event_type="chapter_result",
            ),
        )
        self.store.add_timeline_node(
            self.project.id,
            TimelineNode(
                project_id=self.project.id,
                chapter_number=4,
                chapter_id=chapter.id,
                event_id=event.id,
                label="当前节点",
                predecessor_node_ids=[future_node.id],
            ),
        )

        future_constraint = self.store.save_timeline_constraint(
            self.project.id,
            TimelineConstraint(
                project_id=self.project.id,
                chapter_number=5,
                constraint_type="travel",
                evolution_key="travel::hero",
                related_node_id=future_node.id,
                description="地点切换必须存在明确转场链路",
                evidence=["北域", "南域"],
                status="warning",
                recommendation="补转场",
            ),
        )
        self.store.save_timeline_constraint(
            self.project.id,
            TimelineConstraint(
                project_id=self.project.id,
                chapter_number=4,
                constraint_type="travel",
                evolution_key="travel::hero",
                previous_constraint_id=future_constraint.id,
                related_node_id=future_node.id,
                description="地点切换必须存在明确转场链路",
                evidence=["北域", "南域"],
                status="violated",
                recommendation="补转场",
            ),
        )

        with patch("app.services.state_graph_diagnostics.store", self.store):
            diagnostics = build_state_graph_diagnostics(self.project.id)

        summaries = {item.summary for item in diagnostics}
        self.assertIn("关系边演化链章节顺序倒挂", summaries)
        self.assertIn("时间线节点 predecessor 指向同章或未来章节", summaries)
        self.assertIn("时间线节点 event 章节号不一致", summaries)
        self.assertIn("时间线约束演化链章节顺序倒挂", summaries)


if __name__ == "__main__":
    unittest.main()
