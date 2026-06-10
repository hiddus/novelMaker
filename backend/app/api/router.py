from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.domain import (
    BatchWriteRequest,
    BatchWriteResult,
    ChapterPlanCreate,
    Character,
    CharacterRelationshipEdge,
    CharacterCreate,
    ContinuityReport,
    ContextPack,
    Event,
    EventCreate,
    GovernanceEvent,
    GovernancePolicy,
    GovernancePolicyUpdate,
    HealthResponse,
    HookRecord,
    HookStateChange,
    LLMChapterPreflightRequest,
    LLMChapterPreflightResult,
    LLMDiagnosticResult,
    LLMStatus,
    LLMTestRunRequest,
    LLMTestRunResult,
    LongTermMemoryRecord,
    MemoryIndexStatus,
    MemoryRetrievalTrace,
    MetricsSummary,
    ReplanPatchRequest,
    ReplanPatchResult,
    Project,
    ProjectCreate,
    ProjectDetail,
    QueueJob,
    RunOpsSummary,
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
    TimelineConstraint,
    TimelineNode,
    RetconPatch,
    ReaderCouncilReport,
    WriteChapterRequest,
    WorkerSnapshot,
    WritingRun,
)
from app.services.context_engine import build_context_pack
from app.services.llm_diagnostics import (
    diagnose_llm,
    get_llm_status,
    run_llm_test,
    run_project_chapter_preflight,
)
from app.services.memory import get_memory_index_status, rebuild_long_term_memory
from app.services.ops import build_run_ops_summary
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
    worker = scheduler_worker.snapshot()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        use_mock_writer=settings.use_mock_writer,
        worker_running=worker.is_running,
        worker_mode=worker.mode,
        queue_backlog=worker.queue_backlog,
    )


@router.get("/worker/status", response_model=WorkerSnapshot)
def worker_status() -> WorkerSnapshot:
    return scheduler_worker.snapshot()


@router.post("/worker/start", response_model=WorkerSnapshot)
def start_worker() -> WorkerSnapshot:
    scheduler_worker.start(mode="embedded")
    return scheduler_worker.snapshot()


@router.post("/worker/stop", response_model=WorkerSnapshot)
def stop_worker() -> WorkerSnapshot:
    scheduler_worker.stop()
    return scheduler_worker.snapshot()


@router.post("/worker/run-once", response_model=WorkerSnapshot)
def run_worker_once() -> WorkerSnapshot:
    scheduler_worker.run_once()
    return scheduler_worker.snapshot()


@router.get("/llm/status", response_model=LLMStatus)
def llm_status() -> LLMStatus:
    return get_llm_status()


@router.post("/llm/diagnose", response_model=LLMDiagnosticResult)
def llm_diagnose() -> LLMDiagnosticResult:
    return diagnose_llm()


@router.get("/llm/diagnostics", response_model=list[LLMDiagnosticResult])
def list_llm_diagnostics() -> list[LLMDiagnosticResult]:
    return store.list_llm_diagnostics()


@router.post("/llm/test-run", response_model=LLMTestRunResult)
def llm_test_run(payload: LLMTestRunRequest) -> LLMTestRunResult:
    try:
        return run_llm_test(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/llm/test-runs", response_model=list[LLMTestRunResult])
def list_llm_test_runs() -> list[LLMTestRunResult]:
    return store.list_llm_test_runs()


@router.get("/projects/{project_id}/llm/preflights", response_model=list[LLMChapterPreflightResult])
def list_project_llm_preflights(project_id: str) -> list[LLMChapterPreflightResult]:
    _require_project(project_id)
    return store.list_llm_chapter_preflights(project_id)


@router.post("/projects/{project_id}/llm/preflight", response_model=LLMChapterPreflightResult)
def project_llm_preflight(
    project_id: str,
    payload: LLMChapterPreflightRequest,
) -> LLMChapterPreflightResult:
    _require_project(project_id)
    try:
        return run_project_chapter_preflight(project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@router.get("/projects/{project_id}/governance/policy", response_model=GovernancePolicy)
def get_governance_policy(project_id: str) -> GovernancePolicy:
    _require_project(project_id)
    return store.get_governance_policy(project_id)


@router.put("/projects/{project_id}/governance/policy", response_model=GovernancePolicy)
def update_governance_policy(project_id: str, payload: GovernancePolicyUpdate) -> GovernancePolicy:
    _require_project(project_id)
    current = store.get_governance_policy(project_id)
    updated = current.model_copy(
        update={
            **payload.model_dump(),
            "updated_at": datetime.now(UTC),
        }
    )
    return store.save_governance_policy(project_id, updated)


@router.get("/projects/{project_id}/governance-events", response_model=list[GovernanceEvent])
def list_project_governance_events(project_id: str) -> list[GovernanceEvent]:
    _require_project(project_id)
    return store.list_governance_events(project_id)


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


@router.get("/projects/{project_id}/relationship-edges", response_model=list[CharacterRelationshipEdge])
def list_relationship_edges(project_id: str) -> list[CharacterRelationshipEdge]:
    _require_project(project_id)
    return store.list_relationship_edges(project_id)


@router.get("/projects/{project_id}/timeline-nodes", response_model=list[TimelineNode])
def list_project_timeline_nodes(project_id: str) -> list[TimelineNode]:
    _require_project(project_id)
    return store.list_timeline_nodes(project_id)


@router.get("/projects/{project_id}/timeline-constraints", response_model=list[TimelineConstraint])
def list_project_timeline_constraints(project_id: str) -> list[TimelineConstraint]:
    _require_project(project_id)
    return store.list_timeline_constraints(project_id)


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


@router.get("/projects/{project_id}/memories", response_model=list[LongTermMemoryRecord])
def list_project_memories(project_id: str) -> list[LongTermMemoryRecord]:
    _require_project(project_id)
    return store.list_long_term_memories(project_id)


@router.get("/projects/{project_id}/memory-index/status", response_model=MemoryIndexStatus)
def get_project_memory_index_status(project_id: str) -> MemoryIndexStatus:
    _require_project(project_id)
    return get_memory_index_status(project_id)


@router.post("/projects/{project_id}/memory-index/rebuild", response_model=MemoryIndexStatus)
def rebuild_project_memory_index(project_id: str) -> MemoryIndexStatus:
    _require_project(project_id)
    rebuild_long_term_memory(project_id)
    return get_memory_index_status(project_id)


@router.post("/projects/{project_id}/memories/rebuild", response_model=list[LongTermMemoryRecord])
def rebuild_project_memories(project_id: str) -> list[LongTermMemoryRecord]:
    _require_project(project_id)
    return rebuild_long_term_memory(project_id)


@router.get("/projects/{project_id}/memory-traces", response_model=list[MemoryRetrievalTrace])
def list_project_memory_traces(project_id: str) -> list[MemoryRetrievalTrace]:
    _require_project(project_id)
    return store.list_memory_retrieval_traces(project_id)


@router.get("/projects/{project_id}/ops-summary", response_model=RunOpsSummary)
def get_project_ops_summary(project_id: str) -> RunOpsSummary:
    _require_project(project_id)
    return build_run_ops_summary(project_id)


@router.get("/projects/{project_id}/chapters")
def list_chapters(project_id: str) -> list[dict[str, object]]:
    _require_project(project_id)
    return [item.model_dump(mode="json") for item in store.list_chapters(project_id)]


@router.post("/projects/{project_id}/write/chapter")
def write_chapter(project_id: str, payload: WriteChapterRequest) -> dict[str, object]:
    project = _require_project(project_id)

    try:
        return execute_write(project, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    try:
        result = execute_batch_write(project, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.message)
    return result


@router.get("/projects/{project_id}/scheduler-tasks", response_model=list[SchedulerTask])
def list_scheduler_tasks(project_id: str) -> list[SchedulerTask]:
    _require_project(project_id)
    return store.list_scheduler_tasks(project_id)


@router.get("/projects/{project_id}/queue-jobs", response_model=list[QueueJob])
def list_project_queue_jobs(project_id: str) -> list[QueueJob]:
    _require_project(project_id)
    return store.list_queue_jobs(project_id)


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
    try:
        result = execute_rerun(project, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
