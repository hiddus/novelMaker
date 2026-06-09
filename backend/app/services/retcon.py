from __future__ import annotations

from app.schemas.domain import ChapterPlan, RetconPatch


def build_retcon_patch(
    project_id: str,
    target_chapter_number: int,
    reason: str,
    removed_chapter_numbers: list[int],
    invalidated_version_ids: list[str],
    removed_plan_ids: list[str],
    removed_plan_hooks: list[str],
    removed_events_count: int,
    removed_states_count: int,
    removed_snapshots_count: int,
) -> RetconPatch:
    affected_chapter_numbers = sorted(set(removed_chapter_numbers))
    requires_recompute_hooks = sorted({item for item in removed_plan_hooks if item})
    requires_state_rollback = any(
        value > 0 for value in (removed_events_count, removed_states_count, removed_snapshots_count)
    )

    impact_summary: list[str] = []
    if affected_chapter_numbers:
        impact_summary.append(
            f"受影响章节共 {len(affected_chapter_numbers)} 章：{', '.join(str(item) for item in affected_chapter_numbers[:8])}"
        )
    if removed_plan_ids:
        impact_summary.append(f"失效章节规划 {len(removed_plan_ids)} 个，需要重新生成后续章节 plan。")
    if requires_recompute_hooks:
        impact_summary.append(
            f"需重算钩子 {len(requires_recompute_hooks)} 个：{'；'.join(requires_recompute_hooks[:5])}"
        )
    if requires_state_rollback:
        impact_summary.append("本次回滚已影响事件/角色状态/快照，需要按新正文重新抽取并写回状态层。")
    if not impact_summary:
        impact_summary.append("本次补丁主要影响未来章节，需要重新评估后续规划。")

    recommended_rerun_from = (
        min(affected_chapter_numbers) if affected_chapter_numbers else target_chapter_number + 1
    )

    return RetconPatch(
        project_id=project_id,
        target_chapter_number=target_chapter_number,
        reason=reason,
        affected_chapter_numbers=affected_chapter_numbers,
        invalidated_version_ids=invalidated_version_ids,
        invalidated_plan_ids=removed_plan_ids,
        removed_chapter_numbers=removed_chapter_numbers,
        requires_recompute_hooks=requires_recompute_hooks,
        requires_state_rollback=requires_state_rollback,
        impact_summary=impact_summary,
        recommended_rerun_from=recommended_rerun_from,
    )


def summarize_invalidated_plans(plans: list[ChapterPlan], target_chapter_number: int) -> tuple[list[str], list[str]]:
    invalidated_plan_ids: list[str] = []
    hook_candidates: list[str] = []
    for plan in plans:
        if plan.chapter_number > target_chapter_number:
            invalidated_plan_ids.append(plan.id)
            if plan.hook:
                hook_candidates.append(plan.hook)
    return invalidated_plan_ids, hook_candidates
