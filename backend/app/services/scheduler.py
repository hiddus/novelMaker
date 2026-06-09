from datetime import UTC, datetime

from app.schemas.domain import (
    BatchWriteResult,
    GovernanceDecision,
    Project,
    ReplanPatchRequest,
    SchedulerTask,
    SchedulerTaskCreate,
    TaskRun,
    WriteChapterRequest,
)
from app.services.governance import (
    emit_governance_event,
    evaluate_governance_after_chapter,
    evaluate_governance_before_step,
    load_governance_policy,
)
from app.services.pipeline import execute_patch_replan, execute_write
from app.services.store import store


def create_scheduler_task(project: Project, payload: SchedulerTaskCreate) -> SchedulerTask:
    policy = load_governance_policy(project.id)
    stage = "replanning" if payload.mode == "recovery" else "writing"
    next_chapter = payload.start_chapter
    if payload.mode == "recovery" and not payload.patch_id:
        raise ValueError("恢复任务必须提供 patch_id")
    if payload.mode == "recovery" and payload.patch_id:
        patch = next((item for item in store.list_retcon_patches(project.id) if item.id == payload.patch_id), None)
        if patch is None:
            raise ValueError("patch not found")
        next_chapter = patch.recommended_rerun_from
        if payload.end_chapter < next_chapter:
            raise ValueError("恢复任务的结束章节不能早于补丁建议重跑起点")
    task = SchedulerTask(
        project_id=project.id,
        start_chapter=payload.start_chapter,
        end_chapter=payload.end_chapter,
        next_chapter=next_chapter,
        tone=payload.tone,
        writer_mode=payload.writer_mode,
        max_retries=payload.max_retries,
        mode=payload.mode,
        stage=stage,  # type: ignore[arg-type]
        patch_id=payload.patch_id,
        governance_policy_id=policy.id,
        governance_cost_limit_usd=policy.max_total_estimated_cost_usd,
        stage_message="等待执行恢复重规划" if payload.mode == "recovery" else "等待执行章节生成",
    )
    return store.save_scheduler_task(project.id, task)


def _save_task_run(project_id: str, task_type: str, payload_summary: str, result_summary: str, status: str) -> None:
    store.save_task_run(
        project_id,
        TaskRun(
            project_id=project_id,
            task_type=task_type,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            payload_summary=payload_summary,
            result_summary=result_summary,
            completed_at=datetime.now(UTC),
        ),
    )


def _set_task_state(
    project_id: str,
    task: SchedulerTask,
    *,
    status: str | None = None,
    stage: str | None = None,
    stage_message: str | None = None,
    last_error: str | None = None,
) -> SchedulerTask:
    updated = task.model_copy(
        update={
            "status": status or task.status,
            "stage": stage or task.stage,
            "stage_message": stage_message if stage_message is not None else task.stage_message,
            "last_error": last_error if last_error is not None else task.last_error,
            "updated_at": datetime.now(UTC),
        }
    )
    return store.save_scheduler_task(project_id, updated)


def _apply_governance_decision(
    project: Project,
    task: SchedulerTask,
    decision: GovernanceDecision,
    *,
    default_stage: str | None = None,
) -> SchedulerTask:
    policy = load_governance_policy(project.id)
    summary = store.build_metrics_summary(project.id)
    event = emit_governance_event(project.id, task, policy, decision)
    status = task.status
    stage = task.stage
    last_error = task.last_error
    stage_message = decision.reason or task.stage_message

    if decision.action == "pause":
        status = "paused"
        stage = "awaiting_review" if decision.signal == "review" else "governance_blocked"
        last_error = decision.reason or task.last_error
    elif decision.action == "stop":
        status = "failed"
        stage = "governance_blocked"
        last_error = decision.reason or task.last_error
    elif default_stage is not None:
        stage = default_stage

    updated = task.model_copy(
        update={
            "status": status,
            "stage": stage,
            "stage_message": stage_message,
            "last_error": last_error,
            "governance_status": decision.status,
            "governance_reason": decision.reason,
            "governance_last_event_id": event.id,
            "governance_cost_used_usd": summary.total_estimated_cost_usd,
            "governance_cost_limit_usd": policy.max_total_estimated_cost_usd,
            "governance_policy_id": policy.id,
            "updated_at": datetime.now(UTC),
        }
    )
    return store.save_scheduler_task(project.id, updated)


def _process_recovery_stage(project: Project, task: SchedulerTask) -> SchedulerTask:
    if not task.patch_id:
        raise ValueError("恢复任务缺少 patch_id")

    patch = next((item for item in store.list_retcon_patches(project.id) if item.id == task.patch_id), None)
    if patch is None:
        raise ValueError("恢复补丁不存在")

    if task.stage == "replanning":
        result = execute_patch_replan(project, task.patch_id, ReplanPatchRequest(tone=task.tone))
        next_chapter = max(task.start_chapter, result.patch.recommended_rerun_from)
        stage_message = f"补丁 {task.patch_id} 已重规划，准备从第 {next_chapter} 章重跑"
        task = task.model_copy(
            update={
                "next_chapter": next_chapter,
                "stage": "rerunning",
                "stage_message": stage_message,
                "last_error": "",
                "updated_at": datetime.now(UTC),
            }
        )
        store.save_scheduler_task(project.id, task)
        _save_task_run(project.id, "rerun", f"恢复任务 {task.id} 自动重规划", stage_message, "completed")
        return task

    chapter_result = execute_write(
        project,
        WriteChapterRequest(
            chapter_number=task.next_chapter,
            tone=task.tone,
            writer_mode=task.writer_mode,
        ),
    )
    chapter_payload = chapter_result.get("chapter", {})
    chapter_status = chapter_payload.get("status") if isinstance(chapter_payload, dict) else None

    completed = task.completed_chapters + [task.next_chapter]
    next_chapter = task.next_chapter + 1
    progress_task = store.save_scheduler_task(
        project.id,
        task.model_copy(
            update={
                "completed_chapters": completed,
                "next_chapter": next_chapter,
                "retry_count": 0,
                "consecutive_failures": 0,
                "status": "running",
                "stage": "rerunning",
                "stage_message": f"第 {completed[-1]} 章已完成，准备治理检查",
                "last_error": "",
                "updated_at": datetime.now(UTC),
            }
        ),
    )
    _save_task_run(project.id, "rerun", f"恢复任务执行第 {completed[-1]} 章", progress_task.stage_message, "completed")
    policy, decision = evaluate_governance_after_chapter(project.id, progress_task, completed[-1])
    if chapter_status == "review_required" and decision.action == "continue":
        decision = decision.model_copy(
            update={
                "action": "pause",
                "status": "blocked",
                "signal": "review",
                "reason": f"第 {completed[-1]} 章待人工审核，恢复任务已暂停",
            }
        )
    if decision.action != "continue":
        return _apply_governance_decision(project, progress_task, decision)

    is_done = next_chapter > task.end_chapter
    updated = progress_task.model_copy(
        update={
            "status": "completed" if is_done else "running",
            "stage": "completed" if is_done else "rerunning",
            "stage_message": "恢复任务已完成" if is_done else f"继续重跑第 {next_chapter} 章",
            "last_error": "",
            "updated_at": datetime.now(UTC),
        }
    )
    store.save_scheduler_task(project.id, updated)
    if is_done:
        result_patch = patch.model_copy(update={"status": "rerun_completed"})
        store.save_retcon_patch(project.id, result_patch)
    _save_task_run(project.id, "rerun", f"恢复任务执行第 {completed[-1]} 章", updated.stage_message, "completed")
    return updated


def _process_write_stage(project: Project, task: SchedulerTask) -> SchedulerTask:
    result = execute_write(
        project,
        WriteChapterRequest(
            chapter_number=task.next_chapter,
            tone=task.tone,
            writer_mode=task.writer_mode,
        ),
    )
    chapter_payload = result.get("chapter", {})
    chapter_status = chapter_payload.get("status") if isinstance(chapter_payload, dict) else None
    completed = task.completed_chapters + [task.next_chapter]
    next_chapter = task.next_chapter + 1
    progress_task = store.save_scheduler_task(
        project.id,
        task.model_copy(
            update={
                "completed_chapters": completed,
                "next_chapter": next_chapter,
                "retry_count": 0,
                "consecutive_failures": 0,
                "status": "running",
                "stage": "writing",
                "stage_message": f"第 {completed[-1]} 章已完成，准备治理检查",
                "last_error": "",
                "updated_at": datetime.now(UTC),
            }
        ),
    )
    _save_task_run(project.id, "batch_write", f"调度器执行第 {completed[-1]} 章", progress_task.stage_message, "completed")
    policy, decision = evaluate_governance_after_chapter(project.id, progress_task, completed[-1])
    if chapter_status == "review_required" and decision.action == "continue":
        decision = decision.model_copy(
            update={
                "action": "pause",
                "status": "blocked",
                "signal": "review",
                "reason": f"第 {completed[-1]} 章待人工审核，任务已暂停",
            }
        )
    if decision.action != "continue":
        return _apply_governance_decision(project, progress_task, decision)

    is_done = next_chapter > task.end_chapter
    updated = progress_task.model_copy(
        update={
            "status": "completed" if is_done else "running",
            "stage": "completed" if is_done else "writing",
            "stage_message": "写作任务已完成" if is_done else f"继续生成第 {next_chapter} 章",
            "last_error": "",
            "updated_at": datetime.now(UTC),
        }
    )
    store.save_scheduler_task(project.id, updated)
    return updated


def process_scheduler_step(project: Project, task_id: str) -> SchedulerTask:
    task = store.get_scheduler_task(project.id, task_id)
    if task is None:
        raise ValueError("scheduler task not found")
    if task.status in {"completed", "failed"}:
        return task
    if task.status == "paused":
        return task

    if task.next_chapter > task.end_chapter:
        return _set_task_state(
            project.id,
            task,
            status="completed",
            stage="completed",
            stage_message="调度任务已完成",
            last_error="",
        )

    _, decision = evaluate_governance_before_step(project.id, task)
    task = _set_task_state(project.id, task, status="running")
    if decision.action != "continue":
        return _apply_governance_decision(project, task, decision)
    if decision.status != "clear":
        task = _apply_governance_decision(project, task, decision, default_stage=task.stage)

    try:
        if task.mode == "recovery":
            return _process_recovery_stage(project, task)
        return _process_write_stage(project, task)
    except Exception as exc:
        next_retry_count = task.retry_count + 1
        next_consecutive_failures = task.consecutive_failures + 1
        failed_status = "failed" if next_retry_count > task.max_retries else "running"
        failed_task = task.model_copy(
            update={
                "retry_count": next_retry_count,
                "consecutive_failures": next_consecutive_failures,
                "last_error": str(exc),
                "status": failed_status,
                "updated_at": datetime.now(UTC),
            }
        )
        store.save_scheduler_task(project.id, failed_task)
        _save_task_run(
            project.id,
            "rerun" if task.mode == "recovery" else "batch_write",
            f"调度器执行第 {task.next_chapter} 章",
            str(exc),
            "failed",
        )
        _, failure_decision = evaluate_governance_before_step(project.id, failed_task)
        if failure_decision.action != "continue":
            return _apply_governance_decision(project, failed_task, failure_decision)
        return failed_task


def run_scheduler_to_completion(project: Project, task_id: str) -> BatchWriteResult:
    task = store.get_scheduler_task(project.id, task_id)
    if task is None:
        raise ValueError("scheduler task not found")
    if task.status in {"completed", "failed"}:
        return BatchWriteResult(
            project_id=project.id,
            start_chapter=task.start_chapter,
            end_chapter=task.end_chapter,
            completed_chapters=task.completed_chapters,
            failed_chapter=task.next_chapter if task.status == "failed" else None,
            status="completed" if task.status == "completed" else "failed",
            message=f"调度任务状态：{task.status}",
        )

    if task.status == "paused":
        if task.stage == "governance_blocked":
            stage = "rerunning" if task.mode == "recovery" else "writing"
        else:
            stage = "rerunning" if task.mode == "recovery" and task.stage != "replanning" else task.stage
        task = _set_task_state(project.id, task, status="running", stage=stage, stage_message="任务已恢复执行", last_error="")
    elif task.status == "pending":
        task = _set_task_state(project.id, task, status="running", stage_message="任务已进入后台执行", last_error="")

    return BatchWriteResult(
        project_id=project.id,
        start_chapter=task.start_chapter,
        end_chapter=task.end_chapter,
        completed_chapters=task.completed_chapters,
        failed_chapter=None,
        status="running",
        message=f"调度任务已进入后台执行，当前状态：{task.status} / stage={task.stage}",
    )


def pause_scheduler_task(project: Project, task_id: str) -> SchedulerTask:
    task = store.get_scheduler_task(project.id, task_id)
    if task is None:
        raise ValueError("scheduler task not found")
    if task.status not in {"running", "pending"}:
        return task
    updated = _set_task_state(project.id, task, status="paused", stage_message="任务已手动暂停")
    return _apply_governance_decision(
        project,
        updated,
        GovernanceDecision(action="pause", status="warning", signal="manual", reason="任务被人工暂停"),
    )


def resume_scheduler_task(project: Project, task_id: str) -> SchedulerTask:
    task = store.get_scheduler_task(project.id, task_id)
    if task is None:
        raise ValueError("scheduler task not found")
    if task.status != "paused":
        return task
    if task.stage == "governance_blocked":
        next_stage = "rerunning" if task.mode == "recovery" else "writing"
    else:
        next_stage = "rerunning" if task.mode == "recovery" and task.stage == "awaiting_review" else task.stage
    updated = _set_task_state(project.id, task, status="running", stage=next_stage, stage_message="任务已恢复执行", last_error="")
    return _apply_governance_decision(
        project,
        updated,
        GovernanceDecision(action="continue", status="clear", signal="manual", reason="任务已人工恢复"),
        default_stage=next_stage,
    )


def retry_scheduler_task(project: Project, task_id: str) -> SchedulerTask:
    task = store.get_scheduler_task(project.id, task_id)
    if task is None:
        raise ValueError("scheduler task not found")
    if task.status != "failed":
        return task
    next_stage = "rerunning" if task.mode == "recovery" and task.stage != "replanning" else task.stage
    updated = store.save_scheduler_task(
        project.id,
        task.model_copy(
            update={
                "status": "running",
                "stage": next_stage,
                "retry_count": 0,
                "consecutive_failures": 0,
                "last_error": "",
                "stage_message": "失败后重试任务",
                "updated_at": datetime.now(UTC),
            }
        ),
    )
    return _apply_governance_decision(
        project,
        updated,
        GovernanceDecision(action="continue", status="clear", signal="manual", reason="任务已人工重试"),
        default_stage=next_stage,
    )
