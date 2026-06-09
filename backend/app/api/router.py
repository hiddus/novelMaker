from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.domain import (
    BatchWriteRequest,
    BatchWriteResult,
    ChapterPlanCreate,
    Character,
    CharacterCreate,
    ContinuityReport,
    ContextPack,
    Event,
    EventCreate,
    HealthResponse,
    HookRecord,
    HookStateChange,
    MetricsSummary,
    ReplanPatchRequest,
    ReplanPatchResult,
    Project,
    ProjectCreate,
    ProjectDetail,
    RerunRequest,
    ReviewDecisionRequest,
    ReviewDecisionResult,
    RewriteChapterRequest,
    RewriteChapterResult,
    RollbackRequest,
    RollbackResult,
    SchedulerTask,
    SchedulerTaskCreate,
    ReviewReport,
    StoryBible,
    StoryBibleCreate,
    TaskRun,
    RetconPatch,
    ReaderCouncilReport,
    WriteChapterRequest,
    WritingRun,
)
from app.services.context_engine import build_context_pack
from app.services.planning import build_chapter_plan, generate_book_plan
from app.services.pipeline import (
    execute_batch_write,
    execute_patch_replan,
    execute_rerun,
    execute_review_decision,
    execute_rewrite,
    execute_rollback,
    execute_write,
)
from app.services.project_view import get_project_detail
from app.services.scheduler import (
    create_scheduler_task,
    pause_scheduler_task,
    process_scheduler_step,
    resume_scheduler_task,
    retry_scheduler_task,
    run_scheduler_to_completion,
)
from app.services.store import store
from app.services.worker import scheduler_worker

router = APIRouter(prefix="/api")


def _require_project(project_id: str) -> Project:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        use_mock_writer=settings.use_mock_writer,
        worker_running=scheduler_worker.is_running(),
    )


@router.get("/worker/status")
def worker_status() -> dict[str, object]:
    return scheduler_worker.snapshot()


@router.get("/projects", response_model=list[Project])
def list_projects() -> list[Project]:
    return store.list_projects()


@router.post("/projects", response_model=Project)
def create_project(payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump())
    return store.create_project(project)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    _require_project(project_id)
    return get_project_detail(project_id)


@router.get("/projects/{project_id}/story-bible", response_model=StoryBible)
def get_story_bible(project_id: str) -> StoryBible:
    _require_project(project_id)
    return store.get_story_bible(project_id)


@router.put("/projects/{project_id}/story-bible", response_model=StoryBible)
def update_story_bible(project_id: str, payload: StoryBibleCreate) -> StoryBible:
    _require_project(project_id)
    current = store.get_story_bible(project_id)
    updated = current.model_copy(
        update={**payload.model_dump(), "updated_at": datetime.now(UTC)},
    )
    return store.upsert_story_bible(project_id, updated)


@router.get("/projects/{project_id}/characters", response_model=list[Character])
def list_characters(project_id: str) -> list[Character]:
    _require_project(project_id)
    return store.list_characters(project_id)


@router.post("/projects/{project_id}/characters", response_model=Character)
def create_character(project_id: str, payload: CharacterCreate) -> Character:
    _require_project(project_id)
    character = Character(**payload.model_dump())
    return store.add_character(project_id, character)


@router.get("/projects/{project_id}/events", response_model=list[Event])
def list_events(project_id: str) -> list[Event]:
    _require_project(project_id)
    return store.list_events(project_id)


@router.post("/projects/{project_id}/events", response_model=Event)
def create_event(project_id: str, payload: EventCreate) -> Event:
    _require_project(project_id)
    event = Event(**payload.model_dump())
    return store.add_event(project_id, event)


@router.post("/projects/{project_id}/plan/book")
def create_book_plan(project_id: str) -> dict[str, object]:
    project = _require_project(project_id)
    return generate_book_plan(project)


@router.get("/projects/{project_id}/plans/chapters")
def list_chapter_plans(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_chapter_plans(project_id)]


@router.post("/projects/{project_id}/plan/chapter")
def create_chapter_plan(project_id: str, payload: ChapterPlanCreate) -> dict[str, object]:
    _require_project(project_id)
    plan = build_chapter_plan(payload)
    saved_plan = store.add_chapter_plan(project_id, plan)
    return saved_plan.model_dump(mode="json")


@router.get("/projects/{project_id}/context/{chapter_number}", response_model=ContextPack)
def get_context_pack(project_id: str, chapter_number: int) -> ContextPack:
    _require_project(project_id)
    return build_context_pack(project_id, chapter_number)


@router.get("/projects/{project_id}/chapters")
def list_chapters(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_chapters(project_id)]


@router.post("/projects/{project_id}/write/chapter")
def write_chapter(project_id: str, payload: WriteChapterRequest) -> dict[str, object]:
    project = _require_project(project_id)

    try:
        return execute_write(project, payload)
    except Exception as exc:
        failed_run = WritingRun(
            project_id=project_id,
            chapter_number=payload.chapter_number,
            status="failed",
            writer_mode="openai" if payload.writer_mode == "openai" else "mock",
            message=str(exc),
        )
        store.save_run(project_id, failed_run)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/projects/{project_id}/write/batch", response_model=BatchWriteResult)
def write_batch(project_id: str, payload: BatchWriteRequest) -> BatchWriteResult:
    project = _require_project(project_id)
    result = execute_batch_write(project, payload)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.message)
    return result


@router.get("/projects/{project_id}/scheduler-tasks", response_model=list[SchedulerTask])
def list_scheduler_tasks(project_id: str) -> list[SchedulerTask]:
    _require_project(project_id)
    return store.list_scheduler_tasks(project_id)


@router.post("/projects/{project_id}/scheduler-tasks", response_model=SchedulerTask)
def create_project_scheduler_task(project_id: str, payload: SchedulerTaskCreate) -> SchedulerTask:
    project = _require_project(project_id)
    try:
        return create_scheduler_task(project, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/scheduler-tasks/{task_id}/step", response_model=SchedulerTask)
def step_scheduler_task(project_id: str, task_id: str) -> SchedulerTask:
    project = _require_project(project_id)
    return process_scheduler_step(project, task_id)


@router.post("/projects/{project_id}/scheduler-tasks/{task_id}/run", response_model=BatchWriteResult)
def run_scheduler_task(project_id: str, task_id: str) -> BatchWriteResult:
    project = _require_project(project_id)
    return run_scheduler_to_completion(project, task_id)


@router.post("/projects/{project_id}/scheduler-tasks/{task_id}/pause", response_model=SchedulerTask)
def pause_project_scheduler_task(project_id: str, task_id: str) -> SchedulerTask:
    project = _require_project(project_id)
    return pause_scheduler_task(project, task_id)


@router.post("/projects/{project_id}/scheduler-tasks/{task_id}/resume", response_model=SchedulerTask)
def resume_project_scheduler_task(project_id: str, task_id: str) -> SchedulerTask:
    project = _require_project(project_id)
    return resume_scheduler_task(project, task_id)


@router.post("/projects/{project_id}/scheduler-tasks/{task_id}/retry", response_model=SchedulerTask)
def retry_project_scheduler_task(project_id: str, task_id: str) -> SchedulerTask:
    project = _require_project(project_id)
    return retry_scheduler_task(project, task_id)


@router.get("/projects/{project_id}/runs", response_model=list[WritingRun])
def list_runs(project_id: str) -> list[WritingRun]:
    _require_project(project_id)
    return store.list_runs(project_id)


@router.get("/projects/{project_id}/snapshots")
def list_snapshots(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_snapshots(project_id)]


@router.get("/projects/{project_id}/versions")
def list_versions(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_versions(project_id)]


@router.post("/projects/{project_id}/rollback", response_model=RollbackResult)
def rollback_project(project_id: str, payload: RollbackRequest) -> RollbackResult:
    project = _require_project(project_id)
    rollback_result, _patch_id = execute_rollback(
        project,
        payload.target_chapter_number,
        payload.reason,
    )
    return rollback_result


@router.post("/projects/{project_id}/rerun", response_model=BatchWriteResult)
def rerun_project(project_id: str, payload: RerunRequest) -> BatchWriteResult:
    project = _require_project(project_id)
    result = execute_rerun(project, payload)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.message)
    return result


@router.get("/projects/{project_id}/task-runs", response_model=list[TaskRun])
def list_task_runs(project_id: str) -> list[TaskRun]:
    _require_project(project_id)
    return store.list_task_runs(project_id)


@router.get("/projects/{project_id}/retcon-patches", response_model=list[RetconPatch])
def list_retcon_patches(project_id: str) -> list[RetconPatch]:
    _require_project(project_id)
    return store.list_retcon_patches(project_id)


@router.post("/projects/{project_id}/retcon-patches/{patch_id}/replan", response_model=ReplanPatchResult)
def replan_retcon_patch(
    project_id: str,
    patch_id: str,
    payload: ReplanPatchRequest,
) -> ReplanPatchResult:
    project = _require_project(project_id)
    try:
        return execute_patch_replan(project, patch_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/metrics")
def list_project_metrics(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_chapter_metrics(project_id)]


@router.get("/projects/{project_id}/metrics/summary", response_model=MetricsSummary)
def get_project_metrics_summary(project_id: str) -> MetricsSummary:
    _require_project(project_id)
    return store.build_metrics_summary(project_id)


@router.get("/projects/{project_id}/reviews", response_model=list[ReviewReport])
def list_project_reviews(project_id: str) -> list[ReviewReport]:
    _require_project(project_id)
    return store.list_reviews(project_id)


@router.get("/projects/{project_id}/continuity-reports", response_model=list[ContinuityReport])
def list_project_continuity_reports(project_id: str) -> list[ContinuityReport]:
    _require_project(project_id)
    return store.list_continuity_reports(project_id)


@router.get("/projects/{project_id}/reader-council-reports", response_model=list[ReaderCouncilReport])
def list_project_reader_council_reports(project_id: str) -> list[ReaderCouncilReport]:
    _require_project(project_id)
    return store.list_reader_council_reports(project_id)


@router.get("/projects/{project_id}/hooks", response_model=list[HookRecord])
def list_project_hooks(project_id: str) -> list[HookRecord]:
    _require_project(project_id)
    return store.list_hook_records(project_id)


@router.get("/projects/{project_id}/hook-state-changes", response_model=list[HookStateChange])
def list_project_hook_state_changes(project_id: str) -> list[HookStateChange]:
    _require_project(project_id)
    return store.list_hook_state_changes(project_id)


@router.post("/projects/{project_id}/reviews/{review_id}/decision", response_model=ReviewDecisionResult)
def decide_project_review(
    project_id: str,
    review_id: str,
    payload: ReviewDecisionRequest,
) -> ReviewDecisionResult:
    project = _require_project(project_id)
    try:
        return execute_review_decision(project, review_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/reviews/{review_id}/rewrite", response_model=RewriteChapterResult)
def rewrite_project_chapter(
    project_id: str,
    review_id: str,
    payload: RewriteChapterRequest,
) -> RewriteChapterResult:
    project = _require_project(project_id)
    try:
        return execute_rewrite(project, review_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
