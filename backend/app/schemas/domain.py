from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


class ProjectCreate(BaseModel):
    title: str
    premise: str
    genre: str = "玄幻"
    target_words: int = 1_000_000
    target_chapters: int = 3_000
    tone: str = "热血升级"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("proj"))
    title: str
    premise: str
    genre: str
    target_words: int
    target_chapters: int
    tone: str = "热血升级"
    status: Literal["draft", "active", "paused"] = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StoryBibleCreate(BaseModel):
    genre: str = "玄幻"
    tone: str = "热血升级"
    world_rules: list[str] = Field(default_factory=list)
    power_system: list[str] = Field(default_factory=list)
    forbidden_rules: list[str] = Field(default_factory=list)
    core_setting: list[str] = Field(default_factory=list)
    author_intent: list[str] = Field(default_factory=list)


class StoryBible(BaseModel):
    id: str = Field(default_factory=lambda: new_id("bible"))
    genre: str = "玄幻"
    tone: str = "热血升级"
    world_rules: list[str] = Field(default_factory=list)
    power_system: list[str] = Field(default_factory=list)
    forbidden_rules: list[str] = Field(default_factory=list)
    core_setting: list[str] = Field(default_factory=list)
    author_intent: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CharacterCreate(BaseModel):
    name: str
    role: str = "support"
    realm: str = "凡人"
    personality: list[str] = Field(default_factory=list)
    core_motivation: str = ""


class Character(BaseModel):
    id: str = Field(default_factory=lambda: new_id("char"))
    name: str
    role: str
    realm: str
    personality: list[str] = Field(default_factory=list)
    core_motivation: str = ""
    status: Literal["active", "inactive", "dead"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CharacterState(BaseModel):
    id: str = Field(default_factory=lambda: new_id("state"))
    character_id: str
    chapter_number: int
    location: str | None = None
    emotion: str | None = None
    goal: str | None = None
    relationship_signal: str | None = None
    progress_signal: str | None = None
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventCreate(BaseModel):
    chapter_number: int
    summary: str
    event_type: str = "plot"
    actor_ids: list[str] = Field(default_factory=list)
    location: str | None = None


class Event(BaseModel):
    id: str = Field(default_factory=lambda: new_id("event"))
    chapter_number: int
    summary: str
    event_type: str
    actor_ids: list[str] = Field(default_factory=list)
    location: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChapterPlanCreate(BaseModel):
    chapter_number: int
    goal: str
    conflict: str
    hook: str
    pov_character_id: str | None = None


class ChapterPlan(BaseModel):
    id: str = Field(default_factory=lambda: new_id("plan"))
    chapter_number: int
    goal: str
    conflict: str
    hook: str
    pov_character_id: str | None = None
    beats: list[str] = Field(default_factory=list)
    source: Literal["manual", "auto_replan"] = "manual"
    patch_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WriteChapterRequest(BaseModel):
    chapter_number: int
    plan_id: str | None = None
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"


class BatchWriteRequest(BaseModel):
    start_chapter: int
    end_chapter: int
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"


class SchedulerTaskCreate(BaseModel):
    start_chapter: int
    end_chapter: int
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"
    max_retries: int = 2
    mode: Literal["write", "recovery"] = "write"
    patch_id: str | None = None


class GovernancePolicyUpdate(BaseModel):
    enabled: bool = True
    max_consecutive_failures: int = 3
    max_total_estimated_cost_usd: float = 20.0
    max_chapter_cost_usd: float = 1.0
    max_conflict_score: float = 4.0
    min_reader_score: float = 6.0
    min_review_score: float = 6.0
    pause_on_review_required: bool = True
    pause_on_reader_weak: bool = True
    pause_on_state_anomaly: bool = True
    state_anomaly_keywords: list[str] = Field(
        default_factory=lambda: ["失控", "失忆", "暴走", "濒死", "死亡", "叛逃", "黑化"]
    )


class GovernancePolicy(BaseModel):
    id: str = Field(default_factory=lambda: new_id("govpolicy"))
    project_id: str
    enabled: bool = True
    max_consecutive_failures: int = 3
    max_total_estimated_cost_usd: float = 20.0
    max_chapter_cost_usd: float = 1.0
    max_conflict_score: float = 4.0
    min_reader_score: float = 6.0
    min_review_score: float = 6.0
    pause_on_review_required: bool = True
    pause_on_reader_weak: bool = True
    pause_on_state_anomaly: bool = True
    state_anomaly_keywords: list[str] = Field(
        default_factory=lambda: ["失控", "失忆", "暴走", "濒死", "死亡", "叛逃", "黑化"]
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernanceDecision(BaseModel):
    action: Literal["continue", "pause", "stop"] = "continue"
    status: Literal["clear", "warning", "blocked"] = "clear"
    signal: Literal["budget", "failure", "continuity", "reader", "state", "review", "manual"] = "manual"
    reason: str = ""
    details: list[str] = Field(default_factory=list)
    chapter_number: int | None = None


class GovernanceEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("govevent"))
    project_id: str
    task_id: str
    policy_id: str | None = None
    chapter_number: int | None = None
    level: Literal["info", "warning", "critical"] = "info"
    signal: Literal["budget", "failure", "continuity", "reader", "state", "review", "manual"]
    action: Literal["continue", "pause", "stop"] = "continue"
    summary: str
    details: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RollbackRequest(BaseModel):
    target_chapter_number: int
    reason: str = "manual rollback"


class RerunRequest(BaseModel):
    patch_id: str | None = None
    from_chapter: int
    end_chapter: int
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"


class ReviewDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = ""


class RewriteChapterRequest(BaseModel):
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"
    note: str = ""


class ReplanPatchRequest(BaseModel):
    tone: str = "热血升级"


class ChapterDraft(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chapter"))
    chapter_number: int
    title: str
    content: str
    summary: str
    status: Literal["draft", "review_required", "approved", "rejected"] = "draft"
    source: Literal["mock", "llm"] = "mock"
    revision_number: int = 1
    parent_chapter_id: str | None = None
    rewrite_source_review_id: str | None = None
    is_current: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextPack(BaseModel):
    project_id: str
    chapter_number: int
    story_bible: StoryBible
    recent_events: list[Event] = Field(default_factory=list)
    active_characters: list[Character] = Field(default_factory=list)
    long_term_memories: list["MemoryRetrievalHit"] = Field(default_factory=list)
    open_hooks: list["HookRecord"] = Field(default_factory=list)
    recent_character_states: list[CharacterState] = Field(default_factory=list)
    recent_snapshots: list[Snapshot] = Field(default_factory=list)
    open_retcon_patches: list[RetconPatch] = Field(default_factory=list)
    chapter_plan: ChapterPlan | None = None
    hard_constraints: list[str] = Field(default_factory=list)
    retrieval_priorities: list[str] = Field(default_factory=list)
    context_summary: str = ""
    story_bible_summary: str = ""
    event_summary: str = ""
    character_state_summary: str = ""
    patch_summary: str = ""
    memory_summary: str = ""
    token_budget: dict[str, int] = Field(default_factory=dict)
    retrieval_diagnostics: dict[str, list[str]] = Field(default_factory=dict)
    selection_reasoning: list[str] = Field(default_factory=list)


class WritingRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    chapter_number: int
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    writer_mode: Literal["mock", "openai"] = "mock"
    message: str = ""
    model_name: str = ""
    attempts: int = 0
    fallback_used: bool = False
    prompt_tokens_estimate: int = 0
    completion_tokens_estimate: int = 0
    total_tokens_estimate: int = 0
    error_history: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExtractedUpdate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("extract"))
    project_id: str
    chapter_number: int
    event_ids: list[str] = Field(default_factory=list)
    character_state_ids: list[str] = Field(default_factory=list)
    timeline_advance: str = ""
    hook_changes: list[str] = Field(default_factory=list)
    new_hooks: list[str] = Field(default_factory=list)
    active_hooks: list[str] = Field(default_factory=list)
    resolved_hooks: list[str] = Field(default_factory=list)
    abandoned_hooks: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    relationship_signals: list[str] = Field(default_factory=list)
    location_transitions: list[str] = Field(default_factory=list)
    goal_progress_signals: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Snapshot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("snapshot"))
    project_id: str
    chapter_number: int
    chapter_id: str
    chapter_title: str
    active_character_ids: list[str] = Field(default_factory=list)
    active_hook_ids: list[str] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VersionRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("version"))
    project_id: str
    chapter_number: int
    chapter_id: str
    snapshot_id: str
    extracted_update_id: str
    version_label: str
    change_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchWriteResult(BaseModel):
    project_id: str
    start_chapter: int
    end_chapter: int
    completed_chapters: list[int] = Field(default_factory=list)
    failed_chapter: int | None = None
    status: Literal["running", "completed", "failed"] = "completed"
    message: str = ""


class RollbackResult(BaseModel):
    project_id: str
    target_chapter_number: int
    patch_id: str | None = None
    removed_chapters: int
    removed_events: int
    removed_character_states: int
    removed_snapshots: int
    removed_versions: int
    message: str


class TaskRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    project_id: str
    task_type: Literal["single_write", "batch_write", "rollback", "rerun", "human_review", "rewrite"] = "batch_write"
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    payload_summary: str = ""
    result_summary: str = ""


class LongTermMemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("memory"))
    project_id: str
    source_type: Literal[
        "chapter",
        "event",
        "character_state",
        "snapshot",
        "hook",
        "patch",
        "review",
        "continuity",
        "reader",
    ]
    source_id: str
    chapter_number: int
    memory_type: Literal["fact", "state", "risk", "foreshadow", "summary"] = "fact"
    title: str = ""
    content: str
    keywords: list[str] = Field(default_factory=list)
    importance_score: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryRetrievalHit(BaseModel):
    record_id: str
    chapter_number: int
    source_type: str
    memory_type: str
    title: str = ""
    content: str
    retrieval_score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class MemoryRetrievalTrace(BaseModel):
    id: str = Field(default_factory=lambda: new_id("memtrace"))
    project_id: str
    chapter_number: int
    query_text: str = ""
    query_terms: list[str] = Field(default_factory=list)
    selected_record_ids: list[str] = Field(default_factory=list)
    hits: list[MemoryRetrievalHit] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RetconPatch(BaseModel):
    id: str = Field(default_factory=lambda: new_id("retcon"))
    project_id: str
    target_chapter_number: int
    reason: str
    affected_chapter_numbers: list[int] = Field(default_factory=list)
    invalidated_version_ids: list[str] = Field(default_factory=list)
    invalidated_plan_ids: list[str] = Field(default_factory=list)
    removed_chapter_numbers: list[int] = Field(default_factory=list)
    requires_recompute_hooks: list[str] = Field(default_factory=list)
    requires_state_rollback: bool = False
    impact_summary: list[str] = Field(default_factory=list)
    replanned_plan_ids: list[str] = Field(default_factory=list)
    replan_summary: list[str] = Field(default_factory=list)
    last_replanned_at: datetime | None = None
    recommended_rerun_from: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["open", "replanned", "rerun_completed"] = "open"


class HookRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("hook"))
    project_id: str
    content: str
    created_in_chapter: int
    source_chapter_id: str | None = None
    source_plan_id: str | None = None
    expected_resolution_arc: str = ""
    status: Literal["open", "active", "resolved", "abandoned"] = "open"
    last_touched_chapter: int = 0
    resolution_chapter: int | None = None
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HookStateChange(BaseModel):
    id: str = Field(default_factory=lambda: new_id("hookchange"))
    project_id: str
    hook_id: str
    chapter_number: int
    chapter_id: str
    action: Literal["create", "activate", "resolve", "abandon"]
    content: str = ""
    expected_resolution_arc: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SchedulerTask(BaseModel):
    id: str = Field(default_factory=lambda: new_id("scheduler"))
    project_id: str
    start_chapter: int
    end_chapter: int
    next_chapter: int
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"
    mode: Literal["write", "recovery"] = "write"
    stage: Literal["writing", "awaiting_review", "replanning", "rerunning", "governance_blocked", "completed"] = "writing"
    patch_id: str | None = None
    status: Literal["pending", "running", "paused", "completed", "failed"] = "pending"
    completed_chapters: list[int] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    consecutive_failures: int = 0
    last_error: str = ""
    stage_message: str = ""
    governance_policy_id: str | None = None
    governance_status: Literal["clear", "warning", "blocked"] = "clear"
    governance_reason: str = ""
    governance_last_event_id: str | None = None
    governance_cost_used_usd: float = 0.0
    governance_cost_limit_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChapterMetric(BaseModel):
    id: str = Field(default_factory=lambda: new_id("metric"))
    project_id: str
    chapter_number: int
    run_id: str
    model_name: str = ""
    source: Literal["mock", "llm"] = "mock"
    fallback_used: bool = False
    prompt_tokens_estimate: int = 0
    completion_tokens_estimate: int = 0
    total_tokens_estimate: int = 0
    estimated_cost_usd: float = 0.0
    content_length: int = 0
    quality_score: float = 0.0
    extraction_score: float = 0.0
    hook_score: float = 0.0
    review_score: float = 0.0
    reader_score: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricsSummary(BaseModel):
    project_id: str
    chapter_count: int = 0
    llm_chapter_count: int = 0
    fallback_count: int = 0
    open_hook_count: int = 0
    resolved_hook_count: int = 0
    hook_resolution_rate: float = 0.0
    total_tokens_estimate: int = 0
    total_estimated_cost_usd: float = 0.0
    average_quality_score: float = 0.0
    average_extraction_score: float = 0.0
    average_hook_score: float = 0.0
    average_review_score: float = 0.0
    average_reader_score: float = 0.0
    latest_warnings: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    project_id: str
    chapter_number: int
    chapter_id: str
    status: Literal["approved", "review_required"] = "approved"
    human_decision_status: Literal["pending", "approved", "rejected"] = "pending"
    human_decision_note: str = ""
    human_decision_at: datetime | None = None
    logic_score: float = 0.0
    continuity_score: float = 0.0
    character_score: float = 0.0
    hook_score: float = 0.0
    overall_score: float = 0.0
    decision_reason: str = ""
    findings: list[str] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)
    continuity_report_id: str | None = None
    reader_council_report_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContinuityIssue(BaseModel):
    judge: Literal["lore", "character", "timeline", "power"]
    severity: Literal["low", "medium", "high"] = "low"
    title: str
    detail: str = ""
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = ""


class ContinuityReport(BaseModel):
    id: str = Field(default_factory=lambda: new_id("continuity"))
    project_id: str
    chapter_number: int
    chapter_id: str
    status: Literal["clear", "review_required"] = "clear"
    overall_risk: Literal["low", "medium", "high"] = "low"
    judges_triggered: list[str] = Field(default_factory=list)
    summary: str = ""
    issues: list[ContinuityIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReaderFeedback(BaseModel):
    persona: Literal["core_reader", "fast_paced_reader", "emotion_reader"]
    engagement_score: float = 0.0
    hook_expectation_score: float = 0.0
    payoff_score: float = 0.0
    summary: str = ""
    likes: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ReaderCouncilReport(BaseModel):
    id: str = Field(default_factory=lambda: new_id("reader"))
    project_id: str
    chapter_number: int
    chapter_id: str
    status: Literal["strong", "weak"] = "strong"
    overall_score: float = 0.0
    chase_score: float = 0.0
    payoff_score: float = 0.0
    pace_score: float = 0.0
    summary: str = ""
    highlights: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    persona_feedbacks: list[ReaderFeedback] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewDecisionResult(BaseModel):
    chapter: ChapterDraft
    review: ReviewReport
    extracted_update: ExtractedUpdate | None = None
    snapshot: Snapshot | None = None
    version: VersionRecord | None = None


class RewriteChapterResult(BaseModel):
    chapter: ChapterDraft
    review: ReviewReport
    continuity_report: ContinuityReport
    reader_council_report: ReaderCouncilReport
    extracted_update: ExtractedUpdate
    snapshot: Snapshot | None = None
    version: VersionRecord | None = None
    metric: ChapterMetric | None = None


class ReplanPatchResult(BaseModel):
    patch: RetconPatch
    created_plans: list[ChapterPlan] = Field(default_factory=list)


class ProjectDetail(BaseModel):
    project: Project
    story_bible: StoryBible
    governance_policy: GovernancePolicy | None = None
    characters: list[Character] = Field(default_factory=list)
    character_states: list[CharacterState] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    chapter_plans: list[ChapterPlan] = Field(default_factory=list)
    chapters: list[ChapterDraft] = Field(default_factory=list)
    extracted_updates: list[ExtractedUpdate] = Field(default_factory=list)
    snapshots: list[Snapshot] = Field(default_factory=list)
    versions: list[VersionRecord] = Field(default_factory=list)
    task_runs: list[TaskRun] = Field(default_factory=list)
    retcon_patches: list[RetconPatch] = Field(default_factory=list)
    hook_records: list[HookRecord] = Field(default_factory=list)
    hook_state_changes: list[HookStateChange] = Field(default_factory=list)
    scheduler_tasks: list[SchedulerTask] = Field(default_factory=list)
    reviews: list[ReviewReport] = Field(default_factory=list)
    continuity_reports: list[ContinuityReport] = Field(default_factory=list)
    reader_council_reports: list[ReaderCouncilReport] = Field(default_factory=list)
    governance_events: list[GovernanceEvent] = Field(default_factory=list)
    long_term_memories: list[LongTermMemoryRecord] = Field(default_factory=list)
    memory_retrieval_traces: list[MemoryRetrievalTrace] = Field(default_factory=list)
    chapter_metrics: list[ChapterMetric] = Field(default_factory=list)
    metrics_summary: MetricsSummary | None = None
    latest_run: WritingRun | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    use_mock_writer: bool
    worker_running: bool = False
