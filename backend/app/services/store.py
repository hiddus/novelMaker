import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.domain import (
    BatchWriteResult,
    ChapterDraft,
    ChapterMetric,
    ChapterPlan,
    Character,
    CharacterState,
    ContinuityReport,
    ExtractedUpdate,
    Event,
    HookRecord,
    HookStateChange,
    GovernanceEvent,
    GovernancePolicy,
    LongTermMemoryRecord,
    MemoryRetrievalTrace,
    Project,
    Snapshot,
    StoryBible,
    TaskRun,
    RetconPatch,
    ReaderCouncilReport,
    SchedulerTask,
    VersionRecord,
    WritingRun,
    RollbackResult,
    MetricsSummary,
    ReviewReport,
)
from app.services.retcon import build_retcon_patch, summarize_invalidated_plans


class WorkspaceStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_dir = settings.data_dir
        self.db_path = self.base_dir / "workspace.json"
        self._ensure_db()

    def _ensure_db(self) -> None:
        if self.db_path.exists():
            return

        self._write(
            {
                "projects": [],
                "characters": {},
                "events": {},
                "chapter_plans": {},
                "chapters": {},
                "story_bibles": {},
                "runs": {},
                "character_states": {},
                "extracted_updates": {},
                "snapshots": {},
                "versions": {},
                "task_runs": {},
                "retcon_patches": {},
                "scheduler_tasks": {},
                "chapter_metrics": {},
                "reviews": {},
                "continuity_reports": {},
                "reader_council_reports": {},
                "hook_records": {},
                "hook_state_changes": {},
                "governance_policies": {},
                "governance_events": {},
                "long_term_memories": {},
                "memory_retrieval_traces": {},
            }
        )

    def _read(self) -> dict[str, Any]:
        payload = json.loads(self.db_path.read_text(encoding="utf-8"))
        changed = False
        for key, default in {
            "projects": [],
            "characters": {},
            "events": {},
            "chapter_plans": {},
            "chapters": {},
            "story_bibles": {},
            "runs": {},
            "character_states": {},
            "extracted_updates": {},
            "snapshots": {},
            "versions": {},
            "task_runs": {},
            "retcon_patches": {},
            "scheduler_tasks": {},
            "chapter_metrics": {},
            "reviews": {},
            "continuity_reports": {},
            "reader_council_reports": {},
            "hook_records": {},
            "hook_state_changes": {},
            "governance_policies": {},
            "governance_events": {},
            "long_term_memories": {},
            "memory_retrieval_traces": {},
        }.items():
            if key not in payload:
                payload[key] = default
                changed = True
        if changed:
            self._write(payload)
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.db_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_projects(self) -> list[Project]:
        db = self._read()
        return [Project.model_validate(item) for item in db["projects"]]

    def get_project(self, project_id: str) -> Project | None:
        for project in self.list_projects():
            if project.id == project_id:
                return project
        return None

    def create_project(self, project: Project) -> Project:
        db = self._read()
        db["projects"].append(project.model_dump(mode="json"))
        db["story_bibles"][project.id] = StoryBible(
            genre=project.genre,
            tone=project.tone,
            author_intent=[project.premise],
        ).model_dump(mode="json")
        db["governance_policies"][project.id] = GovernancePolicy(project_id=project.id).model_dump(mode="json")
        self._write(db)
        return project

    def get_story_bible(self, project_id: str) -> StoryBible:
        db = self._read()
        item = db["story_bibles"].get(project_id)
        if item is None:
            bible = StoryBible()
            db["story_bibles"][project_id] = bible.model_dump(mode="json")
            self._write(db)
            return bible
        return StoryBible.model_validate(item)

    def get_governance_policy(self, project_id: str) -> GovernancePolicy:
        db = self._read()
        item = db["governance_policies"].get(project_id)
        if item is None:
            policy = GovernancePolicy(project_id=project_id)
            db["governance_policies"][project_id] = policy.model_dump(mode="json")
            self._write(db)
            return policy
        return GovernancePolicy.model_validate(item)

    def save_governance_policy(self, project_id: str, policy: GovernancePolicy) -> GovernancePolicy:
        db = self._read()
        db["governance_policies"][project_id] = policy.model_dump(mode="json")
        self._write(db)
        return policy

    def upsert_story_bible(self, project_id: str, story_bible: StoryBible) -> StoryBible:
        db = self._read()
        db["story_bibles"][project_id] = story_bible.model_dump(mode="json")
        self._write(db)
        return story_bible

    def list_characters(self, project_id: str) -> list[Character]:
        db = self._read()
        items = db["characters"].get(project_id, [])
        return [Character.model_validate(item) for item in items]

    def add_character(self, project_id: str, character: Character) -> Character:
        db = self._read()
        db["characters"].setdefault(project_id, []).append(character.model_dump(mode="json"))
        self._write(db)
        return character

    def list_character_states(self, project_id: str) -> list[CharacterState]:
        db = self._read()
        items = db["character_states"].get(project_id, [])
        return [CharacterState.model_validate(item) for item in items]

    def add_character_state(self, project_id: str, state: CharacterState) -> CharacterState:
        db = self._read()
        db["character_states"].setdefault(project_id, []).append(state.model_dump(mode="json"))
        self._write(db)
        return state

    def list_events(self, project_id: str) -> list[Event]:
        db = self._read()
        items = db["events"].get(project_id, [])
        return [Event.model_validate(item) for item in items]

    def add_event(self, project_id: str, event: Event) -> Event:
        db = self._read()
        db["events"].setdefault(project_id, []).append(event.model_dump(mode="json"))
        self._write(db)
        return event

    def list_chapter_plans(self, project_id: str) -> list[ChapterPlan]:
        db = self._read()
        items = db["chapter_plans"].get(project_id, [])
        return [ChapterPlan.model_validate(item) for item in items]

    def add_chapter_plan(self, project_id: str, plan: ChapterPlan) -> ChapterPlan:
        db = self._read()
        db["chapter_plans"].setdefault(project_id, []).append(plan.model_dump(mode="json"))
        self._write(db)
        return plan

    def replace_chapter_plans(
        self,
        project_id: str,
        chapter_numbers: list[int],
        plans: list[ChapterPlan],
    ) -> list[ChapterPlan]:
        db = self._read()
        existing = db["chapter_plans"].setdefault(project_id, [])
        target_numbers = set(chapter_numbers)
        kept = [item for item in existing if item.get("chapter_number") not in target_numbers]
        kept.extend(plan.model_dump(mode="json") for plan in plans)
        db["chapter_plans"][project_id] = kept
        self._write(db)
        return plans

    def list_chapters(self, project_id: str) -> list[ChapterDraft]:
        db = self._read()
        items = db["chapters"].get(project_id, [])
        return [ChapterDraft.model_validate(item) for item in items]

    def get_chapter(self, project_id: str, chapter_id: str) -> ChapterDraft | None:
        for chapter in self.list_chapters(project_id):
            if chapter.id == chapter_id:
                return chapter
        return None

    def list_chapter_revisions(self, project_id: str, chapter_number: int) -> list[ChapterDraft]:
        return [chapter for chapter in self.list_chapters(project_id) if chapter.chapter_number == chapter_number]

    def add_chapter(self, project_id: str, chapter: ChapterDraft) -> ChapterDraft:
        db = self._read()
        db["chapters"].setdefault(project_id, []).append(chapter.model_dump(mode="json"))

        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break

        self._write(db)
        return chapter

    def save_chapter(self, project_id: str, chapter: ChapterDraft) -> ChapterDraft:
        db = self._read()
        chapters = db["chapters"].setdefault(project_id, [])
        for index, item in enumerate(chapters):
            if item["id"] == chapter.id:
                chapters[index] = chapter.model_dump(mode="json")
                break
        else:
            chapters.append(chapter.model_dump(mode="json"))
        db["chapters"][project_id] = chapters

        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break

        self._write(db)
        return chapter

    def list_runs(self, project_id: str) -> list[WritingRun]:
        db = self._read()
        items = db["runs"].get(project_id, [])
        return [WritingRun.model_validate(item) for item in items]

    def save_run(self, project_id: str, run: WritingRun) -> WritingRun:
        db = self._read()
        runs = db["runs"].setdefault(project_id, [])
        for index, item in enumerate(runs):
            if item["id"] == run.id:
                runs[index] = run.model_dump(mode="json")
                break
        else:
            runs.append(run.model_dump(mode="json"))
        db["runs"][project_id] = runs
        self._write(db)
        return run

    def list_extracted_updates(self, project_id: str) -> list[ExtractedUpdate]:
        db = self._read()
        items = db["extracted_updates"].get(project_id, [])
        return [ExtractedUpdate.model_validate(item) for item in items]

    def add_extracted_update(self, project_id: str, update: ExtractedUpdate) -> ExtractedUpdate:
        db = self._read()
        db["extracted_updates"].setdefault(project_id, []).append(update.model_dump(mode="json"))
        self._write(db)
        return update

    def list_snapshots(self, project_id: str) -> list[Snapshot]:
        db = self._read()
        items = db["snapshots"].get(project_id, [])
        return [Snapshot.model_validate(item) for item in items]

    def add_snapshot(self, project_id: str, snapshot: Snapshot) -> Snapshot:
        db = self._read()
        db["snapshots"].setdefault(project_id, []).append(snapshot.model_dump(mode="json"))
        self._write(db)
        return snapshot

    def list_versions(self, project_id: str) -> list[VersionRecord]:
        db = self._read()
        items = db["versions"].get(project_id, [])
        return [VersionRecord.model_validate(item) for item in items]

    def add_version(self, project_id: str, version: VersionRecord) -> VersionRecord:
        db = self._read()
        db["versions"].setdefault(project_id, []).append(version.model_dump(mode="json"))
        self._write(db)
        return version

    def list_task_runs(self, project_id: str) -> list[TaskRun]:
        db = self._read()
        items = db["task_runs"].get(project_id, [])
        return [TaskRun.model_validate(item) for item in items]

    def save_task_run(self, project_id: str, task_run: TaskRun) -> TaskRun:
        db = self._read()
        runs = db["task_runs"].setdefault(project_id, [])
        for index, item in enumerate(runs):
            if item["id"] == task_run.id:
                runs[index] = task_run.model_dump(mode="json")
                break
        else:
            runs.append(task_run.model_dump(mode="json"))
        db["task_runs"][project_id] = runs
        self._write(db)
        return task_run

    def list_retcon_patches(self, project_id: str) -> list[RetconPatch]:
        db = self._read()
        items = db["retcon_patches"].get(project_id, [])
        return [RetconPatch.model_validate(item) for item in items]

    def save_retcon_patch(self, project_id: str, patch: RetconPatch) -> RetconPatch:
        db = self._read()
        patches = db["retcon_patches"].setdefault(project_id, [])
        for index, item in enumerate(patches):
            if item["id"] == patch.id:
                patches[index] = patch.model_dump(mode="json")
                break
        else:
            patches.append(patch.model_dump(mode="json"))
        db["retcon_patches"][project_id] = patches
        self._write(db)
        return patch

    def list_scheduler_tasks(self, project_id: str) -> list[SchedulerTask]:
        db = self._read()
        items = db["scheduler_tasks"].get(project_id, [])
        return [SchedulerTask.model_validate(item) for item in items]

    def save_scheduler_task(self, project_id: str, task: SchedulerTask) -> SchedulerTask:
        db = self._read()
        tasks = db["scheduler_tasks"].setdefault(project_id, [])
        for index, item in enumerate(tasks):
            if item["id"] == task.id:
                tasks[index] = task.model_dump(mode="json")
                break
        else:
            tasks.append(task.model_dump(mode="json"))
        db["scheduler_tasks"][project_id] = tasks
        self._write(db)
        return task

    def get_scheduler_task(self, project_id: str, task_id: str) -> SchedulerTask | None:
        for task in self.list_scheduler_tasks(project_id):
            if task.id == task_id:
                return task
        return None

    def list_chapter_metrics(self, project_id: str) -> list[ChapterMetric]:
        db = self._read()
        items = db["chapter_metrics"].get(project_id, [])
        return [ChapterMetric.model_validate(item) for item in items]

    def save_chapter_metric(self, project_id: str, metric: ChapterMetric) -> ChapterMetric:
        db = self._read()
        metrics = db["chapter_metrics"].setdefault(project_id, [])
        for index, item in enumerate(metrics):
            if item["id"] == metric.id:
                metrics[index] = metric.model_dump(mode="json")
                break
        else:
            metrics.append(metric.model_dump(mode="json"))
        db["chapter_metrics"][project_id] = metrics
        self._write(db)
        return metric

    def list_reviews(self, project_id: str) -> list[ReviewReport]:
        db = self._read()
        items = db["reviews"].get(project_id, [])
        return [ReviewReport.model_validate(item) for item in items]

    def get_review(self, project_id: str, review_id: str) -> ReviewReport | None:
        for review in self.list_reviews(project_id):
            if review.id == review_id:
                return review
        return None

    def save_review(self, project_id: str, review: ReviewReport) -> ReviewReport:
        db = self._read()
        reviews = db["reviews"].setdefault(project_id, [])
        for index, item in enumerate(reviews):
            if item["id"] == review.id:
                reviews[index] = review.model_dump(mode="json")
                break
        else:
            reviews.append(review.model_dump(mode="json"))
        db["reviews"][project_id] = reviews
        self._write(db)
        return review

    def list_continuity_reports(self, project_id: str) -> list[ContinuityReport]:
        db = self._read()
        items = db["continuity_reports"].get(project_id, [])
        return [ContinuityReport.model_validate(item) for item in items]

    def save_continuity_report(self, project_id: str, report: ContinuityReport) -> ContinuityReport:
        db = self._read()
        reports = db["continuity_reports"].setdefault(project_id, [])
        for index, item in enumerate(reports):
            if item["id"] == report.id:
                reports[index] = report.model_dump(mode="json")
                break
        else:
            reports.append(report.model_dump(mode="json"))
        db["continuity_reports"][project_id] = reports
        self._write(db)
        return report

    def list_reader_council_reports(self, project_id: str) -> list[ReaderCouncilReport]:
        db = self._read()
        items = db["reader_council_reports"].get(project_id, [])
        return [ReaderCouncilReport.model_validate(item) for item in items]

    def save_reader_council_report(
        self,
        project_id: str,
        report: ReaderCouncilReport,
    ) -> ReaderCouncilReport:
        db = self._read()
        reports = db["reader_council_reports"].setdefault(project_id, [])
        for index, item in enumerate(reports):
            if item["id"] == report.id:
                reports[index] = report.model_dump(mode="json")
                break
        else:
            reports.append(report.model_dump(mode="json"))
        db["reader_council_reports"][project_id] = reports
        self._write(db)
        return report

    def list_hook_records(self, project_id: str) -> list[HookRecord]:
        db = self._read()
        items = db["hook_records"].get(project_id, [])
        return [HookRecord.model_validate(item) for item in items]

    def save_hook_record(self, project_id: str, record: HookRecord) -> HookRecord:
        db = self._read()
        records = db["hook_records"].setdefault(project_id, [])
        for index, item in enumerate(records):
            if item["id"] == record.id:
                records[index] = record.model_dump(mode="json")
                break
        else:
            records.append(record.model_dump(mode="json"))
        db["hook_records"][project_id] = records
        self._write(db)
        return record

    def replace_hook_records(self, project_id: str, records: list[HookRecord]) -> list[HookRecord]:
        db = self._read()
        db["hook_records"][project_id] = [item.model_dump(mode="json") for item in records]
        self._write(db)
        return records

    def list_hook_state_changes(self, project_id: str) -> list[HookStateChange]:
        db = self._read()
        items = db["hook_state_changes"].get(project_id, [])
        return [HookStateChange.model_validate(item) for item in items]

    def add_hook_state_change(self, project_id: str, change: HookStateChange) -> HookStateChange:
        db = self._read()
        db["hook_state_changes"].setdefault(project_id, []).append(change.model_dump(mode="json"))
        self._write(db)
        return change

    def list_governance_events(self, project_id: str) -> list[GovernanceEvent]:
        db = self._read()
        items = db["governance_events"].get(project_id, [])
        return [GovernanceEvent.model_validate(item) for item in items]

    def add_governance_event(self, project_id: str, event: GovernanceEvent) -> GovernanceEvent:
        db = self._read()
        db["governance_events"].setdefault(project_id, []).append(event.model_dump(mode="json"))
        self._write(db)
        return event

    def list_long_term_memories(self, project_id: str) -> list[LongTermMemoryRecord]:
        db = self._read()
        items = db["long_term_memories"].get(project_id, [])
        return [LongTermMemoryRecord.model_validate(item) for item in items]

    def replace_long_term_memories(
        self,
        project_id: str,
        records: list[LongTermMemoryRecord],
    ) -> list[LongTermMemoryRecord]:
        db = self._read()
        db["long_term_memories"][project_id] = [item.model_dump(mode="json") for item in records]
        self._write(db)
        return records

    def list_memory_retrieval_traces(self, project_id: str) -> list[MemoryRetrievalTrace]:
        db = self._read()
        items = db["memory_retrieval_traces"].get(project_id, [])
        return [MemoryRetrievalTrace.model_validate(item) for item in items]

    def add_memory_retrieval_trace(
        self,
        project_id: str,
        trace: MemoryRetrievalTrace,
    ) -> MemoryRetrievalTrace:
        db = self._read()
        traces = db["memory_retrieval_traces"].setdefault(project_id, [])
        traces.append(trace.model_dump(mode="json"))
        limit = get_settings().memory_trace_limit
        if limit > 0 and len(traces) > limit:
            traces = traces[-limit:]
        db["memory_retrieval_traces"][project_id] = traces
        self._write(db)
        return trace

    def rollback_to_chapter(
        self,
        project_id: str,
        target_chapter_number: int,
        reason: str,
    ) -> tuple[RollbackResult, RetconPatch]:
        db = self._read()

        def split_items(items: list[dict[str, Any]], chapter_key: str = "chapter_number") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            kept: list[dict[str, Any]] = []
            removed: list[dict[str, Any]] = []
            for item in items:
                chapter_number = item.get(chapter_key, 0)
                if chapter_number is not None and chapter_number <= target_chapter_number:
                    kept.append(item)
                else:
                    removed.append(item)
            return kept, removed

        chapters_kept, chapters_removed = split_items(db["chapters"].get(project_id, []))
        events_kept, events_removed = split_items(db["events"].get(project_id, []))
        states_kept, states_removed = split_items(db["character_states"].get(project_id, []))
        extracts_kept, _ = split_items(db["extracted_updates"].get(project_id, []))
        snapshots_kept, snapshots_removed = split_items(db["snapshots"].get(project_id, []))
        versions_kept, versions_removed = split_items(db["versions"].get(project_id, []))
        plans_kept, plans_removed = split_items(db["chapter_plans"].get(project_id, []))
        runs_kept, _ = split_items(db["runs"].get(project_id, []))
        metrics_kept, _ = split_items(db["chapter_metrics"].get(project_id, []))
        reviews_kept, _ = split_items(db["reviews"].get(project_id, []))
        continuity_kept, _ = split_items(db["continuity_reports"].get(project_id, []))
        reader_kept, _ = split_items(db["reader_council_reports"].get(project_id, []))
        hook_change_kept, _ = split_items(db["hook_state_changes"].get(project_id, []))

        db["chapters"][project_id] = chapters_kept
        db["events"][project_id] = events_kept
        db["character_states"][project_id] = states_kept
        db["extracted_updates"][project_id] = extracts_kept
        db["snapshots"][project_id] = snapshots_kept
        db["versions"][project_id] = versions_kept
        db["chapter_plans"][project_id] = plans_kept
        db["runs"][project_id] = runs_kept
        db["chapter_metrics"][project_id] = metrics_kept
        db["reviews"][project_id] = reviews_kept
        db["continuity_reports"][project_id] = continuity_kept
        db["reader_council_reports"][project_id] = reader_kept
        db["hook_state_changes"][project_id] = hook_change_kept

        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break

        self._write(db)

        rollback = RollbackResult(
            project_id=project_id,
            target_chapter_number=target_chapter_number,
            removed_chapters=len(chapters_removed),
            removed_events=len(events_removed),
            removed_character_states=len(states_removed),
            removed_snapshots=len(snapshots_removed),
            removed_versions=len(versions_removed),
            message=f"已回滚到第 {target_chapter_number} 章，原因：{reason}",
        )

        removed_plan_models = [ChapterPlan.model_validate(item) for item in plans_removed]
        invalidated_plan_ids, requires_recompute_hooks = summarize_invalidated_plans(
            removed_plan_models,
            target_chapter_number,
        )
        patch = build_retcon_patch(
            project_id=project_id,
            target_chapter_number=target_chapter_number,
            reason=reason,
            removed_chapter_numbers=[item["chapter_number"] for item in chapters_removed],
            invalidated_version_ids=[item["id"] for item in versions_removed],
            removed_plan_ids=invalidated_plan_ids,
            removed_plan_hooks=requires_recompute_hooks,
            removed_events_count=len(events_removed),
            removed_states_count=len(states_removed),
            removed_snapshots_count=len(snapshots_removed),
        )
        self.save_retcon_patch(project_id, patch)
        rollback.patch_id = patch.id

        rebuilt_hooks: dict[str, HookRecord] = {}
        for item in hook_change_kept:
            change = HookStateChange.model_validate(item)
            existing = rebuilt_hooks.get(change.hook_id)
            if change.action == "create":
                rebuilt_hooks[change.hook_id] = HookRecord(
                    id=change.hook_id,
                    project_id=project_id,
                    content=change.content,
                    created_in_chapter=change.chapter_number,
                    source_chapter_id=change.chapter_id,
                    expected_resolution_arc=change.expected_resolution_arc,
                    status="open",
                    last_touched_chapter=change.chapter_number,
                    note=change.note,
                )
                continue
            if existing is None:
                continue
            if change.action == "activate":
                existing.status = "active"
                existing.last_touched_chapter = change.chapter_number
            elif change.action == "resolve":
                existing.status = "resolved"
                existing.last_touched_chapter = change.chapter_number
                existing.resolution_chapter = change.chapter_number
            elif change.action == "abandon":
                existing.status = "abandoned"
                existing.last_touched_chapter = change.chapter_number
                existing.resolution_chapter = change.chapter_number
            existing.updated_at = datetime.now(UTC)
            rebuilt_hooks[change.hook_id] = existing
        self.replace_hook_records(project_id, list(rebuilt_hooks.values()))

        return rollback, patch

    def build_metrics_summary(self, project_id: str) -> MetricsSummary:
        metrics = self.list_chapter_metrics(project_id)
        if not metrics:
            return MetricsSummary(project_id=project_id)

        chapter_count = len(metrics)
        llm_count = sum(1 for item in metrics if item.source == "llm")
        fallback_count = sum(1 for item in metrics if item.fallback_used)
        total_tokens = sum(item.total_tokens_estimate for item in metrics)
        total_cost = sum(item.estimated_cost_usd for item in metrics)
        avg_quality = sum(item.quality_score for item in metrics) / chapter_count
        avg_extraction = sum(item.extraction_score for item in metrics) / chapter_count
        avg_hook = sum(item.hook_score for item in metrics) / chapter_count
        avg_review = sum(item.review_score for item in metrics) / chapter_count
        avg_reader = sum(item.reader_score for item in metrics) / chapter_count
        warnings = [warning for item in metrics[-5:] for warning in item.warnings][:10]
        hooks = self.list_hook_records(project_id)
        open_hook_count = sum(1 for item in hooks if item.status in {"open", "active"})
        resolved_hook_count = sum(1 for item in hooks if item.status == "resolved")
        hook_resolution_rate = round(resolved_hook_count / len(hooks), 2) if hooks else 0.0

        return MetricsSummary(
            project_id=project_id,
            chapter_count=chapter_count,
            llm_chapter_count=llm_count,
            fallback_count=fallback_count,
            open_hook_count=open_hook_count,
            resolved_hook_count=resolved_hook_count,
            hook_resolution_rate=hook_resolution_rate,
            total_tokens_estimate=total_tokens,
            total_estimated_cost_usd=round(total_cost, 6),
            average_quality_score=round(avg_quality, 2),
            average_extraction_score=round(avg_extraction, 2),
            average_hook_score=round(avg_hook, 2),
            average_review_score=round(avg_review, 2),
            average_reader_score=round(avg_reader, 2),
            latest_warnings=warnings,
        )


store = WorkspaceStore()
