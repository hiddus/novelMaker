from app.schemas.domain import ChapterDraft, CharacterState, ContextPack, Event, ExtractedUpdate, Snapshot, VersionRecord
from app.services.hooks import build_hook_updates, materialize_hook_updates
from app.services.store import store


LOCATION_KEYWORDS = ["北域", "南域", "中州", "宗门", "学院", "秘境", "城", "山脉", "皇城"]
EMOTION_KEYWORDS = ["愤怒", "平静", "恐惧", "兴奋", "悲伤", "坚定", "紧张", "狂喜"]
GOAL_KEYWORDS = ["复仇", "突破", "逃离", "结盟", "调查", "夺宝", "闭关", "飞升"]
RELATIONSHIP_KEYWORDS = ["师徒", "盟友", "敌人", "结盟", "背叛", "兄弟", "恋人"]
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


def _infer_location_transitions(context_pack: ContextPack, locations: list[str]) -> list[str]:
    previous_location = None
    if context_pack.recent_character_states:
        previous_location = context_pack.recent_character_states[-1].location
    transitions: list[str] = []
    if previous_location and locations and previous_location != locations[0]:
        transitions.append(f"{previous_location} -> {locations[0]}")
    return transitions


def _infer_goal_progress(content: str, goals: list[str]) -> list[str]:
    signals = [label for keyword, label in PROGRESS_PATTERNS if keyword in content]
    for goal in goals:
        signals.append(f"围绕目标“{goal}”发生推进")
    return list(dict.fromkeys(signals))


def extract_chapter_update(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
) -> tuple[ExtractedUpdate, Event, CharacterState | None]:
    primary_character_id = _pick_primary_character(context_pack)
    locations = _extract_keywords(chapter.content, LOCATION_KEYWORDS)
    emotions = _extract_keywords(chapter.content, EMOTION_KEYWORDS)
    goals = _extract_keywords(chapter.content, GOAL_KEYWORDS)
    relationship_signals = _extract_keywords(chapter.content, RELATIONSHIP_KEYWORDS)
    location_transitions = _infer_location_transitions(context_pack, locations)
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
        location_transitions=location_transitions,
        goal_progress_signals=goal_progress_signals,
        summary=f"已从第 {chapter.chapter_number} 章抽取事件、地点、情绪、目标推进与角色状态。",
    )
    extracted_update, _hook_records, _hook_changes = build_hook_updates(project_id, chapter, context_pack, extracted_update)
    return extracted_update, created_event, created_state


def apply_extracted_update_to_canon(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
    created_event: Event,
    created_state: CharacterState | None,
) -> tuple[ExtractedUpdate, Snapshot, VersionRecord]:
    store.add_event(project_id, created_event)

    character_state_ids: list[str] = list(extracted_update.character_state_ids)
    if created_state is not None:
        store.add_character_state(project_id, created_state)
        character_state_ids = [created_state.id]
    extracted_update = extracted_update.model_copy(update={"character_state_ids": character_state_ids})
    store.add_extracted_update(project_id, extracted_update)

    hook_records, hook_changes = materialize_hook_updates(project_id, chapter, context_pack, extracted_update)
    for record in hook_records:
        store.save_hook_record(project_id, record)
    for change in hook_changes:
        store.add_hook_state_change(project_id, change)

    snapshot = Snapshot(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        chapter_title=chapter.title,
        active_character_ids=[item.id for item in context_pack.active_characters],
        active_hook_ids=[
            item.id
            for item in store.list_hook_records(project_id)
            if item.status in {"open", "active"}
        ],
        recent_event_ids=[created_event.id],
        summary=(
            f"第 {chapter.chapter_number} 章快照，包含 1 条事件、{len(character_state_ids)} 条角色状态，"
            f"以及 {len(extracted_update.new_hooks) + len(extracted_update.active_hooks)} 条活跃伏笔。"
        ),
    )
    store.add_snapshot(project_id, snapshot)

    version = VersionRecord(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        snapshot_id=snapshot.id,
        extracted_update_id=extracted_update.id,
        version_label=f"chapter-{chapter.chapter_number}-v1",
        change_summary=f"生成《{chapter.title}》并写回 canon。",
    )
    store.add_version(project_id, version)

    return extracted_update, snapshot, version


def apply_chapter_to_canon(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
) -> tuple[ExtractedUpdate, Snapshot, VersionRecord]:
    extracted_update, created_event, created_state = extract_chapter_update(project_id, chapter, context_pack)
    return apply_extracted_update_to_canon(
        project_id,
        chapter,
        context_pack,
        extracted_update,
        created_event,
        created_state,
    )
