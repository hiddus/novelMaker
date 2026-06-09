from app.core.config import get_settings
from app.schemas.domain import ContextPack
from app.services.memory import retrieve_long_term_memories
from app.services.store import store


def _approx_chars_from_tokens(token_budget: int) -> int:
    return max(80, token_budget * 4)


def _truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else f"{text[: max_chars - 3]}..."


def _join_or_default(items: list[str], default: str) -> str:
    return "\n".join(items) if items else default


def _keyword_candidates(*parts: str) -> list[str]:
    tokens: list[str] = []
    separators = ["，", "。", "；", "：", "、", "\n", " ", ",", ":", ";", "(", ")", "（", "）", "-", "_"]
    for part in parts:
        normalized = part
        for separator in separators:
            normalized = normalized.replace(separator, "|")
        for token in normalized.split("|"):
            candidate = token.strip()
            if len(candidate) >= 2:
                tokens.append(candidate)
    return list(dict.fromkeys(tokens))


def _overlap_score(text: str, keywords: list[str]) -> float:
    return float(sum(1 for keyword in keywords if keyword and keyword in text))


def _score_event(chapter_number: int, summary: str, item_chapter: int, keywords: list[str]) -> float:
    recency = max(0.0, 8 - abs(chapter_number - item_chapter))
    return recency + _overlap_score(summary, keywords) * 2.0


def _score_state(chapter_number: int, summary: str, item_chapter: int, keywords: list[str]) -> float:
    recency = max(0.0, 7 - abs(chapter_number - item_chapter))
    return recency + _overlap_score(summary, keywords) * 2.3


def _score_snapshot(chapter_number: int, summary: str, item_chapter: int, keywords: list[str]) -> float:
    recency = max(0.0, 6 - abs(chapter_number - item_chapter))
    return recency + _overlap_score(summary, keywords) * 1.8


def _score_patch(chapter_number: int, summary: str, target_chapter: int, keywords: list[str]) -> float:
    proximity = 10.0 if target_chapter <= chapter_number else max(0.0, 6 - abs(chapter_number - target_chapter))
    return proximity + _overlap_score(summary, keywords) * 2.5


def _score_character(summary: str, keywords: list[str], role: str) -> float:
    role_bonus = 2.0 if role in {"protagonist", "lead", "support"} else 0.5
    return role_bonus + _overlap_score(summary, keywords) * 2.0


def _dynamic_token_budget(
    total_budget_tokens: int,
    output_reserve_tokens: int,
    has_plan: bool,
    patch_count: int,
) -> dict[str, int]:
    input_budget = max(2000, total_budget_tokens - output_reserve_tokens)
    story_share = 0.30 if has_plan else 0.35
    event_share = 0.20
    state_share = 0.16
    snapshot_share = 0.12
    memory_share = 0.14
    patch_share = 0.14 if patch_count else 0.03
    if not patch_count:
        event_share += 0.03
        state_share += 0.02
        snapshot_share += 0.01

    return {
        "total_budget_tokens": total_budget_tokens,
        "reserved_for_output_tokens": output_reserve_tokens,
        "input_budget_tokens": input_budget,
        "story_bible_tokens": int(input_budget * story_share),
        "event_tokens": int(input_budget * event_share),
        "character_state_tokens": int(input_budget * state_share),
        "snapshot_tokens": int(input_budget * snapshot_share),
        "memory_tokens": int(input_budget * memory_share),
        "patch_tokens": int(input_budget * patch_share),
    }


def build_context_pack(project_id: str, chapter_number: int) -> ContextPack:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("project not found")
    settings = get_settings()

    story_bible = store.get_story_bible(project_id)
    characters = store.list_characters(project_id)
    events = store.list_events(project_id)
    chapter_plans = store.list_chapter_plans(project_id)
    character_states = store.list_character_states(project_id)
    snapshots = store.list_snapshots(project_id)
    retcon_patches = store.list_retcon_patches(project_id)
    hook_records = store.list_hook_records(project_id)
    chapter_plan = next(
        (plan for plan in chapter_plans if plan.chapter_number == chapter_number),
        None,
    )

    open_retcon_patches = [item for item in retcon_patches if item.status == "open"]
    open_hooks = [
        item
        for item in hook_records
        if item.created_in_chapter <= chapter_number and item.status in {"open", "active"}
    ]
    plan_text = " ".join(
        item
        for item in [
            chapter_plan.goal if chapter_plan else "",
            chapter_plan.conflict if chapter_plan else "",
            chapter_plan.hook if chapter_plan else "",
            project.premise,
            " ".join(story_bible.author_intent[:3]),
            " ".join(story_bible.core_setting[:4]),
            " ".join(item.content for item in open_hooks[:4]),
        ]
        if item
    )
    query_keywords = _keyword_candidates(plan_text)
    memory_hits, memory_trace = retrieve_long_term_memories(
        project_id,
        chapter_number=chapter_number,
        query_text=plan_text,
        limit=settings.context_max_memories,
    )

    scored_events = sorted(
        (
            (
                _score_event(chapter_number, item.summary, item.chapter_number, query_keywords),
                item,
            )
            for item in events
            if item.chapter_number <= chapter_number
        ),
        key=lambda pair: (pair[0], pair[1].chapter_number),
        reverse=True,
    )
    recent_events = [item for _, item in scored_events[: settings.context_max_events]]

    scored_states = sorted(
        (
            (
                _score_state(
                    chapter_number,
                    " ".join(
                        filter(
                            None,
                            [item.location, item.emotion, item.goal, item.relationship_signal, item.progress_signal, item.note],
                        )
                    ),
                    item.chapter_number,
                    query_keywords,
                ),
                item,
            )
            for item in character_states
            if item.chapter_number <= chapter_number
        ),
        key=lambda pair: (pair[0], pair[1].chapter_number),
        reverse=True,
    )
    recent_character_states = [item for _, item in scored_states[: settings.context_max_character_states]]

    scored_snapshots = sorted(
        (
            (
                _score_snapshot(chapter_number, item.summary + item.chapter_title, item.chapter_number, query_keywords),
                item,
            )
            for item in snapshots
            if item.chapter_number <= chapter_number
        ),
        key=lambda pair: (pair[0], pair[1].chapter_number),
        reverse=True,
    )
    recent_snapshots = [item for _, item in scored_snapshots[: settings.context_max_snapshots]]

    scored_patches = sorted(
        (
            (
                _score_patch(
                    chapter_number,
                    f"{item.reason} {' '.join(str(num) for num in item.removed_chapter_numbers)}",
                    item.target_chapter_number,
                    query_keywords,
                ),
                item,
            )
            for item in open_retcon_patches
        ),
        key=lambda pair: (pair[0], pair[1].target_chapter_number),
        reverse=True,
    )
    open_retcon_patches = [item for _, item in scored_patches[: settings.context_max_patches]]

    scored_characters = sorted(
        (
            (
                _score_character(
                    " ".join([item.name, item.role, item.realm, " ".join(item.personality), item.core_motivation]),
                    query_keywords,
                    item.role,
                ),
                item,
            )
            for item in characters
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    active_characters = [item for _, item in scored_characters[: settings.context_max_characters]]

    hard_constraints = story_bible.world_rules + story_bible.forbidden_rules
    retrieval_priorities = [
        "章节规划命中优先",
        "高相关历史事件优先",
        "高相关角色状态优先",
        "开放伏笔优先",
        "开放补丁与回滚影响优先",
        "章节号邻近度作为次级排序",
    ]
    token_budget = _dynamic_token_budget(
        settings.context_total_budget_tokens,
        settings.context_output_reserve_tokens,
        has_plan=chapter_plan is not None,
        patch_count=len(open_retcon_patches),
    )

    story_bible_summary = _truncate(
        _join_or_default(
            [
                f"世界规则：{'；'.join(story_bible.world_rules[:5])}" if story_bible.world_rules else "",
                f"力量体系：{' -> '.join(story_bible.power_system[:6])}" if story_bible.power_system else "",
                f"禁忌：{'；'.join(story_bible.forbidden_rules[:5])}" if story_bible.forbidden_rules else "",
                f"作者意图：{'；'.join(story_bible.author_intent[:5])}" if story_bible.author_intent else "",
            ],
            "暂无 Story Bible 摘要。",
        ),
        _approx_chars_from_tokens(token_budget["story_bible_tokens"]),
    )
    event_summary = _truncate(
        _join_or_default(
            [f"第{item.chapter_number}章：{item.summary}" for item in recent_events],
            "暂无最近事件。",
        ),
        _approx_chars_from_tokens(token_budget["event_tokens"]),
    )
    character_state_summary = _truncate(
        _join_or_default(
            [
                f"角色{item.character_id} 在第{item.chapter_number}章：地点={item.location or '未知'}，情绪={item.emotion or '未知'}，目标={item.goal or '未知'}，推进={item.progress_signal or '无'}"
                for item in recent_character_states
            ],
            "暂无最近角色状态。",
        ),
        _approx_chars_from_tokens(token_budget["character_state_tokens"]),
    )
    snapshot_summary = _truncate(
        _join_or_default(
            [f"第{item.chapter_number}章快照：{item.summary}" for item in recent_snapshots],
            "暂无最近快照。",
        ),
        _approx_chars_from_tokens(token_budget["snapshot_tokens"]),
    )
    patch_summary = _truncate(
        _join_or_default(
            [
                f"{item.id}：目标章节={item.target_chapter_number}，状态={item.status}，建议重跑起点={item.recommended_rerun_from}"
                for item in open_retcon_patches
            ],
            "暂无开放补丁。",
        ),
        _approx_chars_from_tokens(token_budget["patch_tokens"]),
    )
    hook_summary = _truncate(
        _join_or_default(
            [
                f"{item.status} / 第{item.created_in_chapter}章 / {item.content}"
                for item in open_hooks[:6]
            ],
            "暂无开放伏笔。",
        ),
        _approx_chars_from_tokens(max(240, token_budget["patch_tokens"] // 2)),
    )
    memory_summary = _truncate(
        _join_or_default(
            [
                f"第{item.chapter_number}章 / {item.source_type} / score={item.retrieval_score} / {item.content}"
                for item in memory_hits
            ],
            "暂无长期记忆命中。",
        ),
        _approx_chars_from_tokens(token_budget["memory_tokens"]),
    )
    event_diagnostics = [
        f"第{item.chapter_number}章 / score={round(score, 1)} / {item.summary}"
        for score, item in scored_events[: settings.context_max_events]
    ]
    state_diagnostics = [
        f"第{item.chapter_number}章 / score={round(score, 1)} / char={item.character_id} / {item.goal or item.note}"
        for score, item in scored_states[: settings.context_max_character_states]
    ]
    snapshot_diagnostics = [
        f"第{item.chapter_number}章 / score={round(score, 1)} / {item.chapter_title}"
        for score, item in scored_snapshots[: settings.context_max_snapshots]
    ]
    patch_diagnostics = [
        f"{item.id} / score={round(score, 1)} / target={item.target_chapter_number} / {item.reason}"
        for score, item in scored_patches[: settings.context_max_patches]
    ]
    character_diagnostics = [
        f"{item.name} / score={round(score, 1)} / role={item.role}"
        for score, item in scored_characters[: settings.context_max_characters]
    ]
    hook_diagnostics = [
        f"{item.status} / 第{item.created_in_chapter}章 / {item.content}"
        for item in open_hooks[:6]
    ]
    memory_diagnostics = [
        f"第{item.chapter_number}章 / {item.source_type} / {item.memory_type} / score={item.retrieval_score} / terms={','.join(item.matched_terms[:4]) or '无'}"
        for item in memory_hits
    ]
    selection_reasoning = [
        f"query_terms={', '.join(query_keywords[:12]) or '无'}",
        f"selected_events={len(recent_events)} / selected_states={len(recent_character_states)} / selected_snapshots={len(recent_snapshots)} / selected_hooks={len(open_hooks)} / selected_patches={len(open_retcon_patches)}",
        f"snapshot_summary={snapshot_summary}",
        f"memory_trace={memory_trace.id}",
    ]
    context_summary = (
        f"第 {chapter_number} 章上下文包："
        f"从 {len(events)} 条事件中选出 {len(recent_events)} 条，"
        f"从 {len(character_states)} 条状态中选出 {len(recent_character_states)} 条，"
        f"从 {len(snapshots)} 个快照中选出 {len(recent_snapshots)} 个，"
        f"长期记忆命中 {len(memory_hits)} 条，"
        f"开放伏笔 {len(open_hooks)} 条，"
        f"开放补丁 {len(open_retcon_patches)} 个。"
    )

    return ContextPack(
        project_id=project_id,
        chapter_number=chapter_number,
        story_bible=story_bible,
        recent_events=recent_events,
        active_characters=active_characters,
        long_term_memories=memory_hits,
        open_hooks=open_hooks,
        recent_character_states=recent_character_states,
        recent_snapshots=recent_snapshots,
        open_retcon_patches=open_retcon_patches,
        chapter_plan=chapter_plan,
        hard_constraints=hard_constraints,
        retrieval_priorities=retrieval_priorities,
        context_summary=context_summary,
        story_bible_summary=story_bible_summary,
        event_summary=event_summary,
        character_state_summary=character_state_summary,
        patch_summary=patch_summary,
        memory_summary=memory_summary,
        token_budget=token_budget,
        retrieval_diagnostics={
            "events": event_diagnostics,
            "character_states": state_diagnostics,
            "snapshots": snapshot_diagnostics,
            "long_term_memory": memory_diagnostics,
            "open_hooks": hook_diagnostics,
            "patches": patch_diagnostics,
            "characters": character_diagnostics,
        },
        selection_reasoning=selection_reasoning + [f"hook_summary={hook_summary}", f"memory_summary={memory_summary}"],
    )
