<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

type HealthState = {
  status: 'loading' | 'online' | 'offline'
  message: string
}

type Project = {
  id: string
  title: string
  premise: string
  genre: string
  target_words: number
  target_chapters: number
  tone: string
  status: 'draft' | 'active' | 'paused'
}

type StoryBible = {
  genre: string
  tone: string
  world_rules: string[]
  power_system: string[]
  forbidden_rules: string[]
  core_setting: string[]
  author_intent: string[]
}

type Character = {
  id: string
  name: string
  role: string
  realm: string
  personality: string[]
  core_motivation: string
}

type EventItem = {
  id: string
  chapter_number: number
  summary: string
  event_type: string
  actor_ids: string[]
  location?: string | null
}

type ChapterPlan = {
  id: string
  chapter_number: number
  goal: string
  conflict: string
  hook: string
  beats: string[]
  source?: 'manual' | 'auto_replan'
  patch_id?: string | null
}

type ChapterDraft = {
  id: string
  chapter_number: number
  title: string
  content: string
  summary: string
  status: 'draft' | 'review_required' | 'approved' | 'rejected'
  source: 'mock' | 'llm'
  revision_number: number
  parent_chapter_id?: string | null
  rewrite_source_review_id?: string | null
  is_current: boolean
}

type WritingRun = {
  id: string
  chapter_number: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  writer_mode: 'mock' | 'openai'
  message: string
}

type CharacterState = {
  id: string
  character_id: string
  chapter_number: number
  location?: string | null
  emotion?: string | null
  goal?: string | null
  relationship_signal?: string | null
  progress_signal?: string | null
  note: string
}

type CharacterRelationshipEdge = {
  id: string
  chapter_number: number
  source_character_id: string
  target_character_id: string
  pair_key: string
  relation_type: 'ally' | 'enemy' | 'mentor' | 'student' | 'lover' | 'family' | 'rival' | 'unknown'
  direction: 'forward' | 'mutual'
  change_type: 'new' | 'reinforce' | 'shift' | 'reverse'
  previous_edge_id?: string | null
  is_current: boolean
  intensity: number
  evidence: string
  note: string
}

type TimelineNode = {
  id: string
  chapter_number: number
  chapter_id?: string | null
  event_id?: string | null
  label: string
  location?: string | null
  previous_location?: string | null
  participants: string[]
  time_marker: string
  predecessor_node_ids: string[]
  note: string
}

type TimelineConstraint = {
  id: string
  chapter_number: number
  constraint_type: 'ordering' | 'travel' | 'presence' | 'patch'
  evolution_key: string
  previous_constraint_id?: string | null
  is_current: boolean
  resolved_in_chapter?: number | null
  severity: 'low' | 'medium' | 'high'
  related_node_id?: string | null
  related_character_id?: string | null
  description: string
  evidence: string[]
  status: 'clear' | 'warning' | 'violated' | 'resolved'
  recommendation: string
}

type ExtractedUpdate = {
  id: string
  chapter_number: number
  event_ids: string[]
  character_state_ids: string[]
  timeline_advance: string
  hook_changes: string[]
  new_hooks: string[]
  active_hooks: string[]
  resolved_hooks: string[]
  abandoned_hooks: string[]
  locations: string[]
  emotions: string[]
  goals: string[]
  relationship_signals: string[]
  location_transitions: string[]
  goal_progress_signals: string[]
  summary: string
}

type ReviewReport = {
  id: string
  chapter_number: number
  chapter_id: string
  status: 'approved' | 'review_required'
  human_decision_status: 'pending' | 'approved' | 'rejected'
  human_decision_note: string
  human_decision_at?: string | null
  logic_score: number
  continuity_score: number
  character_score: number
  hook_score: number
  overall_score: number
  decision_reason: string
  findings: string[]
  rewrite_suggestions: string[]
  continuity_report_id?: string | null
  reader_council_report_id?: string | null
}

type ContinuityIssue = {
  judge: 'lore' | 'character' | 'timeline' | 'power'
  severity: 'low' | 'medium' | 'high'
  title: string
  detail: string
  evidence: string[]
  recommendation: string
}

type ContinuityReport = {
  id: string
  chapter_number: number
  chapter_id: string
  status: 'clear' | 'review_required'
  overall_risk: 'low' | 'medium' | 'high'
  judges_triggered: string[]
  summary: string
  issues: ContinuityIssue[]
}

type ReaderFeedback = {
  persona: 'core_reader' | 'fast_paced_reader' | 'emotion_reader'
  engagement_score: number
  hook_expectation_score: number
  payoff_score: number
  summary: string
  likes: string[]
  concerns: string[]
  suggestions: string[]
}

type ReaderCouncilReport = {
  id: string
  chapter_number: number
  chapter_id: string
  status: 'strong' | 'weak'
  overall_score: number
  chase_score: number
  payoff_score: number
  pace_score: number
  summary: string
  highlights: string[]
  concerns: string[]
  suggestions: string[]
  persona_feedbacks: ReaderFeedback[]
}

type HookRecord = {
  id: string
  content: string
  created_in_chapter: number
  expected_resolution_arc: string
  status: 'open' | 'active' | 'resolved' | 'abandoned'
  last_touched_chapter: number
  resolution_chapter?: number | null
  note: string
}

type HookStateChange = {
  id: string
  hook_id: string
  chapter_number: number
  chapter_id: string
  action: 'create' | 'activate' | 'resolve' | 'abandon'
  content: string
  expected_resolution_arc: string
  note: string
}

type Snapshot = {
  id: string
  chapter_number: number
  chapter_title: string
  active_character_ids: string[]
  active_hook_ids: string[]
  recent_event_ids: string[]
  summary: string
}

type VersionRecord = {
  id: string
  chapter_number: number
  version_label: string
  change_summary: string
}

type StateGraphRepairSuggestion = {
  title: string
  detail: string
  severity: 'warning' | 'critical'
  recommended_action: 'rerun_projection' | 'rerun_window' | 'manual_review'
  scheduler_mode: 'recovery' | 'manual'
  start_chapter?: number | null
  end_chapter?: number | null
  target_entity_type: string
  target_entity_id: string
  can_create_scheduler_task: boolean
}

type StateGraphRecoveryPlan = {
  title: string
  detail: string
  severity: 'warning' | 'critical'
  recommended_action: 'rerun_projection' | 'rerun_window' | 'manual_review'
  scheduler_mode: 'recovery' | 'manual'
  start_chapter?: number | null
  end_chapter?: number | null
  can_create_scheduler_task: boolean
  issue_count: number
  critical_issue_count: number
  summary_lines: string[]
  focus_categories: string[]
}

type StateGraphDiagnostic = {
  category: 'projection' | 'reference' | 'relationship' | 'timeline' | 'revision'
  severity: 'warning' | 'critical'
  chapter_number?: number | null
  entity_type: string
  entity_id: string
  summary: string
  detail: string
  repair_suggestion?: StateGraphRepairSuggestion | null
}

type BatchWriteResult = {
  project_id: string
  start_chapter: number
  end_chapter: number
  completed_chapters: number[]
  failed_chapter?: number | null
  status: 'completed' | 'failed'
  message: string
}

type RollbackResult = {
  project_id: string
  target_chapter_number: number
  patch_id?: string | null
  removed_chapters: number
  removed_events: number
  removed_character_states: number
  removed_snapshots: number
  removed_versions: number
  message: string
}

type TaskRun = {
  id: string
  task_type: 'single_write' | 'batch_write' | 'rollback' | 'rerun'
  status: 'pending' | 'running' | 'completed' | 'failed'
  payload_summary: string
  result_summary: string
}

type RetconPatch = {
  id: string
  target_chapter_number: number
  reason: string
  affected_chapter_numbers: number[]
  invalidated_plan_ids: string[]
  invalidated_version_ids: string[]
  removed_chapter_numbers: number[]
  requires_recompute_hooks: string[]
  requires_state_rollback: boolean
  impact_summary: string[]
  replanned_plan_ids: string[]
  replan_summary: string[]
  last_replanned_at?: string | null
  recommended_rerun_from: number
  status: 'open' | 'replanned' | 'rerun_completed'
}

type ContextPack = {
  project_id: string
  chapter_number: number
  hard_constraints: string[]
  retrieval_priorities: string[]
  context_summary: string
  story_bible_summary: string
  event_summary: string
  character_state_summary: string
  patch_summary: string
  memory_summary: string
  relationship_summary: string
  timeline_summary: string
  token_budget: Record<string, number>
  retrieval_diagnostics: Record<string, string[]>
  selection_reasoning: string[]
  chapter_plan?: ChapterPlan | null
  recent_events: EventItem[]
  active_characters: Character[]
  long_term_memories: MemoryRetrievalHit[]
  relationship_edges: CharacterRelationshipEdge[]
  timeline_nodes: TimelineNode[]
  active_timeline_constraints: TimelineConstraint[]
  recent_character_states: CharacterState[]
  recent_snapshots: Snapshot[]
  open_hooks: HookRecord[]
  open_retcon_patches: RetconPatch[]
}

type LongTermMemoryRecord = {
  id: string
  source_type:
    | 'chapter'
    | 'event'
    | 'character_state'
    | 'snapshot'
    | 'hook'
    | 'patch'
    | 'review'
    | 'continuity'
    | 'reader'
  source_id: string
  chapter_number: number
  memory_type: 'fact' | 'state' | 'risk' | 'foreshadow' | 'summary'
  title: string
  content: string
  keywords: string[]
  term_count: number
  importance_score: number
}

type MemoryIndexStatus = {
  project_id: string
  backend: 'local' | 'qdrant'
  backend_status: 'ready' | 'degraded' | 'unavailable'
  ready: boolean
  indexed_records: number
  last_indexed_at?: string | null
  index_location: string
  collection_name: string
  detail: string
}

type MemoryRetrievalHit = {
  record_id: string
  chapter_number: number
  source_type: string
  memory_type: string
  title: string
  content: string
  retrieval_score: number
  retrieval_backend: 'local' | 'qdrant'
  vector_score: number
  lexical_score: number
  matched_terms: string[]
  reasons: string[]
}

type MemoryRetrievalTrace = {
  id: string
  chapter_number: number
  query_text: string
  query_terms: string[]
  retrieval_backend: 'local' | 'qdrant'
  backend_status: 'ready' | 'degraded' | 'unavailable'
  selected_record_ids: string[]
  hits: MemoryRetrievalHit[]
  created_at: string
}

type QueueJob = {
  id: string
  project_id: string
  task_id: string
  job_type: 'scheduler_task'
  status: 'pending' | 'leased' | 'completed' | 'failed' | 'cancelled'
  worker_id?: string | null
  available_at: string
  lease_expires_at?: string | null
  attempt_count: number
  max_attempts: number
  payload_summary: string
  result_summary: string
  last_error: string
  created_at: string
  updated_at: string
}

type SchedulerTask = {
  id: string
  start_chapter: number
  end_chapter: number
  next_chapter: number
  tone: string
  writer_mode: 'auto' | 'mock' | 'openai'
  mode: 'write' | 'recovery'
  stage:
    | 'writing'
    | 'awaiting_review'
    | 'replanning'
    | 'rerunning'
    | 'governance_blocked'
    | 'completed'
  patch_id?: string | null
  status: 'pending' | 'queued' | 'running' | 'paused' | 'completed' | 'failed'
  completed_chapters: number[]
  retry_count: number
  max_retries: number
  consecutive_failures: number
  last_error: string
  stage_message: string
  governance_policy_id?: string | null
  governance_status: 'clear' | 'warning' | 'blocked'
  governance_reason: string
  governance_last_event_id?: string | null
  governance_cost_used_usd: number
  governance_cost_limit_usd: number
  active_queue_job_id?: string | null
}

type WorkerStatus = {
  worker_id: string
  mode: 'embedded' | 'standalone'
  is_running: boolean
  embedded_worker_enabled: boolean
  started_at?: string | null
  last_tick_at?: string | null
  last_claimed_job_id?: string | null
  active_job_id?: string | null
  processed_jobs: number
  failed_jobs: number
  queue_backlog: number
  poll_interval_seconds: number
}

type GovernancePolicy = {
  id: string
  enabled: boolean
  max_consecutive_failures: number
  max_total_estimated_cost_usd: number
  max_chapter_cost_usd: number
  max_conflict_score: number
  max_continuing_timeline_risks: number
  min_reader_score: number
  min_review_score: number
  pause_on_review_required: boolean
  pause_on_reader_weak: boolean
  pause_on_state_anomaly: boolean
  pause_on_continuing_timeline_risk: boolean
  state_anomaly_keywords: string[]
  updated_at?: string
}

type GovernanceEvent = {
  id: string
  task_id: string
  policy_id?: string | null
  chapter_number?: number | null
  level: 'info' | 'warning' | 'critical'
  signal: 'budget' | 'failure' | 'continuity' | 'reader' | 'state' | 'review' | 'llm' | 'manual'
  action: 'continue' | 'pause' | 'stop'
  summary: string
  details: string[]
  created_at: string
}

type ChapterMetric = {
  id: string
  chapter_number: number
  model_name: string
  source: 'mock' | 'llm'
  fallback_used: boolean
  total_tokens_estimate: number
  estimated_cost_usd: number
  content_length: number
  quality_score: number
  extraction_score: number
  hook_score: number
  reader_score: number
  warnings: string[]
}

type MetricsSummary = {
  chapter_count: number
  llm_chapter_count: number
  fallback_count: number
  open_hook_count: number
  resolved_hook_count: number
  hook_resolution_rate: number
  total_tokens_estimate: number
  total_estimated_cost_usd: number
  average_quality_score: number
  average_extraction_score: number
  average_hook_score: number
  average_review_score: number
  average_reader_score: number
  latest_warnings: string[]
}

type RunOpsSummary = {
  project_id: string
  chapter_count: number
  approved_chapter_count: number
  review_required_chapter_count: number
  total_estimated_cost_usd: number
  budget_limit_usd: number
  budget_used_ratio: number
  total_scheduler_tasks: number
  queued_tasks: number
  running_tasks: number
  paused_tasks: number
  blocked_tasks: number
  queue_pending_jobs: number
  queue_leased_jobs: number
  last_completed_chapter: number
  average_quality_score_last_10: number
  average_reader_score_last_10: number
  average_review_score_last_10: number
  active_timeline_risk_count: number
  continuing_timeline_risk_count: number
  resolved_timeline_risk_count: number
  timeline_risk_alerts: string[]
  state_graph_issue_count: number
  critical_state_graph_issue_count: number
  state_graph_alerts: string[]
  pending_retcon_patch_count: number
  replanned_retcon_patch_count: number
  patch_alerts: string[]
  llm_provider: string
  llm_provider_label: string
  llm_readiness: 'ready' | 'degraded' | 'blocked'
  llm_writer_route: 'mock' | 'openai'
  llm_last_diagnostic_status: 'not_run' | 'skipped' | 'ok' | 'error'
  llm_last_diagnostic_at?: string | null
  llm_last_preflight_status: 'not_run' | 'completed' | 'failed'
  llm_last_preflight_at?: string | null
  llm_last_preflight_chapter: number
  llm_recent_preflight_failures: number
  llm_recent_fallback_runs: number
  llm_config_issue_count: number
  llm_connectivity_issue_count: number
  llm_fallback_issue_count: number
  llm_preflight_issue_count: number
  llm_alerts: string[]
  llm_health_trend: string[]
  active_stop_reasons: string[]
  recent_critical_events: string[]
  recent_task_summaries: string[]
  warnings: string[]
  state_graph_recovery_plan?: StateGraphRecoveryPlan | null
}

type LLMStatus = {
  provider: string
  provider_label: string
  readiness: 'ready' | 'degraded' | 'blocked'
  writer_route: 'mock' | 'openai'
  use_mock_writer: boolean
  api_key_configured: boolean
  api_key_masked: string
  base_url: string
  model: string
  timeout_seconds: number
  max_retries: number
  can_run_live: boolean
  can_run_auto_mode: boolean
  detail: string
  warnings: string[]
}

type LLMDiagnosticResult = {
  status: LLMStatus
  connectivity_status: 'not_run' | 'skipped' | 'ok' | 'error'
  endpoint: string
  request_model: string
  latency_ms: number
  response_excerpt: string
  error: string
  warnings: string[]
  tested_at: string
}

type LLMTestRunResult = {
  status: 'completed' | 'failed'
  provider: string
  provider_label: string
  writer_mode: 'mock' | 'openai'
  model_name: string
  latency_ms: number
  prompt_tokens_estimate: number
  completion_tokens_estimate: number
  total_tokens_estimate: number
  response_text: string
  detail: string
  error: string
  tested_at: string
}

type LLMChapterPreflightResult = {
  status: 'completed' | 'failed'
  project_id: string
  project_title: string
  chapter_number: number
  tone: string
  provider: string
  provider_label: string
  writer_mode_requested: 'auto' | 'mock' | 'openai'
  writer_mode_resolved: 'mock' | 'openai'
  fallback_used: boolean
  model_name: string
  chapter_plan_found: boolean
  active_character_count: number
  recent_event_count: number
  recent_state_count: number
  memory_hit_count: number
  relationship_count: number
  timeline_node_count: number
  timeline_constraint_count: number
  open_hook_count: number
  open_patch_count: number
  prompt_chars: number
  prompt_excerpt: string
  context_summary: string
  prompt_tokens_estimate: number
  completion_tokens_estimate: number
  total_tokens_estimate: number
  latency_ms: number
  response_excerpt: string
  detail: string
  error: string
  tested_at: string
}

type ProjectDetail = {
  project: Project
  story_bible: StoryBible
  governance_policy?: GovernancePolicy | null
  characters: Character[]
  character_states: CharacterState[]
  relationship_edges: CharacterRelationshipEdge[]
  timeline_nodes: TimelineNode[]
  timeline_constraints: TimelineConstraint[]
  events: EventItem[]
  chapter_plans: ChapterPlan[]
  chapters: ChapterDraft[]
  extracted_updates: ExtractedUpdate[]
  snapshots: Snapshot[]
  versions: VersionRecord[]
  task_runs: TaskRun[]
  retcon_patches: RetconPatch[]
  hook_records: HookRecord[]
  hook_state_changes: HookStateChange[]
  scheduler_tasks: SchedulerTask[]
  queue_jobs: QueueJob[]
  reviews: ReviewReport[]
  continuity_reports: ContinuityReport[]
  reader_council_reports: ReaderCouncilReport[]
  governance_events: GovernanceEvent[]
  long_term_memories: LongTermMemoryRecord[]
  memory_retrieval_traces: MemoryRetrievalTrace[]
  memory_index_status?: MemoryIndexStatus | null
  chapter_metrics: ChapterMetric[]
  metrics_summary?: MetricsSummary | null
  ops_summary?: RunOpsSummary | null
  state_graph_diagnostics: StateGraphDiagnostic[]
  state_graph_recovery_plan?: StateGraphRecoveryPlan | null
  latest_run?: WritingRun | null
}

const apiBase = 'http://localhost:8000/api'

const health = ref<HealthState>({
  status: 'loading',
  message: '正在检测后端状态',
})
const busy = ref(false)
const projects = ref<Project[]>([])
const currentDetail = ref<ProjectDetail | null>(null)
const currentContext = ref<ContextPack | null>(null)
const workerStatus = ref<WorkerStatus | null>(null)
const llmStatus = ref<LLMStatus | null>(null)
const llmDiagnostic = ref<LLMDiagnosticResult | null>(null)
const llmTestRun = ref<LLMTestRunResult | null>(null)
const llmDiagnostics = ref<LLMDiagnosticResult[]>([])
const llmTestRuns = ref<LLMTestRunResult[]>([])
const llmPreflight = ref<LLMChapterPreflightResult | null>(null)
const llmPreflights = ref<LLMChapterPreflightResult[]>([])
const lastBatchResult = ref<BatchWriteResult | null>(null)
const lastRollbackResult = ref<RollbackResult | null>(null)
const lastRerunResult = ref<BatchWriteResult | null>(null)
const activeSchedulerTask = ref<SchedulerTask | null>(null)
const selectedProjectId = ref('')
const banner = ref('当前后端如未启动，工作台会停留在离线模式。')

const projectForm = reactive({
  title: '凡人飞升录',
  premise: '一个底层少年靠谨慎、算计和机缘在残酷修真世界中崛起。',
  genre: '玄幻',
  target_words: 1_000_000,
  target_chapters: 3000,
  tone: '热血升级',
})

const storyBibleForm = reactive({
  genre: '玄幻',
  tone: '热血升级',
  world_rules: '死人不可复活\n因果有代价',
  power_system: '炼体\n筑基\n金丹\n元婴',
  forbidden_rules: '金丹不可秒杀元婴',
  core_setting: '前期苟发育\n中期开宗立派\n后期飞升',
  author_intent: '成长\n秩序重构',
})

const characterForm = reactive({
  name: '',
  role: 'support',
  realm: '凡人',
  personality: '',
  core_motivation: '',
})

const eventForm = reactive({
  chapter_number: 1,
  summary: '',
  event_type: 'plot',
  location: '',
})

const chapterPlanForm = reactive({
  chapter_number: 1,
  goal: '',
  conflict: '',
  hook: '',
})

const writingForm = reactive({
  chapter_number: 1,
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
  tone: '热血升级',
})

const rewriteForm = reactive({
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
  tone: '热血升级',
  note: '优先修复评审指出的问题，保留已通过的剧情骨架。',
})

const replanForm = reactive({
  tone: '热血升级',
})

const batchForm = reactive({
  start_chapter: 1,
  end_chapter: 3,
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
  tone: '热血升级',
})

const rollbackForm = reactive({
  target_chapter_number: 1,
  reason: '人工回退到稳定版本',
})

const rerunForm = reactive({
  patch_id: '',
  from_chapter: 1,
  end_chapter: 3,
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
  tone: '热血升级',
})

const schedulerForm = reactive({
  start_chapter: 1,
  end_chapter: 5,
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
  tone: '热血升级',
  max_retries: 2,
  mode: 'write' as 'write' | 'recovery',
  patch_id: '',
})

const governanceForm = reactive({
  enabled: true,
  max_consecutive_failures: 3,
  max_total_estimated_cost_usd: 20,
  max_chapter_cost_usd: 1,
  max_conflict_score: 4,
  max_continuing_timeline_risks: 1,
  min_reader_score: 6,
  min_review_score: 6,
  pause_on_review_required: true,
  pause_on_reader_weak: true,
  pause_on_state_anomaly: true,
  pause_on_continuing_timeline_risk: true,
  state_anomaly_keywords: '失控\n失忆\n暴走\n濒死\n死亡\n叛逃\n黑化',
})

const llmTestForm = reactive({
  prompt: '请用两句话写一个适合百万字升级流小说的开篇引子。',
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
})

const llmPreflightForm = reactive({
  chapter_number: 1,
  tone: '热血升级',
  writer_mode: 'auto' as 'auto' | 'mock' | 'openai',
})

const modules = [
  { title: '项目管理', description: '维护基础 premise、题材、字数目标与项目状态。' },
  { title: 'Story Bible', description: '沉淀世界规则、力量体系、禁忌与作者意图。' },
  { title: '章节规划', description: '把卷目标拆成章节目标、冲突、钩子与 beats。' },
  { title: '章节生成', description: '支持 mock / OpenAI 路由，保留运行记录与草稿。' },
]

const phases = [
  {
    name: 'Phase 1',
    items: ['项目管理', 'Story Bible', '角色/事件录入', '章节规划', '章节草稿'],
  },
  {
    name: 'Phase 2',
    items: ['Context Engine', 'State Extraction', 'Canon Update', 'Snapshot / Versioning'],
  },
  {
    name: 'Phase 3',
    items: ['Human Review Gate', 'Retcon Patch', '成本面板', '批量章节执行'],
  },
]

const healthTone = computed(() => {
  if (health.value.status === 'online') return 'healthy'
  if (health.value.status === 'offline') return 'offline'
  return 'loading'
})

const activeProject = computed(() => currentDetail.value?.project ?? null)

function splitLines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function timelineConstraintStage(constraint: TimelineConstraint) {
  if (constraint.status === 'resolved') {
    return constraint.resolved_in_chapter
      ? `已在第 ${constraint.resolved_in_chapter} 章闭合`
      : '已闭合'
  }
  return constraint.is_current ? '当前约束' : '历史分支'
}

function timelineConstraintChain(constraint: TimelineConstraint) {
  return constraint.previous_constraint_id
    ? `承接 ${constraint.previous_constraint_id}`
    : '链路起点'
}

function isChapterCurrentRevision(chapterId: string) {
  const chapter = currentDetail.value?.chapters.find((item) => item.id === chapterId)
  return chapter?.is_current ?? false
}

function isReviewCurrentRevision(review: ReviewReport) {
  return isChapterCurrentRevision(review.chapter_id)
}

function isContinuityReportCurrentRevision(report: ContinuityReport) {
  return isChapterCurrentRevision(report.chapter_id)
}

function isReaderCouncilReportCurrentRevision(report: ReaderCouncilReport) {
  return isChapterCurrentRevision(report.chapter_id)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `HTTP ${response.status}`)
  }

  return (await response.json()) as T
}

async function loadHealth() {
  try {
    const data = await request<{
      status: string
      version: string
      use_mock_writer: boolean
      worker_running: boolean
      worker_mode: string
      queue_backlog: number
    }>('/health')
    health.value = {
      status: 'online',
      message: `后端在线，版本 ${data.version}，mock writer=${String(data.use_mock_writer)}，worker=${String(data.worker_running)} / mode=${data.worker_mode} / backlog=${data.queue_backlog}`,
    }
  } catch {
    health.value = {
      status: 'offline',
      message: '后端暂不可达，请先启动 FastAPI 服务。',
    }
  }
}

async function loadWorkerStatus() {
  try {
    workerStatus.value = await request<WorkerStatus>('/worker/status')
  } catch {
    workerStatus.value = null
  }
}

async function loadLLMStatus() {
  try {
    llmStatus.value = await request<LLMStatus>('/llm/status')
  } catch {
    llmStatus.value = null
  }
}

async function loadLLMHistory() {
  try {
    const [diagnostics, testRuns] = await Promise.all([
      request<LLMDiagnosticResult[]>('/llm/diagnostics'),
      request<LLMTestRunResult[]>('/llm/test-runs'),
    ])
    llmDiagnostics.value = diagnostics.slice().reverse()
    llmTestRuns.value = testRuns.slice().reverse()
    llmDiagnostic.value = llmDiagnostics.value[0] ?? null
    llmTestRun.value = llmTestRuns.value[0] ?? null
  } catch {
    llmDiagnostics.value = []
    llmTestRuns.value = []
  }
}

async function loadLLMPreflightHistory(projectId: string) {
  if (!projectId) {
    llmPreflight.value = null
    llmPreflights.value = []
    return
  }
  try {
    const items = await request<LLMChapterPreflightResult[]>(`/projects/${projectId}/llm/preflights`)
    llmPreflights.value = items.slice().reverse()
    llmPreflight.value = llmPreflights.value[0] ?? null
  } catch {
    llmPreflight.value = null
    llmPreflights.value = []
  }
}

async function loadProjects() {
  try {
    projects.value = await request<Project[]>('/projects')
    if (!selectedProjectId.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id
      await loadProjectDetail(selectedProjectId.value)
    }
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '加载项目失败'
  }
}

async function loadProjectDetail(projectId: string) {
  if (!projectId) return
  try {
    currentDetail.value = await request<ProjectDetail>(`/projects/${projectId}`)
    currentContext.value = null
    if (currentDetail.value.chapters.length > 0) {
      const latestChapter = currentDetail.value.chapters[currentDetail.value.chapters.length - 1]
      rollbackForm.target_chapter_number = latestChapter.chapter_number
      batchForm.start_chapter = latestChapter.chapter_number + 1
      batchForm.end_chapter = latestChapter.chapter_number + 3
      rerunForm.from_chapter = latestChapter.chapter_number + 1
      rerunForm.end_chapter = latestChapter.chapter_number + 3
      schedulerForm.start_chapter = latestChapter.chapter_number + 1
      schedulerForm.end_chapter = latestChapter.chapter_number + 5
      llmPreflightForm.chapter_number = latestChapter.chapter_number + 1
    }
    if (currentDetail.value.retcon_patches.length > 0) {
      const latestPatch =
        currentDetail.value.retcon_patches[currentDetail.value.retcon_patches.length - 1]
      rerunForm.patch_id = latestPatch.id
      rerunForm.from_chapter = latestPatch.recommended_rerun_from
      schedulerForm.patch_id = latestPatch.id
      schedulerForm.start_chapter = latestPatch.recommended_rerun_from
    }
    activeSchedulerTask.value =
      currentDetail.value.scheduler_tasks[currentDetail.value.scheduler_tasks.length - 1] ?? null
    syncStoryBibleForm()
    syncGovernanceForm()
    await loadLLMPreflightHistory(projectId)
    await loadWorkerStatus()
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '加载项目详情失败'
  }
}

function syncStoryBibleForm() {
  if (!currentDetail.value) return
  const bible = currentDetail.value.story_bible
  storyBibleForm.genre = bible.genre
  storyBibleForm.tone = bible.tone
  storyBibleForm.world_rules = bible.world_rules.join('\n')
  storyBibleForm.power_system = bible.power_system.join('\n')
  storyBibleForm.forbidden_rules = bible.forbidden_rules.join('\n')
  storyBibleForm.core_setting = bible.core_setting.join('\n')
  storyBibleForm.author_intent = bible.author_intent.join('\n')
  writingForm.tone = bible.tone
  llmPreflightForm.tone = bible.tone
}

function syncGovernanceForm() {
  const policy = currentDetail.value?.governance_policy
  if (!policy) return
  governanceForm.enabled = policy.enabled
  governanceForm.max_consecutive_failures = policy.max_consecutive_failures
  governanceForm.max_total_estimated_cost_usd = policy.max_total_estimated_cost_usd
  governanceForm.max_chapter_cost_usd = policy.max_chapter_cost_usd
  governanceForm.max_conflict_score = policy.max_conflict_score
  governanceForm.max_continuing_timeline_risks = policy.max_continuing_timeline_risks
  governanceForm.min_reader_score = policy.min_reader_score
  governanceForm.min_review_score = policy.min_review_score
  governanceForm.pause_on_review_required = policy.pause_on_review_required
  governanceForm.pause_on_reader_weak = policy.pause_on_reader_weak
  governanceForm.pause_on_state_anomaly = policy.pause_on_state_anomaly
  governanceForm.pause_on_continuing_timeline_risk = policy.pause_on_continuing_timeline_risk
  governanceForm.state_anomaly_keywords = policy.state_anomaly_keywords.join('\n')
}

async function createProject() {
  busy.value = true
  try {
    const project = await request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(projectForm),
    })
    banner.value = `项目 ${project.title} 已创建`
    await loadProjects()
    selectedProjectId.value = project.id
    await loadProjectDetail(project.id)
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '创建项目失败'
  } finally {
    busy.value = false
  }
}

async function saveStoryBible() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/story-bible`, {
      method: 'PUT',
      body: JSON.stringify({
        genre: storyBibleForm.genre,
        tone: storyBibleForm.tone,
        world_rules: splitLines(storyBibleForm.world_rules),
        power_system: splitLines(storyBibleForm.power_system),
        forbidden_rules: splitLines(storyBibleForm.forbidden_rules),
        core_setting: splitLines(storyBibleForm.core_setting),
        author_intent: splitLines(storyBibleForm.author_intent),
      }),
    })
    banner.value = 'Story Bible 已保存'
    await loadProjectDetail(selectedProjectId.value)
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '保存 Story Bible 失败'
  } finally {
    busy.value = false
  }
}

async function addCharacter() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/characters`, {
      method: 'POST',
      body: JSON.stringify({
        ...characterForm,
        personality: splitLines(characterForm.personality),
      }),
    })
    characterForm.name = ''
    characterForm.personality = ''
    characterForm.core_motivation = ''
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '角色已添加'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '添加角色失败'
  } finally {
    busy.value = false
  }
}

async function addEvent() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/events`, {
      method: 'POST',
      body: JSON.stringify({
        ...eventForm,
        actor_ids: [],
        location: eventForm.location || null,
      }),
    })
    eventForm.summary = ''
    eventForm.location = ''
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '事件已添加'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '添加事件失败'
  } finally {
    busy.value = false
  }
}

async function addChapterPlan() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/plan/chapter`, {
      method: 'POST',
      body: JSON.stringify(chapterPlanForm),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '章节规划已生成'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '生成章节规划失败'
  } finally {
    busy.value = false
  }
}

async function writeChapter() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/write/chapter`, {
      method: 'POST',
      body: JSON.stringify(writingForm),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '章节草稿已生成'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '生成章节草稿失败'
  } finally {
    busy.value = false
  }
}

async function decideReview(reviewId: string, decision: 'approve' | 'reject') {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    const payload = {
      decision,
      note: decision === 'approve' ? '人工审核通过' : '人工审核驳回，等待重写',
    }
    await request(`/projects/${selectedProjectId.value}/reviews/${reviewId}/decision`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value =
      decision === 'approve' ? '人工审核已通过，章节已写回 canon' : '人工审核已驳回，章节已标记为 rejected'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '人工审核操作失败'
  } finally {
    busy.value = false
  }
}

async function rewriteChapter(reviewId: string) {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/reviews/${reviewId}/rewrite`, {
      method: 'POST',
      body: JSON.stringify(rewriteForm),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '已生成新的修订稿，并重新进入评审链路'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '自动重写失败'
  } finally {
    busy.value = false
  }
}

async function replanPatch(patchId: string) {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/retcon-patches/${patchId}/replan`, {
      method: 'POST',
      body: JSON.stringify(replanForm),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value = `补丁 ${patchId} 已完成自动重规划`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '自动重规划失败'
  } finally {
    busy.value = false
  }
}

async function writeBatch() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    lastBatchResult.value = await request<BatchWriteResult>(
      `/projects/${selectedProjectId.value}/write/batch`,
      {
        method: 'POST',
        body: JSON.stringify(batchForm),
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = lastBatchResult.value.message
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '批量章节生成失败'
  } finally {
    busy.value = false
  }
}

async function rollbackProject() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    lastRollbackResult.value = await request<RollbackResult>(
      `/projects/${selectedProjectId.value}/rollback`,
      {
        method: 'POST',
        body: JSON.stringify(rollbackForm),
      },
    )
    if (lastRollbackResult.value.patch_id) {
      rerunForm.patch_id = lastRollbackResult.value.patch_id
      rerunForm.from_chapter = lastRollbackResult.value.target_chapter_number + 1
      rerunForm.end_chapter = Math.max(
        rerunForm.from_chapter,
        rerunForm.from_chapter + 2,
      )
    }
    await loadProjectDetail(selectedProjectId.value)
    banner.value = lastRollbackResult.value.message
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '回滚失败'
  } finally {
    busy.value = false
  }
}

async function rerunProject() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    lastRerunResult.value = await request<BatchWriteResult>(
      `/projects/${selectedProjectId.value}/rerun`,
      {
        method: 'POST',
        body: JSON.stringify(rerunForm),
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = lastRerunResult.value.message
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '重跑失败'
  } finally {
    busy.value = false
  }
}

async function loadContextPreview() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    currentContext.value = await request<ContextPack>(
      `/projects/${selectedProjectId.value}/context/${writingForm.chapter_number}`,
    )
    banner.value = `已加载第 ${writingForm.chapter_number} 章上下文包`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '加载上下文包失败'
  } finally {
    busy.value = false
  }
}

async function createSchedulerTask() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    const payload =
      schedulerForm.mode === 'recovery'
        ? {
            start_chapter: schedulerForm.start_chapter,
            end_chapter: schedulerForm.end_chapter,
            writer_mode: schedulerForm.writer_mode,
            tone: schedulerForm.tone,
            max_retries: schedulerForm.max_retries,
            mode: schedulerForm.mode,
            patch_id: schedulerForm.patch_id || null,
          }
        : {
            start_chapter: schedulerForm.start_chapter,
            end_chapter: schedulerForm.end_chapter,
            writer_mode: schedulerForm.writer_mode,
            tone: schedulerForm.tone,
            max_retries: schedulerForm.max_retries,
            mode: schedulerForm.mode,
            patch_id: null,
          }
    activeSchedulerTask.value = await request<SchedulerTask>(
      `/projects/${selectedProjectId.value}/scheduler-tasks`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = `已创建调度任务 ${activeSchedulerTask.value.id}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '创建调度任务失败'
  } finally {
    busy.value = false
  }
}

async function applyStateGraphRepairSuggestion(
  suggestion: StateGraphRepairSuggestion | null | undefined,
  createNow = false,
) {
  if (!suggestion) {
    banner.value = '当前诊断尚未生成修复建议'
    return
  }
  if (
    !suggestion.can_create_scheduler_task ||
    suggestion.scheduler_mode !== 'recovery' ||
    suggestion.start_chapter == null ||
    suggestion.end_chapter == null
  ) {
    banner.value = suggestion.detail || '该建议需要人工处理，暂不支持直接创建 recovery 任务'
    return
  }
  schedulerForm.mode = 'recovery'
  schedulerForm.patch_id = ''
  schedulerForm.start_chapter = suggestion.start_chapter
  schedulerForm.end_chapter = suggestion.end_chapter
  schedulerForm.tone = currentDetail.value?.story_bible.tone || activeProject.value?.tone || schedulerForm.tone
  banner.value = `已载入修复建议：第 ${suggestion.start_chapter} 章 -> 第 ${suggestion.end_chapter} 章`
  if (createNow) {
    await createSchedulerTask()
  }
}

async function applyStateGraphRecoveryPlan(
  plan: StateGraphRecoveryPlan | null | undefined,
  createNow = false,
) {
  if (!plan) {
    banner.value = '当前项目尚未生成批量恢复计划'
    return
  }
  if (
    !plan.can_create_scheduler_task ||
    plan.scheduler_mode !== 'recovery' ||
    plan.start_chapter == null ||
    plan.end_chapter == null
  ) {
    banner.value = plan.detail || '当前恢复计划需要人工处理'
    return
  }
  schedulerForm.mode = 'recovery'
  schedulerForm.patch_id = ''
  schedulerForm.start_chapter = plan.start_chapter
  schedulerForm.end_chapter = plan.end_chapter
  schedulerForm.tone = currentDetail.value?.story_bible.tone || activeProject.value?.tone || schedulerForm.tone
  banner.value = `已载入批量恢复计划：第 ${plan.start_chapter} 章 -> 第 ${plan.end_chapter} 章`
  if (createNow) {
    await createSchedulerTask()
  }
}

async function saveGovernancePolicy() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    await request(`/projects/${selectedProjectId.value}/governance/policy`, {
      method: 'PUT',
      body: JSON.stringify({
        ...governanceForm,
        state_anomaly_keywords: splitLines(governanceForm.state_anomaly_keywords),
      }),
    })
    await loadProjectDetail(selectedProjectId.value)
    banner.value = '运行治理策略已保存'
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '保存治理策略失败'
  } finally {
    busy.value = false
  }
}

async function rebuildMemories() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    const status = await request<MemoryIndexStatus>(
      `/projects/${selectedProjectId.value}/memory-index/rebuild`,
      {
        method: 'POST',
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = `长期记忆索引已重建，backend=${status.backend} / status=${status.backend_status}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '重建长期记忆失败'
  } finally {
    busy.value = false
  }
}

async function controlSchedulerTask(action: 'step' | 'pause' | 'resume' | 'retry') {
  if (!selectedProjectId.value || !activeSchedulerTask.value) return
  busy.value = true
  try {
    activeSchedulerTask.value = await request<SchedulerTask>(
      `/projects/${selectedProjectId.value}/scheduler-tasks/${activeSchedulerTask.value.id}/${action}`,
      {
        method: 'POST',
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = `调度任务已执行 ${action}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '调度任务操作失败'
  } finally {
    busy.value = false
  }
}

async function runSchedulerTask() {
  if (!selectedProjectId.value || !activeSchedulerTask.value) return
  busy.value = true
  try {
    lastBatchResult.value = await request<BatchWriteResult>(
      `/projects/${selectedProjectId.value}/scheduler-tasks/${activeSchedulerTask.value.id}/run`,
      {
        method: 'POST',
      },
    )
    await loadProjectDetail(selectedProjectId.value)
    banner.value = lastBatchResult.value.message
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '运行调度任务失败'
  } finally {
    busy.value = false
  }
}

async function controlWorker(action: 'start' | 'stop' | 'run-once') {
  busy.value = true
  try {
    workerStatus.value = await request<WorkerStatus>(`/worker/${action}`, {
      method: 'POST',
    })
    await loadHealth()
    await loadLLMStatus()
    await loadLLMHistory()
    if (selectedProjectId.value) {
      await loadProjectDetail(selectedProjectId.value)
    }
    banner.value = `worker 已执行 ${action}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : 'worker 操作失败'
  } finally {
    busy.value = false
  }
}

async function diagnoseLLM() {
  busy.value = true
  try {
    llmDiagnostic.value = await request<LLMDiagnosticResult>('/llm/diagnose', {
      method: 'POST',
    })
    llmStatus.value = llmDiagnostic.value.status
    await loadLLMHistory()
    banner.value = `LLM 连通性探测完成：${llmDiagnostic.value.connectivity_status}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : 'LLM 连通性探测失败'
  } finally {
    busy.value = false
  }
}

async function runLLMTest() {
  busy.value = true
  try {
    llmTestRun.value = await request<LLMTestRunResult>('/llm/test-run', {
      method: 'POST',
      body: JSON.stringify(llmTestForm),
    })
    await loadLLMStatus()
    await loadLLMHistory()
    banner.value = `LLM 试运行完成：${llmTestRun.value.writer_mode} / ${llmTestRun.value.model_name}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : 'LLM 试运行失败'
  } finally {
    busy.value = false
  }
}

async function runLLMChapterPreflight() {
  if (!selectedProjectId.value) return
  busy.value = true
  try {
    llmPreflight.value = await request<LLMChapterPreflightResult>(
      `/projects/${selectedProjectId.value}/llm/preflight`,
      {
        method: 'POST',
        body: JSON.stringify(llmPreflightForm),
      },
    )
    await loadLLMPreflightHistory(selectedProjectId.value)
    banner.value = `章节 preflight 完成：第 ${llmPreflight.value.chapter_number} 章 / ${llmPreflight.value.writer_mode_resolved}`
  } catch (error) {
    banner.value = error instanceof Error ? error.message : '章节级 preflight 失败'
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await loadHealth()
  if (health.value.status === 'online') {
    await loadWorkerStatus()
    await loadLLMStatus()
    await loadLLMHistory()
    await loadProjects()
  }
})
</script>

<template>
  <main class="page-shell">
    <section class="hero-card">
      <div class="hero-copy">
        <p class="eyebrow">NovelMaker</p>
        <h1>长篇小说 Agent 生产系统工作台</h1>
        <p class="hero-text">
          当前版本已经可以完成项目创建、Story Bible 维护、角色/事件录入、章节规划和章节草稿生成。
          现在已经补上运行治理层，并继续加入长期记忆索引与跨章节召回。
        </p>
      </div>
      <div class="status-card" :data-tone="healthTone">
        <span class="status-label">后端状态</span>
        <strong>{{ health.message }}</strong>
      </div>
    </section>

    <section class="panel banner-panel">
      <div class="panel-head">
        <h2>当前提示</h2>
        <span>{{ busy ? '执行中' : '空闲' }}</span>
      </div>
      <p>{{ banner }}</p>
    </section>

    <section class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>Worker 状态</h2>
          <span>{{ workerStatus?.mode ?? 'unknown' }}</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>{{ workerStatus?.worker_id || '未连接 worker' }}</h3>
            <p>运行中：{{ workerStatus?.is_running ? 'yes' : 'no' }}</p>
            <p>嵌入启动：{{ workerStatus?.embedded_worker_enabled ? 'yes' : 'no' }}</p>
            <p>队列积压：{{ workerStatus?.queue_backlog ?? 0 }}</p>
            <p>已处理：{{ workerStatus?.processed_jobs ?? 0 }} / 失败：{{ workerStatus?.failed_jobs ?? 0 }}</p>
            <p>活跃 job：{{ workerStatus?.active_job_id || '无' }}</p>
            <p>最近认领：{{ workerStatus?.last_claimed_job_id || '无' }}</p>
            <p>最近 tick：{{ workerStatus?.last_tick_at || '无' }}</p>
          </div>
        </div>
        <div class="actions wrap-actions">
          <button :disabled="busy" @click="controlWorker('start')">启动嵌入 Worker</button>
          <button :disabled="busy" @click="controlWorker('run-once')">执行一轮</button>
          <button :disabled="busy" @click="controlWorker('stop')">停止嵌入 Worker</button>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>LLM 诊断</h2>
          <span>{{ llmStatus?.provider_label ?? 'unknown' }}</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>{{ llmStatus?.provider ?? '未加载 provider' }}</h3>
            <p>readiness：{{ llmStatus?.readiness ?? 'unknown' }}</p>
            <p>auto route：{{ llmStatus?.writer_route ?? 'unknown' }}</p>
            <p>mock writer：{{ llmStatus?.use_mock_writer ? 'yes' : 'no' }}</p>
            <p>API Key：{{ llmStatus?.api_key_configured ? (llmStatus.api_key_masked || '已配置') : '未配置' }}</p>
            <p>base_url：{{ llmStatus?.base_url || '无' }}</p>
            <p>model：{{ llmStatus?.model || '无' }}</p>
            <p>{{ llmStatus?.detail || '尚未加载 LLM 状态。' }}</p>
            <ul v-if="llmStatus?.warnings.length" class="mini-list">
              <li v-for="warning in llmStatus.warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>
          <label class="full">
            <span>试运行模式</span>
            <select v-model="llmTestForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label class="full">
            <span>试运行 Prompt</span>
            <textarea v-model="llmTestForm.prompt" rows="4" />
          </label>
          <label v-if="selectedProjectId" class="full">
            <span>章节级 Preflight 章节号</span>
            <input v-model.number="llmPreflightForm.chapter_number" type="number" min="1" />
          </label>
          <label v-if="selectedProjectId">
            <span>Preflight 模式</span>
            <select v-model="llmPreflightForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label v-if="selectedProjectId">
            <span>Preflight 基调</span>
            <input v-model="llmPreflightForm.tone" />
          </label>
        </div>
        <div class="actions wrap-actions">
          <button :disabled="busy" @click="loadLLMStatus">刷新状态</button>
          <button :disabled="busy" @click="loadLLMHistory">刷新历史</button>
          <button :disabled="busy" @click="diagnoseLLM">连通性探测</button>
          <button :disabled="busy" @click="runLLMTest">试运行</button>
          <button v-if="selectedProjectId" :disabled="busy" @click="runLLMChapterPreflight">
            章节级 Preflight
          </button>
        </div>
        <div class="stack compact">
          <div v-if="llmDiagnostic" class="item-card">
            <h3>最近诊断</h3>
            <p>状态：{{ llmDiagnostic.connectivity_status }} / latency={{ llmDiagnostic.latency_ms }}ms</p>
            <p>endpoint：{{ llmDiagnostic.endpoint || '无' }}</p>
            <p>model：{{ llmDiagnostic.request_model || '无' }}</p>
            <p>响应摘要：{{ llmDiagnostic.response_excerpt || '无' }}</p>
            <p v-if="llmDiagnostic.error">错误：{{ llmDiagnostic.error }}</p>
            <p>时间：{{ llmDiagnostic.tested_at }}</p>
            <ul v-if="llmDiagnostic.warnings.length" class="mini-list">
              <li v-for="warning in llmDiagnostic.warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>
          <div v-if="llmTestRun" class="item-card">
            <h3>最近试运行</h3>
            <p>模式：{{ llmTestRun.writer_mode }} / 模型：{{ llmTestRun.model_name }}</p>
            <p>状态：{{ llmTestRun.status }} / latency={{ llmTestRun.latency_ms }}ms</p>
            <p>Token：{{ llmTestRun.total_tokens_estimate }} = {{ llmTestRun.prompt_tokens_estimate }} + {{ llmTestRun.completion_tokens_estimate }}</p>
            <p>{{ llmTestRun.detail }}</p>
            <p v-if="llmTestRun.error">错误：{{ llmTestRun.error }}</p>
            <details>
              <summary>查看试运行输出</summary>
              <pre>{{ llmTestRun.response_text }}</pre>
            </details>
          </div>
          <div v-if="llmDiagnostics.length > 1" class="item-card">
            <h3>诊断历史</h3>
            <ul class="mini-list">
              <li
                v-for="item in llmDiagnostics.slice(0, 5)"
                :key="`${item.tested_at}-${item.connectivity_status}-${item.endpoint}`"
              >
                {{ item.tested_at }} / {{ item.connectivity_status }} / {{ item.status.provider }} /
                {{ item.request_model || 'n/a' }}
              </li>
            </ul>
          </div>
          <div v-if="llmTestRuns.length > 1" class="item-card">
            <h3>试运行历史</h3>
            <ul class="mini-list">
              <li
                v-for="item in llmTestRuns.slice(0, 5)"
                :key="`${item.tested_at}-${item.writer_mode}-${item.model_name}`"
              >
                {{ item.tested_at }} / {{ item.writer_mode }} / {{ item.model_name }} /
                tokens={{ item.total_tokens_estimate }}
              </li>
            </ul>
          </div>
          <div v-if="llmPreflight" class="item-card">
            <h3>最近章节级 Preflight</h3>
            <p>
              项目：{{ llmPreflight.project_title }} / 第 {{ llmPreflight.chapter_number }} 章 /
              {{ llmPreflight.writer_mode_resolved }} / {{ llmPreflight.model_name || 'n/a' }}
            </p>
            <p>
              plan={{ llmPreflight.chapter_plan_found ? 'yes' : 'no' }} / latency={{ llmPreflight.latency_ms }}ms /
              fallback={{ llmPreflight.fallback_used ? 'yes' : 'no' }}
            </p>
            <p>
              context: char={{ llmPreflight.active_character_count }}, event={{ llmPreflight.recent_event_count }},
              state={{ llmPreflight.recent_state_count }}, memory={{ llmPreflight.memory_hit_count }},
              rel={{ llmPreflight.relationship_count }}, timeline={{ llmPreflight.timeline_node_count }}
            </p>
            <p>
              hooks={{ llmPreflight.open_hook_count }} / patches={{ llmPreflight.open_patch_count }} /
              prompt_chars={{ llmPreflight.prompt_chars }} / tokens={{ llmPreflight.total_tokens_estimate }}
            </p>
            <p>{{ llmPreflight.context_summary }}</p>
            <p>{{ llmPreflight.detail }}</p>
            <p v-if="llmPreflight.error">错误：{{ llmPreflight.error }}</p>
            <details>
              <summary>查看 prompt 预览</summary>
              <pre>{{ llmPreflight.prompt_excerpt }}</pre>
            </details>
            <details>
              <summary>查看输出摘要</summary>
              <pre>{{ llmPreflight.response_excerpt }}</pre>
            </details>
          </div>
          <div v-if="llmPreflights.length > 1" class="item-card">
            <h3>章节级 Preflight 历史</h3>
            <ul class="mini-list">
              <li
                v-for="item in llmPreflights.slice(0, 5)"
                :key="`${item.project_id}-${item.chapter_number}-${item.tested_at}`"
              >
                {{ item.tested_at }} / {{ item.project_title }} / ch{{ item.chapter_number }} /
                {{ item.writer_mode_resolved }} / {{ item.status }}
              </li>
            </ul>
          </div>
        </div>
      </article>
    </section>

    <section class="grid two-cols top-grid">
      <article class="panel">
        <div class="panel-head">
          <h2>新建项目</h2>
          <span>先创建单书工程</span>
        </div>
        <div class="form-grid">
          <label>
            <span>项目标题</span>
            <input v-model="projectForm.title" />
          </label>
          <label class="full">
            <span>Premise</span>
            <textarea v-model="projectForm.premise" rows="3" />
          </label>
          <label>
            <span>题材</span>
            <input v-model="projectForm.genre" />
          </label>
          <label>
            <span>基调</span>
            <input v-model="projectForm.tone" />
          </label>
          <label>
            <span>目标字数</span>
            <input v-model.number="projectForm.target_words" type="number" />
          </label>
          <label>
            <span>目标章节</span>
            <input v-model.number="projectForm.target_chapters" type="number" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="createProject">创建项目</button>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>项目列表</h2>
          <span>{{ projects.length }} 本书</span>
        </div>
        <div class="stack">
          <select v-model="selectedProjectId" @change="loadProjectDetail(selectedProjectId)">
            <option value="">请选择项目</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.title }}
            </option>
          </select>
          <div v-for="module in modules" :key="module.title" class="item-card">
            <h3>{{ module.title }}</h3>
            <p>{{ module.description }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>当前项目概览</h2>
          <span>{{ activeProject?.title ?? '未选择项目' }}</span>
        </div>
        <div v-if="currentDetail" class="stats-grid">
          <div class="stat-card">
            <strong>{{ currentDetail.characters.length }}</strong>
            <span>角色</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.events.length }}</strong>
            <span>事件</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.chapter_plans.length }}</strong>
            <span>章节规划</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.chapters.length }}</strong>
            <span>章节草稿</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.snapshots.length }}</strong>
            <span>快照</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.versions.length }}</strong>
            <span>版本</span>
          </div>
          <div class="stat-card full">
            <strong>{{ currentDetail.latest_run?.status ?? '暂无运行记录' }}</strong>
            <span>{{ currentDetail.latest_run?.message ?? '尚未执行写作任务' }}</span>
          </div>
        </div>
        <p v-else class="muted">选择项目后可查看聚合视图。</p>
      </article>
    </section>

    <section v-if="currentDetail" class="panel">
      <div class="panel-head">
        <h2>Story Bible</h2>
        <span>世界规则与作者意图</span>
      </div>
      <div class="form-grid">
        <label>
          <span>题材</span>
          <input v-model="storyBibleForm.genre" />
        </label>
        <label>
          <span>基调</span>
          <input v-model="storyBibleForm.tone" />
        </label>
        <label class="full">
          <span>世界规则</span>
          <textarea v-model="storyBibleForm.world_rules" rows="4" />
        </label>
        <label class="full">
          <span>力量体系</span>
          <textarea v-model="storyBibleForm.power_system" rows="4" />
        </label>
        <label class="full">
          <span>禁忌规则</span>
          <textarea v-model="storyBibleForm.forbidden_rules" rows="3" />
        </label>
        <label class="full">
          <span>核心设定</span>
          <textarea v-model="storyBibleForm.core_setting" rows="3" />
        </label>
        <label class="full">
          <span>作者意图</span>
          <textarea v-model="storyBibleForm.author_intent" rows="3" />
        </label>
      </div>
      <div class="actions">
        <button :disabled="busy" @click="saveStoryBible">保存 Story Bible</button>
      </div>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>角色管理</h2>
          <span>{{ currentDetail.characters.length }} 个角色</span>
        </div>
        <div class="form-grid">
          <label>
            <span>姓名</span>
            <input v-model="characterForm.name" />
          </label>
          <label>
            <span>角色定位</span>
            <input v-model="characterForm.role" />
          </label>
          <label>
            <span>境界</span>
            <input v-model="characterForm.realm" />
          </label>
          <label class="full">
            <span>性格</span>
            <textarea v-model="characterForm.personality" rows="3" />
          </label>
          <label class="full">
            <span>核心动机</span>
            <textarea v-model="characterForm.core_motivation" rows="2" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="addCharacter">添加角色</button>
        </div>
        <div class="stack compact">
          <div v-for="character in currentDetail.characters" :key="character.id" class="item-card">
            <h3>{{ character.name }}</h3>
            <p>{{ character.role }} / {{ character.realm }}</p>
            <p>{{ character.core_motivation }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>事件管理</h2>
          <span>{{ currentDetail.events.length }} 条事件</span>
        </div>
        <div class="form-grid">
          <label>
            <span>章节号</span>
            <input v-model.number="eventForm.chapter_number" type="number" />
          </label>
          <label>
            <span>类型</span>
            <input v-model="eventForm.event_type" />
          </label>
          <label>
            <span>地点</span>
            <input v-model="eventForm.location" />
          </label>
          <label class="full">
            <span>事件摘要</span>
            <textarea v-model="eventForm.summary" rows="3" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="addEvent">添加事件</button>
        </div>
        <div class="stack compact">
          <div v-for="event in currentDetail.events" :key="event.id" class="item-card">
            <h3>第 {{ event.chapter_number }} 章</h3>
            <p>{{ event.summary }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>章节规划</h2>
          <span>{{ currentDetail.chapter_plans.length }} 份规划</span>
        </div>
        <div class="form-grid">
          <label>
            <span>章节号</span>
            <input v-model.number="chapterPlanForm.chapter_number" type="number" />
          </label>
          <label class="full">
            <span>章节目标</span>
            <textarea v-model="chapterPlanForm.goal" rows="2" />
          </label>
          <label class="full">
            <span>核心冲突</span>
            <textarea v-model="chapterPlanForm.conflict" rows="2" />
          </label>
          <label class="full">
            <span>结尾钩子</span>
            <textarea v-model="chapterPlanForm.hook" rows="2" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="addChapterPlan">生成章节规划</button>
        </div>
        <div class="stack compact">
          <div v-for="plan in currentDetail.chapter_plans" :key="plan.id" class="item-card">
            <h3>第 {{ plan.chapter_number }} 章</h3>
            <p>{{ plan.goal }}</p>
            <p>来源：{{ plan.source ?? 'manual' }} {{ plan.patch_id ? `/ ${plan.patch_id}` : '' }}</p>
            <ul class="mini-list">
              <li v-for="beat in plan.beats" :key="beat">{{ beat }}</li>
            </ul>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>章节生成</h2>
          <span>{{ currentDetail.chapters.length }} 份草稿</span>
        </div>
        <div class="form-grid">
          <label>
            <span>章节号</span>
            <input v-model.number="writingForm.chapter_number" type="number" />
          </label>
          <label>
            <span>Writer 模式</span>
            <select v-model="writingForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label class="full">
            <span>写作基调</span>
            <input v-model="writingForm.tone" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="loadContextPreview">预览上下文包</button>
          <button :disabled="busy" @click="writeChapter">生成章节草稿</button>
        </div>
        <div class="stack compact">
          <div v-for="chapter in currentDetail.chapters" :key="chapter.id" class="item-card">
            <h3>{{ chapter.title }}</h3>
            <p>
              第 {{ chapter.chapter_number }} 章 / rev {{ chapter.revision_number }} / 来源
              {{ chapter.source }} / {{ chapter.is_current ? 'current' : 'history' }}
            </p>
            <p>{{ chapter.summary }}</p>
            <details>
              <summary>查看正文</summary>
              <pre>{{ chapter.content }}</pre>
            </details>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>调度控制台</h2>
          <span>{{ activeSchedulerTask?.status ?? '未创建任务' }}</span>
        </div>
        <div class="form-grid">
          <label>
            <span>任务模式</span>
            <select v-model="schedulerForm.mode">
              <option value="write">write</option>
              <option value="recovery">recovery</option>
            </select>
          </label>
          <label>
            <span>起始章节</span>
            <input v-model.number="schedulerForm.start_chapter" type="number" />
          </label>
          <label>
            <span>结束章节</span>
            <input v-model.number="schedulerForm.end_chapter" type="number" />
          </label>
          <label>
            <span>Writer 模式</span>
            <select v-model="schedulerForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label>
            <span>最大重试</span>
            <input v-model.number="schedulerForm.max_retries" type="number" min="0" />
          </label>
          <label v-if="schedulerForm.mode === 'recovery'">
            <span>恢复补丁</span>
            <select v-model="schedulerForm.patch_id">
              <option value="">请选择补丁</option>
              <option
                v-for="patch in currentDetail.retcon_patches.slice().reverse()"
                :key="patch.id"
                :value="patch.id"
              >
                {{ patch.id }} / rerun-from {{ patch.recommended_rerun_from }}
              </option>
            </select>
          </label>
          <label class="full">
            <span>基调</span>
            <input v-model="schedulerForm.tone" />
          </label>
        </div>
        <div class="actions wrap-actions">
          <button :disabled="busy" @click="createSchedulerTask">创建调度任务</button>
          <button :disabled="busy || !activeSchedulerTask" @click="controlSchedulerTask('step')">
            单步推进
          </button>
          <button :disabled="busy || !activeSchedulerTask" @click="runSchedulerTask">
            运行到完成
          </button>
          <button :disabled="busy || !activeSchedulerTask" @click="controlSchedulerTask('pause')">
            暂停
          </button>
          <button :disabled="busy || !activeSchedulerTask" @click="controlSchedulerTask('resume')">
            恢复
          </button>
          <button :disabled="busy || !activeSchedulerTask" @click="controlSchedulerTask('retry')">
            重试
          </button>
        </div>
        <div v-if="activeSchedulerTask" class="stack compact">
          <div class="item-card">
            <h3>{{ activeSchedulerTask.id }}</h3>
            <p>状态：{{ activeSchedulerTask.status }} / stage：{{ activeSchedulerTask.stage }}</p>
            <p>模式：{{ activeSchedulerTask.mode }} {{ activeSchedulerTask.patch_id ? `/ ${activeSchedulerTask.patch_id}` : '' }}</p>
            <p>队列 Job：{{ activeSchedulerTask.active_queue_job_id || '无' }}</p>
            <p>下一章：{{ activeSchedulerTask.next_chapter }}</p>
            <p>已完成：{{ activeSchedulerTask.completed_chapters.join(', ') || '无' }}</p>
            <p>重试：{{ activeSchedulerTask.retry_count }} / {{ activeSchedulerTask.max_retries }}</p>
            <p>连续失败：{{ activeSchedulerTask.consecutive_failures }}</p>
            <p>
              治理：{{ activeSchedulerTask.governance_status }} /
              {{ activeSchedulerTask.governance_reason || '当前无阻断原因' }}
            </p>
            <p>
              预算：{{ activeSchedulerTask.governance_cost_used_usd }} /
              {{ activeSchedulerTask.governance_cost_limit_usd }} USD
            </p>
            <p>{{ activeSchedulerTask.stage_message || '暂无阶段说明' }}</p>
            <p v-if="activeSchedulerTask.last_error">错误：{{ activeSchedulerTask.last_error }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>执行队列</h2>
          <span>{{ currentDetail.queue_jobs.length }} 个 job</span>
        </div>
        <div class="stack compact">
          <div
            v-for="job in currentDetail.queue_jobs.slice().reverse().slice(0, 16)"
            :key="job.id"
            class="item-card"
          >
            <h3>{{ job.id }}</h3>
            <p>任务：{{ job.task_id }}</p>
            <p>状态：{{ job.status }} / worker={{ job.worker_id || '无' }}</p>
            <p>尝试：{{ job.attempt_count }} / {{ job.max_attempts }}</p>
            <p>可执行时间：{{ job.available_at }}</p>
            <p>租约到期：{{ job.lease_expires_at || '无' }}</p>
            <p>{{ job.payload_summary || '无 payload 说明' }}</p>
            <p>{{ job.result_summary || job.last_error || '尚无结果' }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>批量章节执行器</h2>
          <span>连续推进多章</span>
        </div>
        <div class="form-grid">
          <label>
            <span>起始章节</span>
            <input v-model.number="batchForm.start_chapter" type="number" />
          </label>
          <label>
            <span>结束章节</span>
            <input v-model.number="batchForm.end_chapter" type="number" />
          </label>
          <label>
            <span>Writer 模式</span>
            <select v-model="batchForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label>
            <span>基调</span>
            <input v-model="batchForm.tone" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="writeBatch">连续生成多章</button>
        </div>
        <div v-if="lastBatchResult" class="stack compact">
          <div class="item-card">
            <h3>最近批量任务</h3>
            <p>{{ lastBatchResult.message }}</p>
            <p>完成章节：{{ lastBatchResult.completed_chapters.join(', ') || '无' }}</p>
          </div>
        </div>
      </article>

    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>回滚控制台</h2>
          <span>按章节恢复状态</span>
        </div>
        <div class="form-grid">
          <label>
            <span>目标章节</span>
            <input v-model.number="rollbackForm.target_chapter_number" type="number" />
          </label>
          <label class="full">
            <span>回滚原因</span>
            <textarea v-model="rollbackForm.reason" rows="3" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="rollbackProject">执行回滚</button>
        </div>
        <div v-if="lastRollbackResult" class="stack compact">
          <div class="item-card">
            <h3>最近回滚结果</h3>
            <p>{{ lastRollbackResult.message }}</p>
            <p>删除章节：{{ lastRollbackResult.removed_chapters }}</p>
            <p>删除事件：{{ lastRollbackResult.removed_events }}</p>
            <p>删除快照：{{ lastRollbackResult.removed_snapshots }}</p>
            <p>删除版本：{{ lastRollbackResult.removed_versions }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>Retcon Patch</h2>
          <span>{{ currentDetail.retcon_patches.length }} 个补丁</span>
        </div>
        <div class="form-grid">
          <label>
            <span>Patch</span>
            <select v-model="rerunForm.patch_id">
              <option value="">不绑定 patch</option>
              <option
                v-for="patch in currentDetail.retcon_patches.slice().reverse()"
                :key="patch.id"
                :value="patch.id"
              >
                {{ patch.id }} / ch{{ patch.target_chapter_number }}
              </option>
            </select>
          </label>
          <label>
            <span>重跑起点</span>
            <input v-model.number="rerunForm.from_chapter" type="number" />
          </label>
          <label>
            <span>重跑终点</span>
            <input v-model.number="rerunForm.end_chapter" type="number" />
          </label>
          <label>
            <span>Writer 模式</span>
            <select v-model="rerunForm.writer_mode">
              <option value="auto">auto</option>
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>
          <label class="full">
            <span>基调</span>
            <input v-model="rerunForm.tone" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="rerunProject">执行补丁重跑</button>
        </div>
        <div v-if="lastRerunResult" class="stack compact">
          <div class="item-card">
            <h3>最近重跑结果</h3>
            <p>{{ lastRerunResult.message }}</p>
            <p>完成章节：{{ lastRerunResult.completed_chapters.join(', ') || '无' }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>补丁列表</h2>
          <span>回滚后的失效传播</span>
        </div>
        <div class="stack compact">
          <div
            v-for="patch in currentDetail.retcon_patches.slice().reverse()"
            :key="patch.id"
            class="item-card"
          >
            <h3>{{ patch.id }}</h3>
            <p>目标章节：{{ patch.target_chapter_number }}</p>
            <p>原因：{{ patch.reason }}</p>
            <p>状态：{{ patch.status }}</p>
            <p>建议从第 {{ patch.recommended_rerun_from }} 章开始重跑</p>
            <p>影响章节：{{ patch.affected_chapter_numbers.join(', ') || '无' }}</p>
            <p>失效规划：{{ patch.invalidated_plan_ids.join(', ') || '无' }}</p>
            <p>需重算 hooks：{{ patch.requires_recompute_hooks.join('；') || '无' }}</p>
            <p>状态层回滚：{{ patch.requires_state_rollback ? '是' : '否' }}</p>
            <p>重规划结果：{{ patch.replanned_plan_ids.join(', ') || '尚未重规划' }}</p>
            <p>最近重规划：{{ patch.last_replanned_at || '无' }}</p>
            <ul class="mini-list">
              <li v-for="item in patch.impact_summary" :key="item">{{ item }}</li>
            </ul>
            <ul v-if="patch.replan_summary.length" class="mini-list">
              <li v-for="item in patch.replan_summary" :key="item">{{ item }}</li>
            </ul>
            <div v-if="patch.status !== 'rerun_completed'" class="actions">
              <button :disabled="busy" @click="replanPatch(patch.id)">自动重规划</button>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>运行与上下文</h2>
          <span>{{ currentDetail.latest_run?.status ?? '暂无运行' }}</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>最近运行</h3>
            <p>{{ currentDetail.latest_run?.message ?? '尚未开始写作任务' }}</p>
            <p>
              模式：
              {{ currentDetail.latest_run?.writer_mode ?? 'n/a' }}
            </p>
          </div>
          <div v-if="currentContext" class="item-card">
            <h3>上下文包预览</h3>
            <p>章节：第 {{ currentContext.chapter_number }} 章</p>
            <p>{{ currentContext.context_summary }}</p>
            <p>活跃角色：{{ currentContext.active_characters.length }}</p>
            <p>最近事件：{{ currentContext.recent_events.length }}</p>
            <p>角色状态：{{ currentContext.recent_character_states.length }}</p>
            <p>最近快照：{{ currentContext.recent_snapshots.length }}</p>
            <p>长期记忆命中：{{ currentContext.long_term_memories.length }}</p>
            <p>关系边：{{ currentContext.relationship_edges.length }}</p>
            <p>时间线节点：{{ currentContext.timeline_nodes.length }}</p>
            <p>时间线约束：{{ currentContext.active_timeline_constraints.length }}</p>
            <p>开放伏笔：{{ currentContext.open_hooks.length }}</p>
            <p>开放补丁：{{ currentContext.open_retcon_patches.length }}</p>
            <ul class="mini-list">
              <li
                v-for="priority in currentContext.retrieval_priorities"
                :key="priority"
              >
                {{ priority }}
              </li>
            </ul>
            <details>
              <summary>查看分层摘要与预算</summary>
              <pre>
Story Bible:
{{ currentContext.story_bible_summary }}

Events:
{{ currentContext.event_summary }}

Character States:
{{ currentContext.character_state_summary }}

Retcon Patches:
{{ currentContext.patch_summary }}

Long-Term Memory:
{{ currentContext.memory_summary }}

Relationships:
{{ currentContext.relationship_summary }}

Timeline:
{{ currentContext.timeline_summary }}

Open Hooks:
{{ currentContext.open_hooks.map((item) => `${item.status} / ${item.content}`).join('\n') || '暂无' }}

Token Budget:
{{ JSON.stringify(currentContext.token_budget, null, 2) }}
              </pre>
            </details>
            <details>
              <summary>查看检索诊断</summary>
              <div class="stack compact">
                <div class="item-card">
                  <h3>选择理由</h3>
                  <ul class="mini-list">
                    <li v-for="reason in currentContext.selection_reasoning" :key="reason">
                      {{ reason }}
                    </li>
                  </ul>
                </div>
                <div v-if="currentContext.long_term_memories.length" class="item-card">
                  <h3>长期记忆命中</h3>
                  <ul class="mini-list">
                    <li
                      v-for="memory in currentContext.long_term_memories"
                      :key="memory.record_id"
                    >
                      第{{ memory.chapter_number }}章 / {{ memory.source_type }} /
                      score={{ memory.retrieval_score }} / {{ memory.content }}
                    </li>
                  </ul>
                </div>
                <div v-if="currentContext.relationship_edges.length" class="item-card">
                  <h3>关系边命中</h3>
                  <ul class="mini-list">
                    <li v-for="edge in currentContext.relationship_edges" :key="edge.id">
                      第{{ edge.chapter_number }}章 / {{ edge.source_character_id }} -> {{ edge.target_character_id }} /
                      {{ edge.relation_type }} / {{ edge.change_type }} / current={{ edge.is_current ? 'yes' : 'no' }} /
                      {{ edge.evidence }}
                    </li>
                  </ul>
                </div>
                <div v-if="currentContext.timeline_nodes.length || currentContext.active_timeline_constraints.length" class="item-card">
                  <h3>时间线命中</h3>
                  <ul class="mini-list">
                    <li v-for="node in currentContext.timeline_nodes" :key="node.id">
                      第{{ node.chapter_number }}章 / {{ node.time_marker }} / {{ node.label }}
                    </li>
                    <li v-for="constraint in currentContext.active_timeline_constraints" :key="constraint.id">
                      约束 / 第{{ constraint.chapter_number }}章 / {{ constraint.status }} /
                      {{ constraint.is_current ? 'current' : 'history' }} /
                      {{ constraint.previous_constraint_id ? `承接 ${constraint.previous_constraint_id}` : '链路起点' }} /
                      {{ constraint.description }}
                    </li>
                  </ul>
                </div>
                <div class="item-card" v-for="(items, group) in currentContext.retrieval_diagnostics" :key="group">
                  <h3>{{ group }}</h3>
                  <ul class="mini-list">
                    <li v-for="item in items" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>
            </details>
            <ul class="mini-list">
              <li v-for="rule in currentContext.hard_constraints" :key="rule">{{ rule }}</li>
            </ul>
          </div>
          <div v-else class="item-card">
            <h3>上下文包预览</h3>
            <p>点击“预览上下文包”后可查看当前章节输入到 Writer 的核心约束。</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>写回结果</h2>
          <span>{{ currentDetail.extracted_updates.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="update in currentDetail.extracted_updates.slice().reverse()"
            :key="update.id"
            class="item-card"
          >
            <h3>第 {{ update.chapter_number }} 章抽取</h3>
            <p>{{ update.summary }}</p>
            <p>{{ update.timeline_advance }}</p>
            <p>地点：{{ update.locations.join('、') || '无' }}</p>
            <p>情绪：{{ update.emotions.join('、') || '无' }}</p>
            <p>目标：{{ update.goals.join('、') || '无' }}</p>
            <p>关系：{{ update.relationship_signals.join('、') || '无' }}</p>
            <p>新增伏笔：{{ update.new_hooks.join('；') || '无' }}</p>
            <p>激活伏笔：{{ update.active_hooks.join('；') || '无' }}</p>
            <p>回收伏笔：{{ update.resolved_hooks.join('；') || '无' }}</p>
            <p>废弃伏笔：{{ update.abandoned_hooks.join('；') || '无' }}</p>
            <ul class="mini-list">
              <li v-for="hook in update.hook_changes" :key="hook">{{ hook }}</li>
            </ul>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>质量评审</h2>
          <span>{{ currentDetail.reviews.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="review in currentDetail.reviews.slice().reverse()"
            :key="review.id"
            class="item-card"
          >
            <h3>
              第 {{ review.chapter_number }} 章 / 自动 {{ review.status }} / 人工
              {{ review.human_decision_status }}
            </h3>
            <p>修订态：{{ isReviewCurrentRevision(review) ? 'current' : 'stale' }}</p>
            <p>{{ review.decision_reason }}</p>
            <p>连续性报告：{{ review.continuity_report_id || '无' }}</p>
            <p>读者评议：{{ review.reader_council_report_id || '无' }}</p>
            <p>
              逻辑 {{ review.logic_score }} / 连续性 {{ review.continuity_score }} / 人物
              {{ review.character_score }} / 钩子 {{ review.hook_score }}
            </p>
            <p>总评：{{ review.overall_score }}</p>
            <p v-if="review.human_decision_note">人工备注：{{ review.human_decision_note }}</p>
            <p v-if="!isReviewCurrentRevision(review)">该评审对应旧版本章节，已禁止继续审批或重写。</p>
            <ul class="mini-list">
              <li v-for="finding in review.findings" :key="finding">{{ finding }}</li>
            </ul>
            <div
              v-if="
                review.status === 'review_required' &&
                review.human_decision_status === 'pending' &&
                isReviewCurrentRevision(review)
              "
              class="actions wrap-actions"
            >
              <button :disabled="busy" @click="rewriteChapter(review.id)">自动重写</button>
              <button :disabled="busy" @click="decideReview(review.id, 'approve')">人工通过</button>
              <button :disabled="busy" @click="decideReview(review.id, 'reject')">人工驳回</button>
            </div>
            <details>
              <summary>重写建议</summary>
              <ul class="mini-list">
                <li v-for="item in review.rewrite_suggestions" :key="item">{{ item }}</li>
              </ul>
            </details>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>Continuity Board</h2>
          <span>{{ currentDetail.continuity_reports.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="report in currentDetail.continuity_reports.slice().reverse()"
            :key="report.id"
            class="item-card"
          >
            <h3>第 {{ report.chapter_number }} 章 / {{ report.status }}</h3>
            <p>修订态：{{ isContinuityReportCurrentRevision(report) ? 'current' : 'stale' }}</p>
            <p v-if="!isContinuityReportCurrentRevision(report)">该连续性报告对应旧版本章节，仅保留作历史审计参考。</p>
            <p>风险：{{ report.overall_risk }}</p>
            <p>Judge：{{ report.judges_triggered.join(' / ') || '无' }}</p>
            <p>{{ report.summary }}</p>
            <details v-if="report.issues.length">
              <summary>查看一致性问题</summary>
              <div class="stack compact">
                <div
                  v-for="issue in report.issues"
                  :key="`${report.id}-${issue.judge}-${issue.title}`"
                  class="item-card"
                >
                  <p>{{ issue.judge }} / {{ issue.severity }} / {{ issue.title }}</p>
                  <p>{{ issue.detail }}</p>
                  <p>证据：{{ issue.evidence.join('；') || '无' }}</p>
                  <p>建议：{{ issue.recommendation || '无' }}</p>
                </div>
              </div>
            </details>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>角色关系图谱</h2>
          <span>{{ currentDetail.relationship_edges.length }} 条边</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>当前关系态</h3>
            <ul class="mini-list">
              <li
                v-for="edge in currentDetail.relationship_edges.filter((item) => item.is_current).slice().reverse().slice(0, 10)"
                :key="`current-${edge.id}`"
              >
                {{ edge.source_character_id }} -> {{ edge.target_character_id }} / {{ edge.relation_type }} /
                {{ edge.change_type }} / 强度 {{ edge.intensity }}
              </li>
            </ul>
          </div>
          <div
            v-for="edge in currentDetail.relationship_edges.slice().reverse().slice(0, 20)"
            :key="edge.id"
            class="item-card"
          >
            <h3>{{ edge.source_character_id }} -> {{ edge.target_character_id }}</h3>
            <p>
              第 {{ edge.chapter_number }} 章 / {{ edge.relation_type }} / {{ edge.direction }} /
              {{ edge.change_type }} / {{ edge.is_current ? 'current' : 'history' }}
            </p>
            <p>强度：{{ edge.intensity }}</p>
            <p>前序边：{{ edge.previous_edge_id || '无' }}</p>
            <p>{{ edge.evidence }}</p>
            <p>{{ edge.note || '无备注' }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>时间线约束</h2>
          <span>{{ currentDetail.timeline_constraints.length }} 条</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>约束演化概览</h3>
            <p>
              当前态：
              {{ currentDetail.timeline_constraints.filter((item) => item.is_current).length }} /
              已闭合：{{ currentDetail.timeline_constraints.filter((item) => item.status === 'resolved').length }}
            </p>
            <p>
              活跃风险：
              {{
                currentDetail.timeline_constraints.filter(
                  (item) => item.is_current && ['warning', 'violated'].includes(item.status),
                ).length
              }}
              / 历史链：
              {{ currentDetail.timeline_constraints.filter((item) => item.previous_constraint_id).length }}
            </p>
          </div>
          <div
            v-for="node in currentDetail.timeline_nodes.slice().reverse().slice(0, 12)"
            :key="node.id"
            class="item-card"
          >
            <h3>{{ node.time_marker }} / 第 {{ node.chapter_number }} 章</h3>
            <p>{{ node.label }}</p>
            <p>上一地点：{{ node.previous_location || '无' }}</p>
            <p>地点：{{ node.location || '未知' }}</p>
            <p>参与者：{{ node.participants.join('、') || '无' }}</p>
          </div>
          <div
            v-for="constraint in currentDetail.timeline_constraints.slice().reverse().slice(0, 12)"
            :key="constraint.id"
            class="item-card"
          >
            <h3>{{ constraint.constraint_type }} / {{ constraint.status }} / {{ constraint.severity }}</h3>
            <p>第 {{ constraint.chapter_number }} 章</p>
            <p>{{ timelineConstraintStage(constraint) }} / {{ timelineConstraintChain(constraint) }}</p>
            <p>相关节点：{{ constraint.related_node_id || '无' }} / 角色：{{ constraint.related_character_id || '无' }}</p>
            <p>演化键：{{ constraint.evolution_key || '无' }}</p>
            <p>{{ constraint.description }}</p>
            <p>证据：{{ constraint.evidence.join('；') || '无' }}</p>
            <p>建议：{{ constraint.recommendation || '无' }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>Reader Council</h2>
          <span>{{ currentDetail.reader_council_reports.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="report in currentDetail.reader_council_reports.slice().reverse()"
            :key="report.id"
            class="item-card"
          >
            <h3>第 {{ report.chapter_number }} 章 / {{ report.status }}</h3>
            <p>修订态：{{ isReaderCouncilReportCurrentRevision(report) ? 'current' : 'stale' }}</p>
            <p v-if="!isReaderCouncilReportCurrentRevision(report)">该读者反馈对应旧版本章节，仅保留作历史审计参考。</p>
            <p>
              综合 {{ report.overall_score }} / 追读 {{ report.chase_score }} / 回报
              {{ report.payoff_score }} / 节奏 {{ report.pace_score }}
            </p>
            <p>{{ report.summary }}</p>
            <ul class="mini-list">
              <li v-for="item in report.highlights" :key="item">{{ item }}</li>
            </ul>
            <details>
              <summary>查看读者视角反馈</summary>
              <div class="stack compact">
                <div
                  v-for="feedback in report.persona_feedbacks"
                  :key="`${report.id}-${feedback.persona}`"
                  class="item-card"
                >
                  <p>{{ feedback.persona }} / 代入 {{ feedback.engagement_score }} / 钩子 {{ feedback.hook_expectation_score }} / 回报 {{ feedback.payoff_score }}</p>
                  <p>{{ feedback.summary }}</p>
                  <p>亮点：{{ feedback.likes.join('；') || '无' }}</p>
                  <p>担忧：{{ feedback.concerns.join('；') || '无' }}</p>
                  <p>建议：{{ feedback.suggestions.join('；') || '无' }}</p>
                </div>
              </div>
            </details>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>Foreshadow Tracker</h2>
          <span>{{ currentDetail.hook_records.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="hook in currentDetail.hook_records.slice().reverse()"
            :key="hook.id"
            class="item-card"
          >
            <h3>{{ hook.content }}</h3>
            <p>
              状态：{{ hook.status }} / 创建章：{{ hook.created_in_chapter }} / 最近触达：{{ hook.last_touched_chapter }}
            </p>
            <p>预期回收：{{ hook.expected_resolution_arc || '未指定' }}</p>
            <p>实际回收章：{{ hook.resolution_chapter ?? '未回收' }}</p>
            <p>{{ hook.note || '无备注' }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>Hook 状态变更</h2>
          <span>{{ currentDetail.hook_state_changes.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="change in currentDetail.hook_state_changes.slice().reverse()"
            :key="change.id"
            class="item-card"
          >
            <h3>{{ change.action }} / 第 {{ change.chapter_number }} 章</h3>
            <p>{{ change.content }}</p>
            <p>预期回收：{{ change.expected_resolution_arc || '未指定' }}</p>
            <p>{{ change.note || '无备注' }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>任务运行历史</h2>
          <span>{{ currentDetail.task_runs.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="task in currentDetail.task_runs.slice().reverse()"
            :key="task.id"
            class="item-card"
          >
            <h3>{{ task.task_type }}</h3>
            <p>状态：{{ task.status }}</p>
            <p>{{ task.payload_summary }}</p>
            <p>{{ task.result_summary }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>章节审核状态</h2>
          <span>{{ currentDetail.chapters.length }} 章</span>
        </div>
        <div class="stack compact">
          <div
            v-for="chapter in currentDetail.chapters.slice().reverse()"
            :key="chapter.id"
            class="item-card"
          >
            <h3>{{ chapter.title }}</h3>
            <p>
              第 {{ chapter.chapter_number }} 章 / rev {{ chapter.revision_number }} / 状态：{{ chapter.status }}
            </p>
            <p>{{ chapter.summary }}</p>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>运行治理策略</h2>
          <span>{{ currentDetail.governance_policy?.enabled ? 'enabled' : 'disabled' }}</span>
        </div>
        <div class="form-grid">
          <label>
            <span>启用治理</span>
            <input v-model="governanceForm.enabled" type="checkbox" />
          </label>
          <label>
            <span>连续失败阈值</span>
            <input v-model.number="governanceForm.max_consecutive_failures" type="number" min="1" />
          </label>
          <label>
            <span>总预算 USD</span>
            <input v-model.number="governanceForm.max_total_estimated_cost_usd" type="number" min="0" step="0.1" />
          </label>
          <label>
            <span>单章预算 USD</span>
            <input v-model.number="governanceForm.max_chapter_cost_usd" type="number" min="0" step="0.1" />
          </label>
          <label>
            <span>冲突分阈值</span>
            <input v-model.number="governanceForm.max_conflict_score" type="number" min="0" step="0.5" />
          </label>
          <label>
            <span>延续时间线风险阈值</span>
            <input v-model.number="governanceForm.max_continuing_timeline_risks" type="number" min="1" />
          </label>
          <label>
            <span>最小读者分</span>
            <input v-model.number="governanceForm.min_reader_score" type="number" min="0" max="10" step="0.5" />
          </label>
          <label>
            <span>最小评审分</span>
            <input v-model.number="governanceForm.min_review_score" type="number" min="0" max="10" step="0.5" />
          </label>
          <label>
            <span>评审待定即暂停</span>
            <input v-model="governanceForm.pause_on_review_required" type="checkbox" />
          </label>
          <label>
            <span>读者弱反馈即暂停</span>
            <input v-model="governanceForm.pause_on_reader_weak" type="checkbox" />
          </label>
          <label>
            <span>状态异常即暂停</span>
            <input v-model="governanceForm.pause_on_state_anomaly" type="checkbox" />
          </label>
          <label>
            <span>延续时间线风险即暂停</span>
            <input v-model="governanceForm.pause_on_continuing_timeline_risk" type="checkbox" />
          </label>
          <label class="full">
            <span>状态异常关键词</span>
            <textarea v-model="governanceForm.state_anomaly_keywords" rows="4" />
          </label>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="saveGovernancePolicy">保存治理策略</button>
        </div>
        <p class="muted">
          用于控制预算耗尽、连续失败、连续性冲突和关键状态异常时的自动停机行为。
        </p>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>治理事件流</h2>
          <span>{{ currentDetail.governance_events.length }} 条</span>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>当前预算</h3>
            <p>
              {{ currentDetail.metrics_summary?.total_estimated_cost_usd ?? 0 }} /
              {{ currentDetail.governance_policy?.max_total_estimated_cost_usd ?? 0 }} USD
            </p>
            <p>最近告警：{{ currentDetail.metrics_summary?.latest_warnings.join('；') || '暂无' }}</p>
          </div>
          <div
            v-for="event in currentDetail.governance_events.slice().reverse()"
            :key="event.id"
            class="item-card"
          >
            <h3>{{ event.signal }} / {{ event.action }} / {{ event.level }}</h3>
            <p>{{ event.summary }}</p>
            <p>任务：{{ event.task_id }} / 章节：{{ event.chapter_number ?? 'n/a' }}</p>
            <p>{{ event.created_at }}</p>
            <ul class="mini-list">
              <li v-for="detail in event.details" :key="`${event.id}-${detail}`">{{ detail }}</li>
            </ul>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>长期记忆索引</h2>
          <span>{{ currentDetail.long_term_memories.length }} 条</span>
        </div>
        <div class="actions">
          <button :disabled="busy" @click="rebuildMemories">重建长期记忆</button>
        </div>
        <div class="stack compact">
          <div class="item-card">
            <h3>索引说明</h3>
            <p>当前会把章节、事件、角色状态、快照、伏笔、补丁和评审结果沉淀为统一记忆条目。</p>
            <p>
              检索后端：{{ currentDetail.memory_index_status?.backend ?? 'unknown' }} /
              {{ currentDetail.memory_index_status?.backend_status ?? 'unavailable' }}
            </p>
            <p>索引就绪：{{ currentDetail.memory_index_status?.ready ? 'yes' : 'no' }}</p>
            <p>已索引记录：{{ currentDetail.memory_index_status?.indexed_records ?? 0 }}</p>
            <p>最近建索引：{{ currentDetail.memory_index_status?.last_indexed_at || '无' }}</p>
            <p>集合：{{ currentDetail.memory_index_status?.collection_name || '无' }}</p>
            <p>{{ currentDetail.memory_index_status?.detail || '尚未生成检索状态说明。' }}</p>
          </div>
          <div
            v-for="memory in currentDetail.long_term_memories.slice().reverse().slice(0, 20)"
            :key="memory.id"
            class="item-card"
          >
            <h3>{{ memory.title || memory.source_type }}</h3>
            <p>
              第 {{ memory.chapter_number }} 章 / {{ memory.source_type }} / {{ memory.memory_type }}
            </p>
            <p>重要度：{{ memory.importance_score }}</p>
            <p>Term 数：{{ memory.term_count }}</p>
            <p>{{ memory.content }}</p>
            <p>关键词：{{ memory.keywords.join('、') || '无' }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>召回轨迹</h2>
          <span>{{ currentDetail.memory_retrieval_traces.length }} 条</span>
        </div>
        <div class="stack compact">
          <div
            v-for="trace in currentDetail.memory_retrieval_traces.slice().reverse().slice(0, 12)"
            :key="trace.id"
            class="item-card"
          >
            <h3>第 {{ trace.chapter_number }} 章 / {{ trace.id }}</h3>
            <p>后端：{{ trace.retrieval_backend }} / 状态：{{ trace.backend_status }}</p>
            <p>Query Terms：{{ trace.query_terms.join('、') || '无' }}</p>
            <p>命中记录：{{ trace.selected_record_ids.join(', ') || '无' }}</p>
            <p>{{ trace.created_at }}</p>
            <ul class="mini-list">
              <li v-for="hit in trace.hits.slice(0, 5)" :key="`${trace.id}-${hit.record_id}`">
                第{{ hit.chapter_number }}章 / {{ hit.source_type }} / {{ hit.retrieval_backend }} /
                score={{ hit.retrieval_score }} / vector={{ hit.vector_score }} / lexical={{ hit.lexical_score }} /
                {{ hit.matched_terms.join('、') || '无命中词' }}
              </li>
            </ul>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>运行评估总览</h2>
          <span>批量执行与停机信号</span>
        </div>
        <div v-if="currentDetail.ops_summary" class="stats-grid">
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.chapter_count }}</strong>
            <span>当前章节数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.last_completed_chapter }}</strong>
            <span>最新完成章节</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.review_required_chapter_count }}</strong>
            <span>待审核章节</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.total_scheduler_tasks }}</strong>
            <span>调度任务总数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.queued_tasks }}</strong>
            <span>排队任务</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.running_tasks }}</strong>
            <span>运行任务</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.blocked_tasks }}</strong>
            <span>治理阻断任务</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.queue_pending_jobs }}</strong>
            <span>待认领 Job</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.queue_leased_jobs }}</strong>
            <span>租约中 Job</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.budget_limit_usd > 0 ? `${Math.round(currentDetail.ops_summary.budget_used_ratio * 100)}%` : '0%' }}</strong>
            <span>预算使用率</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.average_quality_score_last_10 }}</strong>
            <span>最近 10 章质量</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.average_reader_score_last_10 }}</strong>
            <span>最近 10 章读者分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.active_timeline_risk_count }}</strong>
            <span>活跃时间线风险</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.continuing_timeline_risk_count }}</strong>
            <span>延续型风险</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.resolved_timeline_risk_count }}</strong>
            <span>已闭合时间线风险</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.state_graph_issue_count }}</strong>
            <span>状态图谱问题数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.critical_state_graph_issue_count }}</strong>
            <span>关键断链问题</span>
          </div>
          <div class="stat-card">
            <strong>
              {{
                currentDetail.ops_summary.state_graph_recovery_plan
                  ? `${currentDetail.ops_summary.state_graph_recovery_plan.start_chapter || 'n/a'} -> ${currentDetail.ops_summary.state_graph_recovery_plan.end_chapter || 'n/a'}`
                  : '暂无'
              }}
            </strong>
            <span>建议 Recovery 窗口</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.pending_retcon_patch_count }}</strong>
            <span>开放补丁数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.replanned_retcon_patch_count }}</strong>
            <span>待 Rerun 补丁</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_readiness }}</strong>
            <span>LLM 就绪状态</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_writer_route }}</strong>
            <span>Auto 路由</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_last_diagnostic_status }}</strong>
            <span>最近诊断</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_last_preflight_status }}</strong>
            <span>最近 Preflight</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_recent_preflight_failures }}</strong>
            <span>近期 Preflight 失败</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_recent_fallback_runs }}</strong>
            <span>近期 Fallback</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_config_issue_count }}</strong>
            <span>配置风险桶</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_connectivity_issue_count }}</strong>
            <span>连通性风险桶</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_fallback_issue_count }}</strong>
            <span>Fallback 风险桶</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary.llm_preflight_issue_count }}</strong>
            <span>Preflight 风险桶</span>
          </div>
          <div class="stat-card full">
            <strong>活跃停机原因</strong>
            <span>{{ currentDetail.ops_summary.active_stop_reasons.join('；') || '暂无' }}</span>
          </div>
          <div class="stat-card full">
            <strong>近期关键事件</strong>
            <span>{{ currentDetail.ops_summary.recent_critical_events.join('；') || '暂无' }}</span>
          </div>
          <div class="stat-card full">
            <strong>补丁风险</strong>
            <span>{{ currentDetail.ops_summary.patch_alerts.join('；') || '暂无' }}</span>
          </div>
          <div class="stat-card full">
            <strong>时间线风险链</strong>
            <span>{{ currentDetail.ops_summary.timeline_risk_alerts.join('；') || '暂无' }}</span>
          </div>
          <div class="stat-card full">
            <strong>状态图谱巡检</strong>
            <span>{{ currentDetail.ops_summary.state_graph_alerts.join('；') || '暂无' }}</span>
          </div>
          <div
            v-if="currentDetail.ops_summary.state_graph_recovery_plan"
            class="stat-card full"
          >
            <strong>状态图谱批量恢复</strong>
            <span>
              {{ currentDetail.ops_summary.state_graph_recovery_plan.title }}；
              {{ currentDetail.ops_summary.state_graph_recovery_plan.detail }}
            </span>
            <span>
              聚焦：{{ currentDetail.ops_summary.state_graph_recovery_plan.focus_categories.join(' / ') || '暂无' }}；
              问题：{{ currentDetail.ops_summary.state_graph_recovery_plan.issue_count }} 条 /
              critical {{ currentDetail.ops_summary.state_graph_recovery_plan.critical_issue_count }} 条
            </span>
            <span>
              {{ currentDetail.ops_summary.state_graph_recovery_plan.summary_lines.join('；') || '暂无摘要' }}
            </span>
            <div
              v-if="currentDetail.ops_summary.state_graph_recovery_plan.can_create_scheduler_task"
              class="actions wrap-actions"
            >
              <button
                :disabled="busy"
                @click="applyStateGraphRecoveryPlan(currentDetail.ops_summary.state_graph_recovery_plan)"
              >
                载入批量恢复
              </button>
              <button
                :disabled="busy"
                @click="applyStateGraphRecoveryPlan(currentDetail.ops_summary.state_graph_recovery_plan, true)"
              >
                创建批量 recovery
              </button>
            </div>
          </div>
          <div class="stat-card full">
            <strong>LLM 告警</strong>
            <span>{{ currentDetail.ops_summary.llm_alerts.join('；') || '暂无' }}</span>
          </div>
          <div class="stat-card full">
            <strong>LLM 健康趋势</strong>
            <span>{{ currentDetail.ops_summary.llm_health_trend.join('；') || '暂无' }}</span>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>成本与质量</h2>
          <span>{{ currentDetail.metrics_summary?.chapter_count ?? 0 }} 章</span>
        </div>
        <div v-if="currentDetail.metrics_summary" class="stats-grid">
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.total_tokens_estimate }}</strong>
            <span>总 Token 估算</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.total_estimated_cost_usd }}</strong>
            <span>总成本估算 USD</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.average_quality_score }}</strong>
            <span>平均质量分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.average_extraction_score }}</strong>
            <span>平均抽取分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.average_hook_score }}</strong>
            <span>平均钩子分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.average_review_score }}</strong>
            <span>平均评审分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.average_reader_score }}</strong>
            <span>平均读者分</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.fallback_count }}</strong>
            <span>降级次数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.ops_summary?.llm_last_preflight_chapter ?? 0 }}</strong>
            <span>最近 Preflight 章节</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.open_hook_count }}</strong>
            <span>开放伏笔数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.resolved_hook_count }}</strong>
            <span>已回收伏笔数</span>
          </div>
          <div class="stat-card">
            <strong>{{ currentDetail.metrics_summary.hook_resolution_rate }}</strong>
            <span>伏笔回收率</span>
          </div>
          <div class="stat-card full">
            <strong>最近告警</strong>
            <span>
              {{ currentDetail.metrics_summary.latest_warnings.join('；') || '暂无' }}
            </span>
          </div>
          <div class="stat-card full">
            <strong>最近 LLM 探测时间</strong>
            <span>
              {{ currentDetail.ops_summary?.llm_last_diagnostic_at || currentDetail.ops_summary?.llm_last_preflight_at || '暂无' }}
            </span>
          </div>
          <div class="stat-card full">
            <strong>LLM 风险摘要</strong>
            <span>
              {{
                currentDetail.ops_summary
                  ? `config=${currentDetail.ops_summary.llm_config_issue_count}；connectivity=${currentDetail.ops_summary.llm_connectivity_issue_count}；fallback=${currentDetail.ops_summary.llm_fallback_issue_count}；preflight=${currentDetail.ops_summary.llm_preflight_issue_count}`
                  : '暂无'
              }}
            </span>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>状态图谱巡检</h2>
          <span>{{ currentDetail.state_graph_diagnostics.length }} 条</span>
        </div>
        <div class="stack compact">
          <div v-if="currentDetail.state_graph_recovery_plan" class="item-card">
            <h3>批量恢复计划</h3>
            <p>{{ currentDetail.state_graph_recovery_plan.title }}</p>
            <p>{{ currentDetail.state_graph_recovery_plan.detail }}</p>
            <p>
              问题：{{ currentDetail.state_graph_recovery_plan.issue_count }} 条 /
              critical：{{ currentDetail.state_graph_recovery_plan.critical_issue_count }} 条
            </p>
            <p>
              动作：{{ currentDetail.state_graph_recovery_plan.recommended_action }} /
              窗口：{{ currentDetail.state_graph_recovery_plan.start_chapter ?? 'n/a' }} ->
              {{ currentDetail.state_graph_recovery_plan.end_chapter ?? 'n/a' }}
            </p>
            <p>
              重点类别：{{ currentDetail.state_graph_recovery_plan.focus_categories.join(' / ') || '无' }}
            </p>
            <p>
              摘要：{{ currentDetail.state_graph_recovery_plan.summary_lines.join('；') || '无' }}
            </p>
            <div
              v-if="currentDetail.state_graph_recovery_plan.can_create_scheduler_task"
              class="actions wrap-actions"
            >
              <button
                :disabled="busy"
                @click="applyStateGraphRecoveryPlan(currentDetail.state_graph_recovery_plan)"
              >
                载入批量恢复
              </button>
              <button
                :disabled="busy"
                @click="applyStateGraphRecoveryPlan(currentDetail.state_graph_recovery_plan, true)"
              >
                创建批量 recovery
              </button>
            </div>
          </div>
          <div v-if="currentDetail.state_graph_diagnostics.length === 0" class="item-card">
            <h3>当前无断链</h3>
            <p>current revision、图谱、时间线、快照与版本引用未发现显式不一致。</p>
          </div>
          <div
            v-for="item in currentDetail.state_graph_diagnostics"
            :key="`${item.category}-${item.entity_type}-${item.entity_id}-${item.summary}`"
            class="item-card"
          >
            <h3>{{ item.severity }} / {{ item.category }}</h3>
            <p>章节：{{ item.chapter_number ?? 'n/a' }} / 实体：{{ item.entity_type || 'unknown' }}</p>
            <p>ID：{{ item.entity_id || '无' }}</p>
            <p>{{ item.summary }}</p>
            <p>{{ item.detail || '无补充说明' }}</p>
            <div v-if="item.repair_suggestion" class="item-card">
              <h3>修复建议</h3>
              <p>{{ item.repair_suggestion.title }}</p>
              <p>{{ item.repair_suggestion.detail || '无补充说明' }}</p>
              <p>
                动作：{{ item.repair_suggestion.recommended_action }} /
                窗口：{{ item.repair_suggestion.start_chapter ?? 'n/a' }} ->
                {{ item.repair_suggestion.end_chapter ?? 'n/a' }}
              </p>
              <div
                v-if="item.repair_suggestion.can_create_scheduler_task"
                class="actions wrap-actions"
              >
                <button
                  :disabled="busy"
                  @click="applyStateGraphRepairSuggestion(item.repair_suggestion)"
                >
                  载入到调度器
                </button>
                <button
                  :disabled="busy"
                  @click="applyStateGraphRepairSuggestion(item.repair_suggestion, true)"
                >
                  创建 recovery 任务
                </button>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>章节指标明细</h2>
          <span>{{ currentDetail.chapter_metrics.length }} 条</span>
        </div>
        <div class="stack compact">
          <div v-if="currentDetail.ops_summary" class="item-card">
            <h3>批量执行观察</h3>
            <p>预算：{{ currentDetail.ops_summary.total_estimated_cost_usd }} / {{ currentDetail.ops_summary.budget_limit_usd }} USD</p>
            <p>最近告警：{{ currentDetail.ops_summary.warnings.join('；') || '暂无' }}</p>
            <p v-if="currentDetail.ops_summary.state_graph_recovery_plan">
              恢复建议：{{ currentDetail.ops_summary.state_graph_recovery_plan.title }}
            </p>
            <ul class="mini-list">
              <li v-for="item in currentDetail.ops_summary.recent_task_summaries" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div
            v-for="metric in currentDetail.chapter_metrics.slice().reverse()"
            :key="metric.id"
            class="item-card"
          >
            <h3>第 {{ metric.chapter_number }} 章 / {{ metric.source }}</h3>
            <p>模型：{{ metric.model_name }}</p>
            <p>Token：{{ metric.total_tokens_estimate }} / 成本：{{ metric.estimated_cost_usd }}</p>
            <p>
              质量 {{ metric.quality_score }} / 抽取 {{ metric.extraction_score }} / 钩子
              {{ metric.hook_score }} / 读者 {{ metric.reader_score }}
            </p>
            <p>长度：{{ metric.content_length }} / 降级：{{ metric.fallback_used ? '是' : '否' }}</p>
            <ul class="mini-list">
              <li v-for="warning in metric.warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>
        </div>
      </article>
    </section>

    <section v-if="currentDetail" class="grid two-cols">
      <article class="panel">
        <div class="panel-head">
          <h2>快照</h2>
          <span>{{ currentDetail.snapshots.length }} 个</span>
        </div>
        <div class="stack compact">
          <div
            v-for="snapshot in currentDetail.snapshots.slice().reverse()"
            :key="snapshot.id"
            class="item-card"
          >
            <h3>{{ snapshot.chapter_title }}</h3>
            <p>第 {{ snapshot.chapter_number }} 章</p>
            <p>{{ snapshot.summary }}</p>
            <p>活跃伏笔数：{{ snapshot.active_hook_ids.length }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>版本记录</h2>
          <span>{{ currentDetail.versions.length }} 个版本</span>
        </div>
        <div class="stack compact">
          <div
            v-for="version in currentDetail.versions.slice().reverse()"
            :key="version.id"
            class="item-card"
          >
            <h3>{{ version.version_label }}</h3>
            <p>第 {{ version.chapter_number }} 章</p>
            <p>{{ version.change_summary }}</p>
          </div>
        </div>
      </article>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>开发阶段</h2>
        <span>按风险从低到高推进</span>
      </div>
      <div class="phase-grid">
        <div v-for="phase in phases" :key="phase.name" class="phase-card">
          <h3>{{ phase.name }}</h3>
          <ul>
            <li v-for="item in phase.items" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>当前约束</h2>
        <span>已在设计中显式处理</span>
      </div>
      <div class="bullet-grid">
        <p>长期记忆不依赖对话历史，改为结构化状态系统。</p>
        <p>章节写作前必须先有章节规划，避免生成链路失控。</p>
        <p>默认支持 mock writer，未配置 LLM 时也能继续开发。</p>
        <p>真实 OpenAI 调用入口已预留，但当前环境尚未配置 API Key。</p>
      </div>
    </section>
  </main>
</template>
