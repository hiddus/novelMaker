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


class CharacterRelationshipEdge(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rel"))
    project_id: str
    chapter_number: int
    source_character_id: str
    target_character_id: str
    pair_key: str = ""
    relation_type: Literal[
        "ally",
        "enemy",
        "mentor",
        "student",
        "lover",
        "family",
        "rival",
        "unknown",
    ] = "unknown"
    direction: Literal["forward", "mutual"] = "forward"
    change_type: Literal["new", "reinforce", "shift", "reverse"] = "new"
    previous_edge_id: str | None = None
    is_current: bool = True
    intensity: float = 1.0
    evidence: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TimelineNode(BaseModel):
    id: str = Field(default_factory=lambda: new_id("timeline"))
    project_id: str
    chapter_number: int
    chapter_id: str | None = None
    event_id: str | None = None
    label: str
    location: str | None = None
    previous_location: str | None = None
    participants: list[str] = Field(default_factory=list)
    time_marker: str = ""
    predecessor_node_ids: list[str] = Field(default_factory=list)
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TimelineConstraint(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tconstraint"))
    project_id: str
    chapter_number: int
    constraint_type: Literal["ordering", "travel", "presence", "patch"] = "ordering"
    evolution_key: str = ""
    previous_constraint_id: str | None = None
    is_current: bool = True
    resolved_in_chapter: int | None = None
    severity: Literal["low", "medium", "high"] = "low"
    related_node_id: str | None = None
    related_character_id: str | None = None
    description: str
    evidence: list[str] = Field(default_factory=list)
    status: Literal["clear", "warning", "violated", "resolved"] = "clear"
    recommendation: str = ""
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
    max_continuing_timeline_risks: int = 1
    min_reader_score: float = 6.0
    min_review_score: float = 6.0
    pause_on_review_required: bool = True
    pause_on_reader_weak: bool = True
    pause_on_state_anomaly: bool = True
    pause_on_continuing_timeline_risk: bool = True
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
    max_continuing_timeline_risks: int = 1
    min_reader_score: float = 6.0
    min_review_score: float = 6.0
    pause_on_review_required: bool = True
    pause_on_reader_weak: bool = True
    pause_on_state_anomaly: bool = True
    pause_on_continuing_timeline_risk: bool = True
    state_anomaly_keywords: list[str] = Field(
        default_factory=lambda: ["失控", "失忆", "暴走", "濒死", "死亡", "叛逃", "黑化"]
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernanceDecision(BaseModel):
    action: Literal["continue", "pause", "stop"] = "continue"
    status: Literal["clear", "warning", "blocked"] = "clear"
    signal: Literal["budget", "failure", "continuity", "reader", "state", "review", "llm", "manual"] = "manual"
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
    signal: Literal["budget", "failure", "continuity", "reader", "state", "review", "llm", "manual"]
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
    relationship_edges: list[CharacterRelationshipEdge] = Field(default_factory=list)
    timeline_nodes: list[TimelineNode] = Field(default_factory=list)
    active_timeline_constraints: list[TimelineConstraint] = Field(default_factory=list)
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
    relationship_summary: str = ""
    timeline_summary: str = ""
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
    relationship_edge_ids: list[str] = Field(default_factory=list)
    location_transitions: list[str] = Field(default_factory=list)
    goal_progress_signals: list[str] = Field(default_factory=list)
    timeline_node_ids: list[str] = Field(default_factory=list)
    timeline_constraints: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Snapshot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("snapshot"))
    project_id: str
    chapter_number: int
    chapter_id: str
    chapter_title: str
    active_character_ids: list[str] = Field(default_factory=list)
    relationship_edge_ids: list[str] = Field(default_factory=list)
    timeline_node_ids: list[str] = Field(default_factory=list)
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
    term_count: int = 0
    importance_score: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryIndexStatus(BaseModel):
    project_id: str
    backend: Literal["local", "qdrant"] = "local"
    backend_status: Literal["ready", "degraded", "unavailable"] = "ready"
    ready: bool = False
    indexed_records: int = 0
    last_indexed_at: datetime | None = None
    index_location: str = ""
    collection_name: str = ""
    detail: str = ""


class MemoryRetrievalHit(BaseModel):
    record_id: str
    chapter_number: int
    source_type: str
    memory_type: str
    title: str = ""
    content: str
    retrieval_score: float = 0.0
    retrieval_backend: Literal["local", "qdrant"] = "local"
    vector_score: float = 0.0
    lexical_score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class MemoryRetrievalTrace(BaseModel):
    id: str = Field(default_factory=lambda: new_id("memtrace"))
    project_id: str
    chapter_number: int
    query_text: str = ""
    query_terms: list[str] = Field(default_factory=list)
    retrieval_backend: Literal["local", "qdrant"] = "local"
    backend_status: Literal["ready", "degraded", "unavailable"] = "ready"
    selected_record_ids: list[str] = Field(default_factory=list)
    hits: list[MemoryRetrievalHit] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueJob(BaseModel):
    id: str = Field(default_factory=lambda: new_id("queue"))
    project_id: str
    task_id: str
    job_type: Literal["scheduler_task"] = "scheduler_task"
    status: Literal["pending", "leased", "completed", "failed", "cancelled"] = "pending"
    worker_id: str | None = None
    available_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    lease_expires_at: datetime | None = None
    attempt_count: int = 0
    max_attempts: int = 20
    payload_summary: str = ""
    result_summary: str = ""
    last_error: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
    status: Literal["pending", "queued", "running", "paused", "completed", "failed"] = "pending"
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
    active_queue_job_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkerSnapshot(BaseModel):
    worker_id: str = ""
    mode: Literal["embedded", "standalone"] = "embedded"
    is_running: bool = False
    embedded_worker_enabled: bool = True
    started_at: datetime | None = None
    last_tick_at: datetime | None = None
    last_claimed_job_id: str | None = None
    active_job_id: str | None = None
    processed_jobs: int = 0
    failed_jobs: int = 0
    queue_backlog: int = 0
    poll_interval_seconds: float = 1.0


class RunOpsSummary(BaseModel):
    project_id: str
    chapter_count: int = 0
    approved_chapter_count: int = 0
    review_required_chapter_count: int = 0
    total_estimated_cost_usd: float = 0.0
    budget_limit_usd: float = 0.0
    budget_used_ratio: float = 0.0
    total_scheduler_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    paused_tasks: int = 0
    blocked_tasks: int = 0
    queue_pending_jobs: int = 0
    queue_leased_jobs: int = 0
    last_completed_chapter: int = 0
    average_quality_score_last_10: float = 0.0
    average_reader_score_last_10: float = 0.0
    average_review_score_last_10: float = 0.0
    active_timeline_risk_count: int = 0
    continuing_timeline_risk_count: int = 0
    resolved_timeline_risk_count: int = 0
    timeline_risk_alerts: list[str] = Field(default_factory=list)
    state_graph_issue_count: int = 0
    critical_state_graph_issue_count: int = 0
    state_graph_alerts: list[str] = Field(default_factory=list)
    pending_retcon_patch_count: int = 0
    replanned_retcon_patch_count: int = 0
    patch_alerts: list[str] = Field(default_factory=list)
    llm_provider: str = ""
    llm_provider_label: str = ""
    llm_readiness: Literal["ready", "degraded", "blocked"] = "blocked"
    llm_writer_route: Literal["mock", "openai"] = "mock"
    llm_last_diagnostic_status: Literal["not_run", "skipped", "ok", "error"] = "not_run"
    llm_last_diagnostic_at: datetime | None = None
    llm_last_preflight_status: Literal["not_run", "completed", "failed"] = "not_run"
    llm_last_preflight_at: datetime | None = None
    llm_last_preflight_chapter: int = 0
    llm_recent_preflight_failures: int = 0
    llm_recent_fallback_runs: int = 0
    llm_config_issue_count: int = 0
    llm_connectivity_issue_count: int = 0
    llm_fallback_issue_count: int = 0
    llm_preflight_issue_count: int = 0
    llm_alerts: list[str] = Field(default_factory=list)
    llm_health_trend: list[str] = Field(default_factory=list)
    active_stop_reasons: list[str] = Field(default_factory=list)
    recent_critical_events: list[str] = Field(default_factory=list)
    recent_task_summaries: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    state_graph_recovery_plan: StateGraphRecoveryPlan | None = None


class LLMStatus(BaseModel):
    provider: str = "openai"
    provider_label: str = "OpenAI"
    readiness: Literal["ready", "degraded", "blocked"] = "blocked"
    writer_route: Literal["mock", "openai"] = "mock"
    use_mock_writer: bool = True
    api_key_configured: bool = False
    api_key_masked: str = ""
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 0
    max_retries: int = 0
    can_run_live: bool = False
    can_run_auto_mode: bool = True
    detail: str = ""
    warnings: list[str] = Field(default_factory=list)


class LLMDiagnosticResult(BaseModel):
    status: LLMStatus
    connectivity_status: Literal["not_run", "skipped", "ok", "error"] = "not_run"
    endpoint: str = ""
    request_model: str = ""
    latency_ms: int = 0
    response_excerpt: str = ""
    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMTestRunRequest(BaseModel):
    prompt: str = "请用两句话概括一个适合长篇升级流小说的开篇引子。"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"


class LLMTestRunResult(BaseModel):
    status: Literal["completed", "failed"] = "completed"
    provider: str = "openai"
    provider_label: str = "OpenAI"
    writer_mode: Literal["mock", "openai"] = "mock"
    model_name: str = ""
    latency_ms: int = 0
    prompt_tokens_estimate: int = 0
    completion_tokens_estimate: int = 0
    total_tokens_estimate: int = 0
    response_text: str = ""
    detail: str = ""
    error: str = ""
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMChapterPreflightRequest(BaseModel):
    chapter_number: int
    tone: str = "热血升级"
    writer_mode: Literal["auto", "mock", "openai"] = "auto"


class LLMChapterPreflightResult(BaseModel):
    status: Literal["completed", "failed"] = "completed"
    project_id: str
    project_title: str = ""
    chapter_number: int
    tone: str = "热血升级"
    provider: str = "openai"
    provider_label: str = "OpenAI"
    writer_mode_requested: Literal["auto", "mock", "openai"] = "auto"
    writer_mode_resolved: Literal["mock", "openai"] = "mock"
    fallback_used: bool = False
    model_name: str = ""
    chapter_plan_found: bool = False
    active_character_count: int = 0
    recent_event_count: int = 0
    recent_state_count: int = 0
    memory_hit_count: int = 0
    relationship_count: int = 0
    timeline_node_count: int = 0
    timeline_constraint_count: int = 0
    open_hook_count: int = 0
    open_patch_count: int = 0
    prompt_chars: int = 0
    prompt_excerpt: str = ""
    context_summary: str = ""
    prompt_tokens_estimate: int = 0
    completion_tokens_estimate: int = 0
    total_tokens_estimate: int = 0
    latency_ms: int = 0
    response_excerpt: str = ""
    detail: str = ""
    error: str = ""
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class StateGraphRepairSuggestion(BaseModel):
    title: str
    detail: str = ""
    severity: Literal["warning", "critical"] = "warning"
    recommended_action: Literal["rerun_projection", "rerun_window", "manual_review"] = "manual_review"
    scheduler_mode: Literal["recovery", "manual"] = "manual"
    start_chapter: int | None = None
    end_chapter: int | None = None
    target_entity_type: str = ""
    target_entity_id: str = ""
    can_create_scheduler_task: bool = False


class StateGraphRecoveryPlan(BaseModel):
    title: str
    detail: str = ""
    severity: Literal["warning", "critical"] = "warning"
    recommended_action: Literal["rerun_projection", "rerun_window", "manual_review"] = "manual_review"
    scheduler_mode: Literal["recovery", "manual"] = "manual"
    start_chapter: int | None = None
    end_chapter: int | None = None
    can_create_scheduler_task: bool = False
    issue_count: int = 0
    critical_issue_count: int = 0
    summary_lines: list[str] = Field(default_factory=list)
    focus_categories: list[str] = Field(default_factory=list)


class StateGraphDiagnostic(BaseModel):
    category: Literal["projection", "reference", "relationship", "timeline", "revision"] = "projection"
    severity: Literal["warning", "critical"] = "warning"
    chapter_number: int | None = None
    entity_type: str = ""
    entity_id: str = ""
    summary: str
    detail: str = ""
    repair_suggestion: StateGraphRepairSuggestion | None = None


class ProjectDetail(BaseModel):
    project: Project
    story_bible: StoryBible
    governance_policy: GovernancePolicy | None = None
    characters: list[Character] = Field(default_factory=list)
    character_states: list[CharacterState] = Field(default_factory=list)
    relationship_edges: list[CharacterRelationshipEdge] = Field(default_factory=list)
    timeline_nodes: list[TimelineNode] = Field(default_factory=list)
    timeline_constraints: list[TimelineConstraint] = Field(default_factory=list)
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
    queue_jobs: list[QueueJob] = Field(default_factory=list)
    reviews: list[ReviewReport] = Field(default_factory=list)
    continuity_reports: list[ContinuityReport] = Field(default_factory=list)
    reader_council_reports: list[ReaderCouncilReport] = Field(default_factory=list)
    governance_events: list[GovernanceEvent] = Field(default_factory=list)
    long_term_memories: list[LongTermMemoryRecord] = Field(default_factory=list)
    memory_retrieval_traces: list[MemoryRetrievalTrace] = Field(default_factory=list)
    memory_index_status: MemoryIndexStatus | None = None
    chapter_metrics: list[ChapterMetric] = Field(default_factory=list)
    metrics_summary: MetricsSummary | None = None
    ops_summary: RunOpsSummary | None = None
    state_graph_diagnostics: list[StateGraphDiagnostic] = Field(default_factory=list)
    state_graph_recovery_plan: StateGraphRecoveryPlan | None = None
    latest_run: WritingRun | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    use_mock_writer: bool
    worker_running: bool = False
    worker_mode: str = "embedded"
    queue_backlog: int = 0
