from datetime import UTC, datetime

from app.schemas.domain import (
    BatchWriteRequest,
    BatchWriteResult,
    ReplanPatchRequest,
    ReplanPatchResult,
    Project,
    RerunRequest,
    ReviewDecisionRequest,
    ReviewDecisionResult,
    RewriteChapterRequest,
    RewriteChapterResult,
    RollbackResult,
    TaskRun,
    WriteChapterRequest,
)
from app.services.canon import apply_extracted_update_to_canon, extract_chapter_update
from app.services.continuity import run_continuity_board
from app.services.context_engine import build_context_pack
from app.services.metrics import build_chapter_metric
from app.services.planning import build_replanned_chapter_plans
from app.services.reader_council import run_reader_council
from app.services.reviewer import review_chapter
from app.services.store import store
from app.services.writing import create_chapter_draft, create_rewrite_draft


def execute_write(project: Project, payload: WriteChapterRequest) -> dict[str, object]:
    plans = store.list_chapter_plans(project.id)
    context_pack = build_context_pack(project.id, payload.chapter_number)
    run, chapter = create_chapter_draft(project, payload, plans, context_pack)
    store.save_run(project.id, run)
    extracted_update, created_event, created_state = extract_chapter_update(
        project.id,
        chapter,
        context_pack,
    )
    continuity_report = run_continuity_board(project.id, chapter, context_pack, extracted_update)
    store.save_continuity_report(project.id, continuity_report)
    reader_council_report = run_reader_council(project.id, chapter, context_pack, extracted_update)
    store.save_reader_council_report(project.id, reader_council_report)
    review = review_chapter(
        project.id,
        chapter,
        context_pack,
        extracted_update,
        continuity_report,
        reader_council_report,
    )
    saved_chapter = store.add_chapter(project.id, chapter.model_copy(update={"status": review.status}))
    store.save_review(project.id, review)

    snapshot = None
    version = None
    extracted_to_save = extracted_update
    if review.status == "approved":
        extracted_to_save, snapshot, version = apply_extracted_update_to_canon(
            project.id,
            saved_chapter,
            context_pack,
            extracted_update,
            created_event,
            created_state,
        )

    metric = build_chapter_metric(
        project.id,
        saved_chapter,
        run,
        extracted_to_save,
        review,
        reader_council_report,
    )
    store.save_chapter_metric(project.id, metric)
    return {
        "chapter": saved_chapter.model_dump(mode="json"),
        "review": review.model_dump(mode="json"),
        "continuity_report": continuity_report.model_dump(mode="json"),
        "reader_council_report": reader_council_report.model_dump(mode="json"),
        "extracted_update": extracted_to_save.model_dump(mode="json"),
        "snapshot": snapshot.model_dump(mode="json") if snapshot is not None else None,
        "version": version.model_dump(mode="json") if version is not None else None,
        "metric": metric.model_dump(mode="json"),
    }


def execute_review_decision(
    project: Project,
    review_id: str,
    payload: ReviewDecisionRequest,
) -> ReviewDecisionResult:
    review = store.get_review(project.id, review_id)
    if review is None:
        raise ValueError("评审记录不存在")

    chapter = store.get_chapter(project.id, review.chapter_id)
    if chapter is None:
        raise ValueError("章节草稿不存在")

    if review.human_decision_status != "pending":
        raise ValueError("该评审已经处理过了")

    task_run = TaskRun(
        project_id=project.id,
        task_type="human_review",
        status="running",
        payload_summary=f"人工审核第 {review.chapter_number} 章：{payload.decision}",
    )
    store.save_task_run(project.id, task_run)

    review_note = payload.note.strip()
    decision_time = datetime.now(UTC)
    extracted_update = None
    snapshot = None
    version = None

    if payload.decision == "approve":
        has_version = any(item.chapter_id == chapter.id for item in store.list_versions(project.id))
        if not has_version:
            context_pack = build_context_pack(project.id, chapter.chapter_number)
            extracted_update, created_event, created_state = extract_chapter_update(
                project.id,
                chapter,
                context_pack,
            )
            extracted_update, snapshot, version = apply_extracted_update_to_canon(
                project.id,
                chapter.model_copy(update={"status": "approved"}),
                context_pack,
                extracted_update,
                created_event,
                created_state,
            )

        saved_chapter = store.save_chapter(project.id, chapter.model_copy(update={"status": "approved"}))
        decision_reason = review_note or "人工审核通过，已写回 canon。"
        saved_review = store.save_review(
            project.id,
            review.model_copy(
                update={
                    "status": "approved",
                    "decision_reason": decision_reason,
                    "human_decision_status": "approved",
                    "human_decision_note": review_note,
                    "human_decision_at": decision_time,
                }
            ),
        )
    else:
        saved_chapter = store.save_chapter(project.id, chapter.model_copy(update={"status": "rejected"}))
        decision_reason = review_note or "人工审核驳回，保留草稿等待重写。"
        saved_review = store.save_review(
            project.id,
            review.model_copy(
                update={
                    "decision_reason": decision_reason,
                    "human_decision_status": "rejected",
                    "human_decision_note": review_note,
                    "human_decision_at": decision_time,
                }
            ),
        )

    task_run.status = "completed"
    task_run.completed_at = datetime.now(UTC)
    task_run.result_summary = saved_review.decision_reason
    store.save_task_run(project.id, task_run)

    return ReviewDecisionResult(
        chapter=saved_chapter,
        review=saved_review,
        extracted_update=extracted_update,
        snapshot=snapshot,
        version=version,
    )


def execute_rewrite(
    project: Project,
    review_id: str,
    payload: RewriteChapterRequest,
) -> RewriteChapterResult:
    review = store.get_review(project.id, review_id)
    if review is None:
        raise ValueError("评审记录不存在")
    if review.status != "review_required":
        raise ValueError("当前评审不需要进入重写流程")

    source_chapter = store.get_chapter(project.id, review.chapter_id)
    if source_chapter is None:
        raise ValueError("待重写章节不存在")
    if source_chapter.status == "approved":
        raise ValueError("已通过章节不能直接进入自动重写")

    revisions = store.list_chapter_revisions(project.id, source_chapter.chapter_number)
    rewrite_attempts = max(0, len(revisions) - 1)
    if rewrite_attempts >= 3:
        raise ValueError("已达到最大自动重写次数，请转人工处理")

    task_run = TaskRun(
        project_id=project.id,
        task_type="rewrite",
        status="running",
        payload_summary=f"重写第 {source_chapter.chapter_number} 章，第 {rewrite_attempts + 1} 次自动重写",
    )
    store.save_task_run(project.id, task_run)

    try:
        context_pack = build_context_pack(project.id, source_chapter.chapter_number)
        run, rewritten_chapter = create_rewrite_draft(
            project,
            payload,
            source_chapter,
            review,
            context_pack,
            revision_number=max(item.revision_number for item in revisions) + 1,
        )
        store.save_run(project.id, run)

        store.save_chapter(project.id, source_chapter.model_copy(update={"is_current": False}))
        saved_chapter = store.add_chapter(project.id, rewritten_chapter)

        extracted_update, created_event, created_state = extract_chapter_update(
            project.id,
            saved_chapter,
            context_pack,
        )
        continuity_report = run_continuity_board(project.id, saved_chapter, context_pack, extracted_update)
        store.save_continuity_report(project.id, continuity_report)
        reader_council_report = run_reader_council(project.id, saved_chapter, context_pack, extracted_update)
        store.save_reader_council_report(project.id, reader_council_report)
        rewrite_review = review_chapter(
            project.id,
            saved_chapter,
            context_pack,
            extracted_update,
            continuity_report,
            reader_council_report,
        )
        saved_chapter = store.save_chapter(project.id, saved_chapter.model_copy(update={"status": rewrite_review.status}))
        store.save_review(project.id, rewrite_review)

        snapshot = None
        version = None
        extracted_to_save = extracted_update
        if rewrite_review.status == "approved":
            extracted_to_save, snapshot, version = apply_extracted_update_to_canon(
                project.id,
                saved_chapter,
                context_pack,
                extracted_update,
                created_event,
                created_state,
            )

        metric = build_chapter_metric(
            project.id,
            saved_chapter,
            run,
            extracted_to_save,
            rewrite_review,
            reader_council_report,
        )
        store.save_chapter_metric(project.id, metric)

        task_run.status = "completed"
        task_run.completed_at = datetime.now(UTC)
        task_run.result_summary = f"已生成第 {saved_chapter.chapter_number} 章第 {saved_chapter.revision_number} 版修订稿"
        store.save_task_run(project.id, task_run)

        return RewriteChapterResult(
            chapter=saved_chapter,
            review=rewrite_review,
            continuity_report=continuity_report,
            reader_council_report=reader_council_report,
            extracted_update=extracted_to_save,
            snapshot=snapshot,
            version=version,
            metric=metric,
        )
    except Exception as exc:
        task_run.status = "failed"
        task_run.completed_at = datetime.now(UTC)
        task_run.result_summary = str(exc)
        store.save_task_run(project.id, task_run)
        raise


def execute_patch_replan(
    project: Project,
    patch_id: str,
    payload: ReplanPatchRequest,
) -> ReplanPatchResult:
    patch = next((item for item in store.list_retcon_patches(project.id) if item.id == patch_id), None)
    if patch is None:
        raise ValueError("补丁不存在")
    if patch.status == "rerun_completed":
        raise ValueError("该补丁已经完成 rerun，不应再次重规划")

    task_run = TaskRun(
        project_id=project.id,
        task_type="rerun",
        status="running",
        payload_summary=f"根据补丁 {patch.id} 自动重规划",
    )
    store.save_task_run(project.id, task_run)

    try:
        story_bible = store.get_story_bible(project.id)
        replanned = build_replanned_chapter_plans(project, story_bible, patch, payload.tone)
        chapter_numbers = [plan.chapter_number for plan in replanned]
        store.replace_chapter_plans(project.id, chapter_numbers, replanned)

        updated_patch = patch.model_copy(
            update={
                "replanned_plan_ids": [plan.id for plan in replanned],
                "replan_summary": [
                    f"已重建 {len(replanned)} 个 future chapter plans",
                    f"覆盖章节：{', '.join(str(item.chapter_number) for item in replanned)}",
                ],
                "last_replanned_at": datetime.now(UTC),
                "status": "replanned",
            }
        )
        store.save_retcon_patch(project.id, updated_patch)

        task_run.status = "completed"
        task_run.completed_at = datetime.now(UTC)
        task_run.result_summary = f"补丁 {patch.id} 已自动重规划 {len(replanned)} 章"
        store.save_task_run(project.id, task_run)
        return ReplanPatchResult(patch=updated_patch, created_plans=replanned)
    except Exception as exc:
        task_run.status = "failed"
        task_run.completed_at = datetime.now(UTC)
        task_run.result_summary = str(exc)
        store.save_task_run(project.id, task_run)
        raise


def execute_batch_write(project: Project, payload: BatchWriteRequest) -> BatchWriteResult:
    task_run = TaskRun(
        project_id=project.id,
        task_type="batch_write",
        status="running",
        payload_summary=f"连续生成第 {payload.start_chapter} 到 {payload.end_chapter} 章",
    )
    store.save_task_run(project.id, task_run)

    completed_chapters: list[int] = []
    if payload.end_chapter < payload.start_chapter:
        result = BatchWriteResult(
            project_id=project.id,
            start_chapter=payload.start_chapter,
            end_chapter=payload.end_chapter,
            completed_chapters=[],
            failed_chapter=payload.start_chapter,
            status="failed",
            message="结束章节不能小于起始章节",
        )
        task_run.status = "failed"
        task_run.completed_at = datetime.now(UTC)
        task_run.result_summary = result.message
        store.save_task_run(project.id, task_run)
        return result

    for chapter_number in range(payload.start_chapter, payload.end_chapter + 1):
        try:
            execute_write(
                project,
                WriteChapterRequest(
                    chapter_number=chapter_number,
                    tone=payload.tone,
                    writer_mode=payload.writer_mode,
                ),
            )
            completed_chapters.append(chapter_number)
        except Exception as exc:
            result = BatchWriteResult(
                project_id=project.id,
                start_chapter=payload.start_chapter,
                end_chapter=payload.end_chapter,
                completed_chapters=completed_chapters,
                failed_chapter=chapter_number,
                status="failed",
                message=str(exc),
            )
            task_run.status = "failed"
            task_run.completed_at = datetime.now(UTC)
            task_run.result_summary = result.message
            store.save_task_run(project.id, task_run)
            return result

    result = BatchWriteResult(
        project_id=project.id,
        start_chapter=payload.start_chapter,
        end_chapter=payload.end_chapter,
        completed_chapters=completed_chapters,
        status="completed",
        message=f"已连续生成 {len(completed_chapters)} 章。",
    )
    task_run.status = "completed"
    task_run.completed_at = datetime.now(UTC)
    task_run.result_summary = result.message
    store.save_task_run(project.id, task_run)
    return result


def execute_rerun(project: Project, payload: RerunRequest) -> BatchWriteResult:
    task_run = TaskRun(
        project_id=project.id,
        task_type="rerun",
        status="running",
        payload_summary=f"从第 {payload.from_chapter} 章重跑到第 {payload.end_chapter} 章",
    )
    store.save_task_run(project.id, task_run)

    result = execute_batch_write(
        project,
        BatchWriteRequest(
            start_chapter=payload.from_chapter,
            end_chapter=payload.end_chapter,
            tone=payload.tone,
            writer_mode=payload.writer_mode,
        ),
    )

    task_run.status = "completed" if result.status == "completed" else "failed"
    task_run.completed_at = datetime.now(UTC)
    task_run.result_summary = result.message
    store.save_task_run(project.id, task_run)

    if payload.patch_id:
        patches = store.list_retcon_patches(project.id)
        patch = next((item for item in patches if item.id == payload.patch_id), None)
        if patch is not None and result.status == "completed":
            patch.status = "rerun_completed"
            store.save_retcon_patch(project.id, patch)

    return result


def execute_rollback(project: Project, target_chapter_number: int, reason: str) -> tuple[RollbackResult, str]:
    task_run = TaskRun(
        project_id=project.id,
        task_type="rollback",
        status="running",
        payload_summary=f"回滚到第 {target_chapter_number} 章",
    )
    store.save_task_run(project.id, task_run)

    rollback_result, patch = store.rollback_to_chapter(project.id, target_chapter_number, reason)
    task_run.status = "completed"
    task_run.completed_at = datetime.now(UTC)
    task_run.result_summary = rollback_result.message
    store.save_task_run(project.id, task_run)
    return rollback_result, patch.id
