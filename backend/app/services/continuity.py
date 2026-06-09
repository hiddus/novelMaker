from __future__ import annotations

from app.schemas.domain import (
    ChapterDraft,
    Character,
    ContinuityIssue,
    ContinuityReport,
    ContextPack,
    ExtractedUpdate,
)


def _keyword_candidates(text: str) -> list[str]:
    tokens: list[str] = []
    for separator in ["，", "。", "；", "：", "、", "\n", " ", ",", ":", ";", "(", ")", "（", "）", "-", "_", "/"]:
        text = text.replace(separator, "|")
    for token in text.split("|"):
        token = token.strip()
        if len(token) >= 2:
            tokens.append(token)
    return list(dict.fromkeys(tokens))


def _push_issue(
    issues: list[ContinuityIssue],
    judge: str,
    severity: str,
    title: str,
    detail: str,
    evidence: list[str],
    recommendation: str,
) -> None:
    issues.append(
        ContinuityIssue(
            judge=judge,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            title=title,
            detail=detail,
            evidence=[item for item in evidence if item],
            recommendation=recommendation,
        )
    )


def _active_character_names(characters: list[Character]) -> list[str]:
    return [item.name for item in characters if item.status == "active"]


def _power_jump_issue(
    chapter: ChapterDraft,
    characters: list[Character],
    power_system: list[str],
) -> list[ContinuityIssue]:
    issues: list[ContinuityIssue] = []
    if not power_system:
        return issues

    for character in characters:
        if not character.name or not character.realm or character.realm not in power_system:
            continue
        current_index = power_system.index(character.realm)
        for higher_index in range(current_index + 3, len(power_system)):
            target_realm = power_system[higher_index]
            if character.name in chapter.content and target_realm in chapter.content:
                _push_issue(
                    issues,
                    "power",
                    "high",
                    "战力跨度异常",
                    f"{character.name} 当前设定境界为 {character.realm}，正文却直接出现更高阶的 {target_realm}。",
                    [character.name, character.realm, target_realm],
                    "补充越级手段、外力来源，或回退到合理的战力提升幅度。",
                )
                break
    return issues


def run_continuity_board(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ContinuityReport:
    issues: list[ContinuityIssue] = []
    story_bible = context_pack.story_bible
    chapter_text = f"{chapter.title}\n{chapter.content}\n{chapter.summary}"

    forbidden_hits = [item for item in story_bible.forbidden_rules if item and item in chapter_text]
    if forbidden_hits:
        _push_issue(
            issues,
            "lore",
            "high",
            "触碰禁忌设定",
            "正文直接命中了 Story Bible 中的禁忌规则，需要人工确认是否为有意突破设定。",
            forbidden_hits[:5],
            "检查世界规则是否被打破，必要时回写设定或改写正文。",
        )

    core_keywords = _keyword_candidates(" ".join(story_bible.core_setting[:4] + story_bible.world_rules[:4]))
    lore_hits = [item for item in core_keywords if item in chapter_text]
    if core_keywords and not lore_hits:
        _push_issue(
            issues,
            "lore",
            "low",
            "世界观锚点偏弱",
            "本章没有明显承接核心设定或世界规则，容易写成脱离主设定的通用剧情。",
            story_bible.core_setting[:3],
            "补充场景规则、势力信息或世界代价，让章节重新挂回 Story Bible。",
        )

    active_names = _active_character_names(context_pack.active_characters[:4])
    present_names = [name for name in active_names if name in chapter_text]
    if active_names and not present_names:
        _push_issue(
            issues,
            "character",
            "medium",
            "活跃角色缺席",
            "上下文判定为活跃的关键角色没有在正文中出现，角色推进可能断层。",
            active_names,
            "确认是否应当切换 POV，或补足关键角色的在场与互动。",
        )

    if context_pack.chapter_plan and context_pack.chapter_plan.pov_character_id:
        pov_character = next(
            (item for item in context_pack.active_characters if item.id == context_pack.chapter_plan.pov_character_id),
            None,
        )
        if pov_character and pov_character.name not in chapter_text:
            _push_issue(
                issues,
                "character",
                "high",
                "POV 角色未落地",
                "章节规划指定了 POV 角色，但正文几乎没有体现该角色。",
                [pov_character.name],
                "让 POV 角色进入场景、行动或内心活动，避免计划与正文断裂。",
            )

    if not extracted_update.relationship_signals:
        _push_issue(
            issues,
            "character",
            "low",
            "人物关系推进不足",
            "本章没有明显的关系变化信号，长期人物弧线可能停滞。",
            [],
            "增加协作、冲突、背叛、试探等互动结果。",
        )

    if context_pack.open_retcon_patches:
        open_patch_ids = [item.id for item in context_pack.open_retcon_patches[:4]]
        _push_issue(
            issues,
            "timeline",
            "high",
            "存在未消化补丁",
            "当前章节仍处于开放补丁影响范围内，时间线和状态链可能尚未完全收敛。",
            open_patch_ids,
            "优先完成补丁重规划与 rerun，再继续扩写后续章节。",
        )

    if not extracted_update.timeline_advance:
        _push_issue(
            issues,
            "timeline",
            "medium",
            "时间推进不明确",
            "本章没有形成明确的时间推进描述，连载长篇中容易造成前后章顺序感变弱。",
            [],
            "补充事件结果、阶段节点或时间流逝的明确信号。",
        )

    previous_location = next(
        (item.location for item in context_pack.recent_character_states if item.location),
        None,
    )
    current_location = extracted_update.locations[0] if extracted_update.locations else None
    if previous_location and current_location and previous_location != current_location and not extracted_update.location_transitions:
        _push_issue(
            issues,
            "timeline",
            "medium",
            "地点切换缺少过渡",
            "角色状态记录与本章地点出现变化，但抽取不到明确转场信息。",
            [previous_location, current_location],
            "补充赶路、传送、撤离或场景切换的过程描述。",
        )

    issues.extend(_power_jump_issue(chapter, context_pack.active_characters, story_bible.power_system))

    judges_triggered = list(dict.fromkeys(issue.judge for issue in issues))
    high_count = sum(1 for item in issues if item.severity == "high")
    medium_count = sum(1 for item in issues if item.severity == "medium")
    if high_count:
        status = "review_required"
        risk = "high"
    elif medium_count >= 2:
        status = "review_required"
        risk = "medium"
    elif issues:
        status = "clear"
        risk = "medium"
    else:
        status = "clear"
        risk = "low"

    summary = (
        "Continuity Board 未发现明显一致性风险。"
        if not issues
        else f"Continuity Board 发现 {len(issues)} 个问题，涉及 {'/'.join(judges_triggered)}。"
    )

    return ContinuityReport(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        status=status,
        overall_risk=risk,  # type: ignore[arg-type]
        judges_triggered=judges_triggered,
        summary=summary,
        issues=issues,
    )
