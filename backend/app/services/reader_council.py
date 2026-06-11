from __future__ import annotations

from app.schemas.domain import (
    ChapterDraft,
    ContextPack,
    ExtractedUpdate,
    ReaderCouncilReport,
    ReaderFeedback,
)
from app.services.webnovel_knowledge import 爽点库, 节奏模板


def _clip(score: float) -> float:
    return round(max(0.0, min(10.0, score)), 2)


def _detect_爽点(content: str) -> tuple[list[str], float]:
    """检测文本中的爽点类型和强度"""
    detected = []
    score = 0.0
    for 爽点类型, 爽点信息 in 爽点库.items():
        for 触发条件 in 爽点信息.get("触发条件", []):
            if 触发条件 in content:
                detected.append(爽点类型)
                score += 爽点信息.get("回报强度", "中") == "高" and 2.0 or 1.0
        for 典型表现 in 爽点信息.get("典型表现", []):
            if 典型表现 in content:
                score += 1.0
    return detected, score


def _core_reader_feedback(
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderFeedback:
    engagement = 5.5
    hook = 5.0
    payoff = 5.0
    likes: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    if context_pack.chapter_plan and context_pack.chapter_plan.goal in chapter.content:
        engagement += 1.0
        payoff += 0.8
        likes.append("章节目标与正文推进对齐，主线阅读体验稳定。")
    else:
        concerns.append("主线目标回应偏弱，追读读者可能感觉这章推进不足。")
        suggestions.append("让本章结果更明确地作用于当前主线。")

    if extracted_update.goal_progress_signals:
        payoff += 1.2
        likes.append("主角目标出现阶段性推进。")
    else:
        concerns.append("没有形成明确的阶段性收获或受挫。")
        suggestions.append("补充阶段结果，让读者感到这一章有实际进展。")

    if extracted_update.hook_changes:
        hook += min(2.0, len(extracted_update.hook_changes) * 0.8)
        likes.append("章节结尾存在继续追读的钩子。")
    else:
        hook -= 1.8
        concerns.append("章节结尾钩子偏弱，追更意愿可能下滑。")
        suggestions.append("结尾增加悬念、威胁升级或下一步行动目标。")

    # 新增：爽点检测
    爽点列表, 爽点分数 = _detect_爽点(chapter.content)
    if 爽点分数 >= 3.0:
        payoff += 1.0
        likes.append(f"检测到爽点：{', '.join(爽点列表)}，提升阅读满足感。")
    elif 爽点分数 > 0:
        payoff += 0.5
        suggestions.append("可增强爽点强度，提升读者满足感。")
    else:
        concerns.append("缺少明确爽点，读者满足感可能不足。")
        suggestions.append("增加升级、打脸、逆袭等爽点设计。")

    return ReaderFeedback(
        persona="core_reader",
        engagement_score=_clip(engagement),
        hook_expectation_score=_clip(hook),
        payoff_score=_clip(payoff),
        summary="核心连载读者更关心主线推进、阶段收获与追更钩子。",
        likes=likes,
        concerns=concerns,
        suggestions=suggestions,
    )


def _fast_paced_reader_feedback(
    chapter: ChapterDraft,
    _context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderFeedback:
    engagement = 5.0
    hook = 5.0
    payoff = 5.0
    likes: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    content_length = len(chapter.content)
    if content_length >= 2000:
        engagement += 1.0
        likes.append("章节篇幅充足，内容密度高。")
    elif content_length >= 900:
        engagement += 0.5
    elif content_length < 600:
        engagement -= 1.5
        concerns.append("章节篇幅偏短，快节奏读者会觉得不够过瘾。")
        suggestions.append("增加更高密度的冲突推进和结果反馈。")

    action_count = len(extracted_update.location_transitions or []) + len(extracted_update.goal_progress_signals or [])
    if action_count >= 3:
        engagement += 1.5
        payoff += 0.8
        likes.append("章节动作推进密集，阅读体感爽快。")
    elif action_count >= 2:
        engagement += 0.8
        likes.append("章节动作推进明显，阅读体感不拖。")
    else:
        concerns.append("章节动态事件偏少，可能显得偏静态。")
        suggestions.append("加入更直接的行动、转场或对抗。")

    if extracted_update.hook_changes:
        hook += 1.5
        payoff += 0.5
        likes.append("结尾形成了继续点下一章的驱动力。")
    else:
        hook -= 1.5
        concerns.append("缺少足够强的悬念或反转。")
        suggestions.append("把结尾设计成信息揭示、反杀前夜或危机升级。")

    return ReaderFeedback(
        persona="fast_paced_reader",
        engagement_score=_clip(engagement),
        hook_expectation_score=_clip(hook),
        payoff_score=_clip(payoff),
        summary="快节奏读者更敏感于推进密度、冲突爆点和追更冲动。",
        likes=likes,
        concerns=concerns,
        suggestions=suggestions,
    )


def _emotion_reader_feedback(
    chapter: ChapterDraft,
    _context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderFeedback:
    engagement = 5.0
    hook = 4.8
    payoff = 5.2
    likes: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    emotions = extracted_update.emotions or []
    emotion_variety = len(set(emotions))
    
    if emotion_variety >= 3:
        engagement += 1.5
        payoff += 0.5
        likes.append("章节情绪层次丰富，代入感强。")
    elif emotions:
        engagement += min(1.0, len(emotions) * 0.4)
        likes.append("章节有较明确的情绪表达。")
    else:
        concerns.append("情绪层偏弱，代入感不足。")
        suggestions.append("增加角色反应、心理落差和情绪结果。")

    if extracted_update.relationship_signals:
        payoff += min(1.5, len(extracted_update.relationship_signals) * 0.5)
        likes.append("人物关系有可感知的变化。")
    else:
        concerns.append("人物互动结果不够鲜明。")
        suggestions.append("让角色之间形成更明确的信任、试探或冲突变化。")

    if extracted_update.hook_changes:
        hook += 1.0
    else:
        hook -= 1.0

    return ReaderFeedback(
        persona="emotion_reader",
        engagement_score=_clip(engagement),
        hook_expectation_score=_clip(hook),
        payoff_score=_clip(payoff),
        summary="情绪向读者更看重代入感、人物关系变化和情绪余味。",
        likes=likes,
        concerns=concerns,
        suggestions=suggestions,
    )


def _detail_reader_feedback(
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderFeedback:
    """细节控读者：关注设定一致性和细节丰富度"""
    engagement = 5.0
    hook = 5.0
    payoff = 5.0
    likes: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    # 检查设定一致性
    if context_pack.story_bible_summary:
        bible_keywords = ["境界", "修炼", "法宝", "宗门", "家族", "规则"]
        mentioned_count = sum(1 for kw in bible_keywords if kw in chapter.content)
        if mentioned_count >= 2:
            engagement += 1.0
            likes.append("章节提及设定元素，世界感强。")
        else:
            suggestions.append("适当提及世界设定元素，增强沉浸感。")

    # 检查细节描写
    detail_keywords = ["眼神", "动作", "语气", "环境", "气息", "光芒"]
    detail_count = sum(1 for kw in detail_keywords if kw in chapter.content)
    if detail_count >= 3:
        engagement += 0.8
        payoff += 0.5
        likes.append("细节描写丰富，画面感强。")
    elif detail_count >= 1:
        engagement += 0.3
    else:
        concerns.append("细节描写偏少，画面感较弱。")
        suggestions.append("增加场景、动作、表情等细节描写。")

    # 检查逻辑合理性
    if extracted_update.goal_progress_signals and extracted_update.location_transitions:
        payoff += 0.5
        likes.append("情节推进逻辑清晰。")

    return ReaderFeedback(
        persona="detail_reader",
        engagement_score=_clip(engagement),
        hook_expectation_score=_clip(hook),
        payoff_score=_clip(payoff),
        summary="细节控读者更关注设定一致性、细节丰富度和逻辑合理性。",
        likes=likes,
        concerns=concerns,
        suggestions=suggestions,
    )


def _payoff_seeking_reader_feedback(
    chapter: ChapterDraft,
    _context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderFeedback:
    """回报导向读者：关注爽点密度和价值获取"""
    engagement = 5.0
    hook = 5.0
    payoff = 5.0
    likes: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    爽点列表, 爽点分数 = _detect_爽点(chapter.content)
    
    if 爽点分数 >= 5.0:
        payoff += 2.0
        engagement += 1.5
        likes.append(f"爽点密集且强度高：{', '.join(爽点列表)}，阅读体验爽快！")
    elif 爽点分数 >= 3.0:
        payoff += 1.0
        engagement += 0.5
        likes.append(f"存在爽点：{', '.join(爽点列表)}，满足感尚可。")
    elif 爽点分数 > 0:
        suggestions.append("爽点强度不足，可增强冲突和回报。")
    else:
        payoff -= 1.5
        concerns.append("缺少明确的价值回报，读者容易弃书。")
        suggestions.append("增加升级、打脸、逆袭、收获等明确爽点。")

    # 检查资源获取
    resource_keywords = ["获得", "得到", "突破", "升级", "领悟", "传承"]
    resource_count = sum(1 for kw in resource_keywords if kw in chapter.content)
    if resource_count >= 2:
        payoff += 1.0
        likes.append("存在多重价值获取，回报感强。")

    return ReaderFeedback(
        persona="payoff_seeking_reader",
        engagement_score=_clip(engagement),
        hook_expectation_score=_clip(hook),
        payoff_score=_clip(payoff),
        summary="回报导向读者最关注爽点密度和价值获取，追求明确的成就感。",
        likes=likes,
        concerns=concerns,
        suggestions=suggestions,
    )


def run_reader_council(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> ReaderCouncilReport:
    persona_feedbacks = [
        _core_reader_feedback(chapter, context_pack, extracted_update),
        _fast_paced_reader_feedback(chapter, context_pack, extracted_update),
        _emotion_reader_feedback(chapter, context_pack, extracted_update),
        _detail_reader_feedback(chapter, context_pack, extracted_update),
        _payoff_seeking_reader_feedback(chapter, context_pack, extracted_update),
    ]
    overall_score = _clip(sum(item.engagement_score for item in persona_feedbacks) / len(persona_feedbacks))
    chase_score = _clip(sum(item.hook_expectation_score for item in persona_feedbacks) / len(persona_feedbacks))
    payoff_score = _clip(sum(item.payoff_score for item in persona_feedbacks) / len(persona_feedbacks))
    pace_score = _clip((overall_score + chase_score) / 2)

    highlights = [item for feedback in persona_feedbacks for item in feedback.likes][:8]
    concerns = [item for feedback in persona_feedbacks for item in feedback.concerns][:8]
    suggestions = [item for feedback in persona_feedbacks for item in feedback.suggestions][:8]

    status = "strong" if overall_score >= 6.5 and chase_score >= 6.0 and payoff_score >= 6.0 else "weak"
    summary = (
        "Reader Council 认为本章具备稳定追读价值，爽点、节奏和情绪回报均衡。"
        if status == "strong"
        else "Reader Council 认为本章追读驱动力不足，建议强化爽点密度、节奏把控或情绪回报。"
    )

    return ReaderCouncilReport(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        status=status,
        overall_score=overall_score,
        chase_score=chase_score,
        payoff_score=payoff_score,
        pace_score=pace_score,
        summary=summary,
        highlights=highlights,
        concerns=concerns,
        suggestions=suggestions,
        persona_feedbacks=persona_feedbacks,
    )
