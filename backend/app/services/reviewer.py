from app.schemas.domain import (
    ChapterDraft,
    ContinuityReport,
    ContextPack,
    ExtractedUpdate,
    ReaderCouncilReport,
    ReviewReport,
)


def review_chapter(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
    continuity_report: ContinuityReport,
    reader_council_report: ReaderCouncilReport,
) -> ReviewReport:
    findings: list[str] = []
    suggestions: list[str] = []

    logic_score = 6.0
    continuity_score = 6.0
    character_score = 6.0
    hook_score = 6.0

    if len(chapter.content) >= 600:
        logic_score += 1.5
    else:
        findings.append("章节正文偏短，逻辑铺垫可能不足。")
        suggestions.append("补足起因、推进和结果三个阶段。")
        logic_score -= 1.5

    if context_pack.chapter_plan:
        if context_pack.chapter_plan.goal and context_pack.chapter_plan.goal not in chapter.content:
            findings.append("章节目标在正文中体现不足。")
            suggestions.append("加强对章节目标的直接回应。")
            continuity_score -= 1.0
        if context_pack.chapter_plan.conflict and context_pack.chapter_plan.conflict not in chapter.content:
            findings.append("章节冲突与规划不够贴合。")
            suggestions.append("补强与章节冲突相关的对抗或阻力。")
            continuity_score -= 1.0
        if context_pack.chapter_plan.hook and context_pack.chapter_plan.hook in extracted_update.hook_changes:
            hook_score += 1.0

    if not extracted_update.location_transitions and extracted_update.locations:
        continuity_score += 0.5
    if not extracted_update.locations:
        findings.append("未识别到明确地点信息。")
        suggestions.append("增加场景锚点，明确人物所处地点。")
        continuity_score -= 1.0

    if not extracted_update.relationship_signals:
        findings.append("人物关系变化不明显。")
        suggestions.append("增加角色互动，显式呈现盟友、敌意或背叛线索。")
        character_score -= 1.0
    else:
        character_score += min(1.5, len(extracted_update.relationship_signals) * 0.5)

    if not extracted_update.goal_progress_signals:
        findings.append("未识别到明确的目标推进。")
        suggestions.append("让章节结果对主角当前目标形成具体推进或受挫。")
        logic_score -= 0.5
    else:
        logic_score += 1.0

    if not extracted_update.hook_changes:
        findings.append("章节结尾钩子不足。")
        suggestions.append("在结尾增加悬念、反转或下一章明确目标。")
        hook_score -= 2.0
    else:
        hook_score += min(2.0, len(extracted_update.hook_changes))

    if context_pack.hard_constraints:
        forbidden_hits = [item for item in context_pack.hard_constraints if item and item in chapter.content]
        if forbidden_hits:
            findings.append("正文可能直接触碰硬规则，需要人工确认。")
            suggestions.append("检查是否违背世界规则或禁忌条款。")
            continuity_score -= 1.0

    if continuity_report.issues:
        findings.append(continuity_report.summary)
        for issue in continuity_report.issues:
            findings.append(f"[{issue.judge}/{issue.severity}] {issue.title}")
            if issue.recommendation:
                suggestions.append(issue.recommendation)
            if issue.severity == "high":
                continuity_score -= 1.5
                character_score -= 0.5 if issue.judge == "character" else 0.0
            elif issue.severity == "medium":
                continuity_score -= 0.8
            else:
                continuity_score -= 0.3

    if reader_council_report.status == "weak":
        findings.append(reader_council_report.summary)
        hook_score -= 1.0
        logic_score -= 0.5
    if reader_council_report.concerns:
        for concern in reader_council_report.concerns[:3]:
            findings.append(f"[reader] {concern}")
    for suggestion in reader_council_report.suggestions[:3]:
        suggestions.append(suggestion)

    overall_score = round((logic_score + continuity_score + character_score + hook_score) / 4, 2)
    status = (
        "approved"
        if overall_score >= 6.5
        and len(findings) <= 6
        and continuity_report.status == "clear"
        and reader_council_report.status == "strong"
        else "review_required"
    )
    decision_reason = "评审通过，可进入 canon。" if status == "approved" else "评审未通过，建议人工复核或重写。"

    return ReviewReport(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        chapter_id=chapter.id,
        status=status,
        logic_score=round(max(0.0, min(10.0, logic_score)), 2),
        continuity_score=round(max(0.0, min(10.0, continuity_score)), 2),
        character_score=round(max(0.0, min(10.0, character_score)), 2),
        hook_score=round(max(0.0, min(10.0, hook_score)), 2),
        overall_score=overall_score,
        decision_reason=decision_reason,
        findings=findings,
        rewrite_suggestions=suggestions,
        continuity_report_id=continuity_report.id,
        reader_council_report_id=reader_council_report.id,
    )
