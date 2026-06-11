from app.schemas.domain import (
    ChapterDraft,
    ContinuityReport,
    ContextPack,
    ExtractedUpdate,
    ReaderCouncilReport,
    ReviewReport,
)
from app.services.webnovel_knowledge import (
    QUALITY_STANDARDS,
    爽点库,
    节奏模板,
    钩子库,
    追读要素,
)


def _detect_爽点(content: str) -> tuple[list[str], float]:
    """检测章节中的爽点"""
    爽点列表 = []
    爽点分数 = 0.0
    
    # 爽点关键词检测
    爽点关键词 = {
        "升级爽": ["突破", "晋升", "实力提升", "境界提升", "修为提升"],
        "打脸爽": ["反击", "碾压", "嘲讽", "轻视", "质疑", "侮辱"],
        "逆袭爽": ["反转", "逆袭", "绝境", "劣势", "压制"],
        "收获爽": ["获得", "收获", "宝物", "资源", "传承"],
        "认可爽": ["认可", "尊重", "信任", "地位提升"],
    }
    
    for 爽点类型, 关键词列表 in 爽点关键词.items():
        for 关键词 in 关键词列表:
            if 关键词 in content:
                爽点列表.append(爽点类型)
                回报强度 = 爽点库.get(爽点类型, {}).get("回报强度", "中")
                爽点分数 += 2.0 if 回报强度 == "高" else 1.0
                break
    
    return 爽点列表, 爽点分数


def _detect_转折点(content: str) -> tuple[int, float]:
    """检测章节中的转折点"""
    转折关键词 = ["突然", "然而", "但是", "可是", "不料", "意外", "转折", "变化", "危机", "突破"]
    转折数量 = sum(1 for 关键词 in 转折关键词 if 关键词 in content)
    转折分数 = min(5.0, 转折数量 * 1.5)
    return 转折数量, 转折分数


def _detect_钩子强度(content: str) -> tuple[str, float]:
    """检测章节结尾的钩子强度"""
    钩子关键词 = {
        "悬念钩": ["悬念", "谜团", "线索", "疑问"],
        "反转钩": ["反转", "陷阱", "伏笔", "阴谋"],
        "威胁钩": ["威胁", "危机", "危险", "逼近"],
        "期待钩": ["期待", "目标", "即将", "下一步"],
    }
    
    钩子类型 = "无钩子"
    钩子分数 = 0.0
    
    for 类型, 关键词列表 in 钩子关键词.items():
        for 关键词 in 关键词列表:
            if 关键词 in content[-500:]:  # 只检查最后500字符
                钩子类型 = 类型
                强度 = 钩子库.get(类型, {}).get("强度", "中")
                钩子分数 += 3.0 if 强度 == "高" else 2.0
                break
    
    return 钩子类型, 钩子分数


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

    # 基础评分
    logic_score = 6.0
    continuity_score = 6.0
    character_score = 6.0
    hook_score = 6.0
    
    # 新增网文特有评分维度
    爽点密度_score = 5.0
    节奏控制_score = 5.0
    追读意愿_score = 5.0
    代入感_score = 5.0

    # 爽点检测
    爽点列表, 爽点分数 = _detect_爽点(chapter.content)
    if 爽点分数 >= 2.0:
        爽点密度_score += 爽点分数
        findings.append(f"检测到爽点：{', '.join(爽点列表)}")
    else:
        findings.append("爽点密度不足，缺少明确的爽点回报。")
        suggestions.append("增加升级爽、打脸爽、逆袭爽或收获爽等明确爽点。")
        爽点密度_score -= 1.5

    # 转折点检测
    转折数量, 转折分数 = _detect_转折点(chapter.content)
    if 转折数量 >= 3:
        节奏控制_score += 转折分数
        findings.append(f"节奏密度良好，检测到{转折数量}个转折点。")
    else:
        findings.append(f"节奏密度不足，仅检测到{转折数量}个转折点。")
        suggestions.append("增加至少3个明确转折点，保持网文节奏密度。")
        节奏控制_score -= 1.5

    # 钩子强度检测
    钩子类型, 钩子分数 = _detect_钩子强度(chapter.content)
    if 钩子分数 >= 2.0:
        hook_score += 钩子分数
        追读意愿_score += 钩子分数
        findings.append(f"结尾钩子强度良好，检测到{钩子类型}。")
    else:
        findings.append("结尾钩子强度不足，缺少明确的追读钩子。")
        suggestions.append("在结尾增加悬念钩、反转钩、威胁钩或期待钩等明确钩子。")
        hook_score -= 2.0
        追读意愿_score -= 2.0

    # 基础逻辑检查
    if len(chapter.content) >= 600:
        logic_score += 1.5
    else:
        findings.append("章节正文偏短，逻辑铺垫可能不足。")
        suggestions.append("补足起因、推进和结果三个阶段。")
        logic_score -= 1.5

    # 章节规划检查
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

    # 场景检查
    if not extracted_update.location_transitions and extracted_update.locations:
        continuity_score += 0.5
    if not extracted_update.locations:
        findings.append("未识别到明确地点信息。")
        suggestions.append("增加场景锚点，明确人物所处地点。")
        continuity_score -= 1.0
        代入感_score -= 0.5

    # 角色关系检查
    if not extracted_update.relationship_signals:
        findings.append("人物关系变化不明显。")
        suggestions.append("增加角色互动，显式呈现盟友、敌意或背叛线索。")
        character_score -= 1.0
        代入感_score -= 0.5
    else:
        character_score += min(1.5, len(extracted_update.relationship_signals) * 0.5)
        代入感_score += min(1.0, len(extracted_update.relationship_signals) * 0.3)

    # 目标推进检查
    if not extracted_update.goal_progress_signals:
        findings.append("未识别到明确的目标推进。")
        suggestions.append("让章节结果对主角当前目标形成具体推进或受挫。")
        logic_score -= 0.5
        追读意愿_score -= 0.5
    else:
        logic_score += 1.0
        追读意愿_score += 0.5

    # 钩子变化检查
    if not extracted_update.hook_changes:
        findings.append("章节结尾钩子不足。")
        suggestions.append("在结尾增加悬念、反转或下一章明确目标。")
        hook_score -= 2.0
    else:
        hook_score += min(2.0, len(extracted_update.hook_changes))

    # 硬约束检查
    if context_pack.hard_constraints:
        forbidden_hits = [item for item in context_pack.hard_constraints if item and item in chapter.content]
        if forbidden_hits:
            findings.append("正文可能直接触碰硬规则，需要人工确认。")
            suggestions.append("检查是否违背世界规则或禁忌条款。")
            continuity_score -= 1.0

    # Continuity Board检查
    if continuity_report.issues:
        findings.append(continuity_report.summary)
        for issue in continuity_report.issues:
            findings.append(f"[{issue.judge}/{issue.severity}] {issue.title}")
            if issue.recommendation:
                suggestions.append(issue.recommendation)
            if issue.severity == "high":
                continuity_score -= 1.5
                character_score -= 0.5 if issue.judge == "character" else 0.0
                代入感_score -= 0.5
            elif issue.severity == "medium":
                continuity_score -= 0.8
            else:
                continuity_score -= 0.3

    # Reader Council检查
    if reader_council_report.status == "weak":
        findings.append(reader_council_report.summary)
        hook_score -= 1.0
        logic_score -= 0.5
        追读意愿_score -= 1.5
    if reader_council_report.concerns:
        for concern in reader_council_report.concerns[:3]:
            findings.append(f"[reader] {concern}")
    for suggestion in reader_council_report.suggestions[:3]:
        suggestions.append(suggestion)

    # 计算总分（包含网文特有维度）
    overall_score = round(
        (logic_score + continuity_score + character_score + hook_score + 爽点密度_score + 节奏控制_score + 追读意愿_score + 代入感_score) / 8,
        2,
    )
    
    # 确定状态
    status = (
        "approved"
        if overall_score >= 6.5
        and len(findings) <= 6
        and continuity_report.status == "clear"
        and reader_council_report.status == "strong"
        and 爽点密度_score >= 6.0
        and 节奏控制_score >= 6.0
        and 追读意愿_score >= 6.0
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
