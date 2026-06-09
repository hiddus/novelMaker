from __future__ import annotations

from app.schemas.domain import (
    ChapterDraft,
    ContextPack,
    ExtractedUpdate,
    ReaderCouncilReport,
    ReaderFeedback,
)


def _clip(score: float) -> float:
    return round(max(0.0, min(10.0, score)), 2)


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

    if len(chapter.content) >= 900:
        engagement += 1.0
    elif len(chapter.content) < 400:
        engagement -= 1.0
        concerns.append("章节篇幅偏短，快节奏读者会觉得不够过瘾。")
        suggestions.append("增加更高密度的冲突推进和结果反馈。")

    if extracted_update.location_transitions or extracted_update.goal_progress_signals:
        engagement += 1.2
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

    if extracted_update.emotions:
        engagement += min(1.5, len(extracted_update.emotions) * 0.5)
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
    ]
    overall_score = _clip(sum(item.engagement_score for item in persona_feedbacks) / len(persona_feedbacks))
    chase_score = _clip(sum(item.hook_expectation_score for item in persona_feedbacks) / len(persona_feedbacks))
    payoff_score = _clip(sum(item.payoff_score for item in persona_feedbacks) / len(persona_feedbacks))
    pace_score = _clip((overall_score + chase_score) / 2)

    highlights = [item for feedback in persona_feedbacks for item in feedback.likes][:6]
    concerns = [item for feedback in persona_feedbacks for item in feedback.concerns][:6]
    suggestions = [item for feedback in persona_feedbacks for item in feedback.suggestions][:6]

    status = "strong" if overall_score >= 6.5 and chase_score >= 6.0 else "weak"
    summary = (
        "Reader Council 认为本章具备稳定追读价值。"
        if status == "strong"
        else "Reader Council 认为本章追读驱动力不足，建议强化爽点、节奏或情绪回报。"
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
