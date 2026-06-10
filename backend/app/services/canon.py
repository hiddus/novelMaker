from app.schemas.domain import (
    ChapterDraft,
    CharacterRelationshipEdge,
    CharacterState,
    ContextPack,
    Event,
    ExtractedUpdate,
    Snapshot,
    TimelineConstraint,
    TimelineNode,
    VersionRecord,
)
from app.services.graph_state import build_timeline_constraints, evolve_relationship_edges
from app.services.hooks import build_hook_updates, materialize_hook_updates
from app.services.store import store


LOCATION_KEYWORDS = ["北域", "南域", "中州", "宗门", "学院", "秘境", "城", "山脉", "皇城"]
EMOTION_KEYWORDS = ["愤怒", "平静", "恐惧", "兴奋", "悲伤", "坚定", "紧张", "狂喜"]
GOAL_KEYWORDS = ["复仇", "突破", "逃离", "结盟", "调查", "夺宝", "闭关", "飞升"]
RELATIONSHIP_KEYWORDS = ["师徒", "盟友", "敌人", "结盟", "背叛", "兄弟", "恋人"]
RELATION_TYPE_MAP = {
    "师徒": "mentor",
    "盟友": "ally",
    "敌人": "enemy",
    "结盟": "ally",
    "背叛": "rival",
    "兄弟": "family",
    "恋人": "lover",
}
PROGRESS_PATTERNS = [
    ("突破", "境界推进"),
    ("闭关", "修炼推进"),
    ("结盟", "关系推进"),
    ("调查", "线索推进"),
    ("夺宝", "资源推进"),
    ("飞升", "大目标推进"),
]


def _extract_keywords(content: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in content]


def _pick_primary_character(context_pack: ContextPack) -> str | None:
    if context_pack.chapter_plan and context_pack.chapter_plan.pov_character_id:
        return context_pack.chapter_plan.pov_character_id
    if context_pack.active_characters:
        return context_pack.active_characters[0].id
    return None


def _latest_previous_state(
    project_id: str,
    chapter_number: int,
    primary_character_id: str | None,
) -> CharacterState | None:
    states = [
        item
        for item in store.list_character_states(project_id)
        if item.chapter_number < chapter_number
    ]
    if primary_character_id is not None:
        character_states = [
            item for item in states if item.character_id == primary_character_id
        ]
        if character_states:
            return max(character_states, key=lambda item: item.chapter_number)
    if states:
        return max(states, key=lambda item: item.chapter_number)
    return None


def _infer_location_transitions(
    previous_state: CharacterState | None,
    locations: list[str],
) -> list[str]:
    previous_location = previous_state.location if previous_state is not None else None
    transitions: list[str] = []
    if previous_location and locations and previous_location != locations[0]:
        transitions.append(f"{previous_location} -> {locations[0]}")
    return transitions


def _infer_goal_progress(content: str, goals: list[str]) -> list[str]:
    signals = [label for keyword, label in PROGRESS_PATTERNS if keyword in content]
    for goal in goals:
        signals.append(f"围绕目标“{goal}”发生推进")
    return list(dict.fromkeys(signals))


def _timeline_marker(chapter: ChapterDraft) -> str:
    for marker in ["当夜", "次日", "翌日", "三日后", "七日后", "半月后", "一月后"]:
        if marker in chapter.content:
            return marker
    return f"第{chapter.chapter_number}章"


def _infer_relationship_edges(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    relationship_signals: list[str],
    primary_character_id: str | None,
) -> list[CharacterRelationshipEdge]:
    if primary_character_id is None or not relationship_signals:
        return []
    peer_ids = [item.id for item in context_pack.active_characters if item.id != primary_character_id][:2]
    edges: list[CharacterRelationshipEdge] = []
    for index, signal in enumerate(relationship_signals[:2]):
        if index >= len(peer_ids):
            break
        relation_type = RELATION_TYPE_MAP.get(signal, "unknown")
        edges.append(
            CharacterRelationshipEdge(
                project_id=project_id,
                chapter_number=chapter.chapter_number,
                source_character_id=primary_character_id,
                target_character_id=peer_ids[index],
                relation_type=relation_type,  # type: ignore[arg-type]
                direction="mutual" if relation_type in {"ally", "family", "lover"} else "forward",
                intensity=1.2 if signal in {"背叛", "敌人"} else 0.8,
                evidence=f"章节《{chapter.title}》命中关系信号：{signal}",
                note=f"根据第 {chapter.chapter_number} 章自动生成的人际关系边。",
            )
        )
    return edges


def _build_timeline_node(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    created_event: Event,
    locations: list[str],
    primary_character_id: str | None,
) -> TimelineNode:
    previous_nodes = store.list_timeline_nodes(project_id)
    previous_state = _latest_previous_state(
        project_id,
        chapter.chapter_number,
        primary_character_id,
    )
    return TimelineNode(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        event_id=created_event.id,
        label=chapter.summary or chapter.title,
        location=locations[0] if locations else created_event.location,
        previous_location=previous_state.location if previous_state else None,
        participants=[primary_character_id] if primary_character_id else [],
        time_marker=_timeline_marker(chapter),
        predecessor_node_ids=[previous_nodes[-1].id] if previous_nodes else [],
        note=f"由《{chapter.title}》写回生成的时间线节点。",
    )


def extract_chapter_update(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
) -> tuple[
    ExtractedUpdate,
    Event,
    CharacterState | None,
    list[CharacterRelationshipEdge],
    TimelineNode,
    list[TimelineConstraint],
]:
    primary_character_id = _pick_primary_character(context_pack)
    previous_state = _latest_previous_state(
        project_id,
        chapter.chapter_number,
        primary_character_id,
    )
    locations = _extract_keywords(chapter.content, LOCATION_KEYWORDS)
    emotions = _extract_keywords(chapter.content, EMOTION_KEYWORDS)
    goals = _extract_keywords(chapter.content, GOAL_KEYWORDS)
    relationship_signals = _extract_keywords(chapter.content, RELATIONSHIP_KEYWORDS)
    location_transitions = _infer_location_transitions(previous_state, locations)
    goal_progress_signals = _infer_goal_progress(chapter.content, goals)

    created_event = Event(
        chapter_number=chapter.chapter_number,
        summary=chapter.summary or chapter.title,
        event_type="chapter_result" if not relationship_signals else "relationship_shift",
        actor_ids=[primary_character_id] if primary_character_id else [],
        location=locations[0] if locations else None,
    )

    created_state: CharacterState | None = None
    if primary_character_id is not None:
        created_state = CharacterState(
            character_id=primary_character_id,
            chapter_number=chapter.chapter_number,
            location=locations[0] if locations else None,
            emotion=emotions[0] if emotions else "推进中",
            goal=goals[0] if goals else (context_pack.chapter_plan.goal if context_pack.chapter_plan else None),
            relationship_signal=relationship_signals[0] if relationship_signals else None,
            progress_signal=goal_progress_signals[0] if goal_progress_signals else None,
            note=f"根据《{chapter.title}》自动生成的章节状态快照。",
        )
    relationship_edges = _infer_relationship_edges(
        project_id,
        chapter,
        context_pack,
        relationship_signals,
        primary_character_id,
    )
    timeline_node = _build_timeline_node(
        project_id,
        chapter,
        context_pack,
        created_event,
        locations,
        primary_character_id,
    )
    timeline_constraints = build_timeline_constraints(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        context_pack,
        timeline_node=timeline_node,
        location_transitions=location_transitions,
        primary_character_id=primary_character_id,
    )

    extracted_update = ExtractedUpdate(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        event_ids=[created_event.id],
        character_state_ids=[created_state.id] if created_state else [],
        timeline_advance=f"推进到第 {chapter.chapter_number} 章完成后状态",
        hook_changes=[context_pack.chapter_plan.hook] if context_pack.chapter_plan else [],
        locations=locations,
        emotions=emotions,
        goals=goals,
        relationship_signals=relationship_signals,
        relationship_edge_ids=[item.id for item in relationship_edges],
        location_transitions=location_transitions,
        goal_progress_signals=goal_progress_signals,
        timeline_node_ids=[timeline_node.id],
        timeline_constraints=[item.description for item in timeline_constraints],
        summary=f"已从第 {chapter.chapter_number} 章抽取事件、地点、情绪、关系边、时间线节点与角色状态。",
    )
    extracted_update, _hook_records, _hook_changes = build_hook_updates(project_id, chapter, context_pack, extracted_update)
    return extracted_update, created_event, created_state, relationship_edges, timeline_node, timeline_constraints


def apply_extracted_update_to_canon(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
    created_event: Event,
    created_state: CharacterState | None,
    relationship_edges: list[CharacterRelationshipEdge],
    timeline_node: TimelineNode,
    timeline_constraints: list[TimelineConstraint],
) -> tuple[ExtractedUpdate, Snapshot, VersionRecord]:
    # Canon writeback must be idempotent for the same chapter. If a previous
    # attempt partially succeeded, drop the old chapter projection first and rebuild it.
    character_state_ids: list[str] = list(extracted_update.character_state_ids)
    if created_state is not None:
        character_state_ids = [created_state.id]
    relationship_edges = evolve_relationship_edges(
        project_id,
        chapter.chapter_number,
        relationship_edges,
        existing_edges=[
            item
            for item in store.list_relationship_edges(project_id)
            if item.chapter_number != chapter.chapter_number
        ],
    )
    extracted_update = extracted_update.model_copy(update={"character_state_ids": character_state_ids})
    hook_records, hook_changes = materialize_hook_updates(project_id, chapter, context_pack, extracted_update)
    extracted_update, snapshot, version = store.apply_chapter_canon_projection(
        project_id,
        chapter,
        [item.id for item in context_pack.active_characters],
        extracted_update,
        created_event,
        created_state,
        relationship_edges,
        timeline_node,
        timeline_constraints,
        hook_records,
        hook_changes,
    )
    return extracted_update, snapshot, version


def apply_chapter_to_canon(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
) -> tuple[ExtractedUpdate, Snapshot, VersionRecord]:
    extracted_update, created_event, created_state, relationship_edges, timeline_node, timeline_constraints = extract_chapter_update(
        project_id,
        chapter,
        context_pack,
    )
    return apply_extracted_update_to_canon(
        project_id,
        chapter,
        context_pack,
        extracted_update,
        created_event,
        created_state,
        relationship_edges,
        timeline_node,
        timeline_constraints,
    )
