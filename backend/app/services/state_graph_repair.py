from __future__ import annotations

from collections import Counter

from app.schemas.domain import StateGraphDiagnostic, StateGraphRecoveryPlan, StateGraphRepairSuggestion
from app.services.store import store


def _chapter_window(chapter_number: int | None, latest_chapter: int) -> tuple[int | None, int | None]:
    if chapter_number is None or chapter_number <= 0:
        return None, None
    end_chapter = max(chapter_number, latest_chapter)
    return chapter_number, end_chapter


def _safe_start_chapter(chapter_number: int | None, category: str) -> int | None:
    if chapter_number is None or chapter_number <= 0:
        return None
    if category in {"reference", "relationship", "timeline"}:
        return max(1, chapter_number - 1)
    return chapter_number


def _manual_suggestion(diagnostic: StateGraphDiagnostic, detail: str) -> StateGraphRepairSuggestion:
    return StateGraphRepairSuggestion(
        title="需要人工核查状态图谱",
        detail=detail,
        severity=diagnostic.severity,
        recommended_action="manual_review",
        scheduler_mode="manual",
        target_entity_type=diagnostic.entity_type,
        target_entity_id=diagnostic.entity_id,
        can_create_scheduler_task=False,
    )


def build_state_graph_repair_suggestion(
    project_id: str,
    diagnostic: StateGraphDiagnostic,
) -> StateGraphRepairSuggestion:
    latest_chapter = max((item.chapter_number for item in store.list_chapters(project_id)), default=0)
    start_chapter, end_chapter = _chapter_window(diagnostic.chapter_number, latest_chapter)

    if start_chapter is None or end_chapter is None:
        return _manual_suggestion(
            diagnostic,
            "该问题未定位到明确章节，建议先人工检查 current revision 与图谱写回链。",
        )

    if diagnostic.category in {"projection", "revision"}:
        safe_start = _safe_start_chapter(start_chapter, diagnostic.category)
        return StateGraphRepairSuggestion(
            title=f"建议从第 {safe_start} 章发起 recovery，重建 current projection",
            detail=(
                "重跑会重新生成 review、continuity、reader，以及 approved 章节所需的 "
                "snapshot / version / timeline node 写回。"
            ),
            severity=diagnostic.severity,
            recommended_action="rerun_projection",
            scheduler_mode="recovery",
            start_chapter=safe_start,
            end_chapter=end_chapter,
            target_entity_type=diagnostic.entity_type,
            target_entity_id=diagnostic.entity_id,
            can_create_scheduler_task=True,
        )

    if diagnostic.category in {"reference", "relationship", "timeline"}:
        safe_start = _safe_start_chapter(start_chapter, diagnostic.category)
        return StateGraphRepairSuggestion(
            title=f"建议从第 {safe_start} 章发起 recovery，重建后续图谱演化链",
            detail=(
                "该类断链通常会污染前后章节之间的 snapshot、version、relationship 或 timeline current head，"
                "建议至少从问题章节前一章开始重跑到当前末章，确保引用和 current 链尾重新收敛。"
            ),
            severity=diagnostic.severity,
            recommended_action="rerun_window",
            scheduler_mode="recovery",
            start_chapter=safe_start,
            end_chapter=end_chapter,
            target_entity_type=diagnostic.entity_type,
            target_entity_id=diagnostic.entity_id,
            can_create_scheduler_task=True,
        )

    return _manual_suggestion(
        diagnostic,
        "当前规则无法自动推导安全恢复窗口，建议人工检查后再创建 recovery 任务。",
    )


def attach_state_graph_repair_suggestions(
    project_id: str,
    diagnostics: list[StateGraphDiagnostic],
) -> list[StateGraphDiagnostic]:
    return [
        item.model_copy(
            update={
                "repair_suggestion": build_state_graph_repair_suggestion(project_id, item),
            }
        )
        for item in diagnostics
    ]


def build_state_graph_recovery_plan(
    diagnostics: list[StateGraphDiagnostic],
) -> StateGraphRecoveryPlan | None:
    if not diagnostics:
        return None

    actionable = [
        item.repair_suggestion
        for item in diagnostics
        if item.repair_suggestion is not None
        and item.repair_suggestion.can_create_scheduler_task
        and item.repair_suggestion.scheduler_mode == "recovery"
        and item.repair_suggestion.start_chapter is not None
        and item.repair_suggestion.end_chapter is not None
    ]
    critical_actionable = [item for item in actionable if item.severity == "critical"]
    chosen = critical_actionable or actionable
    category_counter = Counter(item.category for item in diagnostics)
    focus_categories = [category for category, _count in category_counter.most_common(3)]
    summary_lines = [
        f"ch{item.chapter_number or 'n/a'} / {item.category} / {item.summary}"
        for item in diagnostics[:5]
    ]
    issue_count = len(diagnostics)
    critical_issue_count = sum(1 for item in diagnostics if item.severity == "critical")

    if not chosen:
        return StateGraphRecoveryPlan(
            title="状态图谱问题需要人工核查",
            detail="当前问题无法自动推导安全 recovery 窗口，建议先人工检查断链章节和当前图谱链路。",
            severity="critical" if critical_issue_count else "warning",
            recommended_action="manual_review",
            scheduler_mode="manual",
            can_create_scheduler_task=False,
            issue_count=issue_count,
            critical_issue_count=critical_issue_count,
            summary_lines=summary_lines,
            focus_categories=focus_categories,
        )

    start_chapter = min(item.start_chapter for item in chosen if item.start_chapter is not None)
    end_chapter = max(item.end_chapter for item in chosen if item.end_chapter is not None)
    recommended_action = (
        "rerun_window"
        if any(item.recommended_action == "rerun_window" for item in chosen)
        else "rerun_projection"
    )
    severity = "critical" if critical_issue_count else "warning"
    return StateGraphRecoveryPlan(
        title=f"建议执行状态图谱批量 recovery：第 {start_chapter} 章 -> 第 {end_chapter} 章",
        detail=(
            f"当前共有 {issue_count} 条状态图谱问题，其中 {critical_issue_count} 条为 critical。"
            "建议按统一窗口重跑，先整体修复 projection / relationship / timeline / hook 链，再继续写作。"
        ),
        severity=severity,  # type: ignore[arg-type]
        recommended_action=recommended_action,  # type: ignore[arg-type]
        scheduler_mode="recovery",
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        can_create_scheduler_task=True,
        issue_count=issue_count,
        critical_issue_count=critical_issue_count,
        summary_lines=summary_lines,
        focus_categories=focus_categories,
    )
