from __future__ import annotations

from app.schemas.domain import CharacterRelationshipEdge, ContextPack, TimelineConstraint, TimelineNode
from app.services.store import store

_TIME_MARKER_ORDER = {
    "当夜": 0,
    "次日": 1,
    "翌日": 1,
    "三日后": 2,
    "七日后": 3,
    "半月后": 4,
    "一月后": 5,
}
_MUTUAL_RELATIONS = {"ally", "enemy", "family", "lover", "rival"}
_POSITIVE_RELATIONS = {"ally", "family", "lover", "mentor", "student"}
_NEGATIVE_RELATIONS = {"enemy", "rival"}


def _pair_key(source_character_id: str, target_character_id: str) -> str:
    ordered = sorted([source_character_id, target_character_id])
    return "::".join(ordered)


def _relationship_change_type(
    previous: CharacterRelationshipEdge | None,
    current: CharacterRelationshipEdge,
) -> tuple[str, float]:
    if previous is None:
        return "new", current.intensity
    if previous.relation_type == current.relation_type:
        return "reinforce", min(2.5, round(previous.intensity + 0.3, 2))
    if (
        previous.relation_type in _POSITIVE_RELATIONS
        and current.relation_type in _NEGATIVE_RELATIONS
    ) or (
        previous.relation_type in _NEGATIVE_RELATIONS
        and current.relation_type in _POSITIVE_RELATIONS
    ):
        return "reverse", min(2.8, round(max(previous.intensity, current.intensity) + 0.5, 2))
    return "shift", min(2.2, round(max(previous.intensity, current.intensity) + 0.2, 2))


def evolve_relationship_edges(
    project_id: str,
    chapter_number: int,
    edges: list[CharacterRelationshipEdge],
    *,
    existing_edges: list[CharacterRelationshipEdge] | None = None,
) -> list[CharacterRelationshipEdge]:
    existing_edges = existing_edges if existing_edges is not None else store.list_relationship_edges(project_id)
    current_edges = {
        item.pair_key or _pair_key(item.source_character_id, item.target_character_id): item
        for item in existing_edges
        if item.is_current
    }
    saved_edges: list[CharacterRelationshipEdge] = []
    for edge in edges:
        pair_key = _pair_key(edge.source_character_id, edge.target_character_id)
        previous = current_edges.get(pair_key)
        change_type, next_intensity = _relationship_change_type(previous, edge)
        updated = edge.model_copy(
            update={
                "pair_key": pair_key,
                "chapter_number": chapter_number,
                "direction": "mutual" if edge.relation_type in _MUTUAL_RELATIONS else edge.direction,
                "change_type": change_type,
                "previous_edge_id": previous.id if previous is not None else None,
                "is_current": True,
                "intensity": next_intensity,
            }
        )
        saved_edges.append(updated)
        current_edges[pair_key] = updated
    return saved_edges


def build_timeline_constraints(
    project_id: str,
    chapter_number: int,
    context_pack: ContextPack,
    timeline_node: TimelineNode,
    *,
    location_transitions: list[str],
    primary_character_id: str | None,
) -> list[TimelineConstraint]:
    constraints: list[TimelineConstraint] = []
    previous_nodes = store.list_timeline_nodes(project_id)
    previous_node = previous_nodes[-1] if previous_nodes else None

    previous_rank = _TIME_MARKER_ORDER.get(previous_node.time_marker, -1) if previous_node else -1
    current_rank = _TIME_MARKER_ORDER.get(timeline_node.time_marker, -1)
    if previous_node is not None:
        ordering_status = "clear"
        severity = "low"
        recommendation = "保持章节顺序与时间标记一致。"
        if current_rank != -1 and previous_rank != -1 and current_rank < previous_rank:
            ordering_status = "violated"
            severity = "high"
            recommendation = "补充倒叙标记，或调整事件顺序。"
        constraints.append(
            TimelineConstraint(
                project_id=project_id,
                chapter_number=chapter_number,
                constraint_type="ordering",
                severity=severity,  # type: ignore[arg-type]
                related_node_id=timeline_node.id,
                description="时间标记不能无说明地逆序跳回",
                evidence=[previous_node.time_marker, timeline_node.time_marker],
                status=ordering_status,  # type: ignore[arg-type]
                recommendation=recommendation,
            )
        )

    if timeline_node.previous_location and timeline_node.location and timeline_node.previous_location != timeline_node.location:
        travel_status = "clear" if location_transitions else "violated"
        constraints.append(
            TimelineConstraint(
                project_id=project_id,
                chapter_number=chapter_number,
                constraint_type="travel",
                severity="high" if travel_status == "violated" else "medium",
                related_node_id=timeline_node.id,
                related_character_id=primary_character_id,
                description="地点切换必须存在明确转场链路",
                evidence=[timeline_node.previous_location, timeline_node.location],
                status=travel_status,  # type: ignore[arg-type]
                recommendation="补充赶路、传送、撤离或队伍移动过程。",
            )
        )

    if context_pack.chapter_plan and context_pack.chapter_plan.pov_character_id:
        pov_id = context_pack.chapter_plan.pov_character_id
        status = "clear" if pov_id in timeline_node.participants else "violated"
        constraints.append(
            TimelineConstraint(
                project_id=project_id,
                chapter_number=chapter_number,
                constraint_type="presence",
                severity="high" if status == "violated" else "low",
                related_node_id=timeline_node.id,
                related_character_id=pov_id,
                description="POV 角色必须进入本章主事件链",
                evidence=[pov_id, ",".join(timeline_node.participants) or "无参与者"],
                status=status,  # type: ignore[arg-type]
                recommendation="让 POV 角色进入动作、观察或内心活动主线。",
            )
        )

    if context_pack.open_retcon_patches:
        constraints.append(
            TimelineConstraint(
                project_id=project_id,
                chapter_number=chapter_number,
                constraint_type="patch",
                severity="high",
                related_node_id=timeline_node.id,
                description="开放补丁尚未消化，继续推进时间线存在风险",
                evidence=[item.id for item in context_pack.open_retcon_patches[:4]],
                status="warning",
                recommendation="优先完成补丁重规划和 rerun，再继续扩写。",
            )
        )
    return constraints
