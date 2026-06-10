import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.domain import (
    BatchWriteResult,
    ChapterDraft,
    ChapterMetric,
    ChapterPlan,
    Character,
    CharacterRelationshipEdge,
    CharacterState,
    ContinuityReport,
    ExtractedUpdate,
    Event,
    HookRecord,
    HookStateChange,
    GovernanceEvent,
    GovernancePolicy,
    LLMChapterPreflightResult,
    LLMDiagnosticResult,
    LLMTestRunResult,
    LongTermMemoryRecord,
    MemoryRetrievalTrace,
    QueueJob,
    Project,
    Snapshot,
    StoryBible,
    TaskRun,
    RetconPatch,
    ReaderCouncilReport,
    SchedulerTask,
    VersionRecord,
    WorkerSnapshot,
    WritingRun,
    RollbackResult,
    MetricsSummary,
    ReviewReport,
    TimelineConstraint,
    TimelineNode,
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
                "relationship_edges": {},
                "timeline_nodes": {},
                "timeline_constraints": {},
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
                "queue_jobs": {},
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
                "llm_diagnostics": [],
                "llm_test_runs": [],
                "llm_chapter_preflights": [],
            }
        )

    def _read(self) -> dict[str, Any]:
        payload = json.loads(self.db_path.read_text(encoding="utf-8"))
        changed = False
        for key, default in {
            "projects": [],
            "characters": {},
            "events": {},
            "relationship_edges": {},
            "timeline_nodes": {},
            "timeline_constraints": {},
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
            "queue_jobs": {},
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
            "llm_diagnostics": [],
            "llm_test_runs": [],
            "llm_chapter_preflights": [],
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

    def list_relationship_edges(self, project_id: str) -> list[CharacterRelationshipEdge]:
        db = self._read()
        items = db["relationship_edges"].get(project_id, [])
        return [CharacterRelationshipEdge.model_validate(item) for item in items]

    def add_relationship_edge(self, project_id: str, edge: CharacterRelationshipEdge) -> CharacterRelationshipEdge:
        db = self._read()
        db["relationship_edges"].setdefault(project_id, []).append(edge.model_dump(mode="json"))
        self._write(db)
        return edge

    def save_relationship_edge(self, project_id: str, edge: CharacterRelationshipEdge) -> CharacterRelationshipEdge:
        db = self._read()
        edges = db["relationship_edges"].setdefault(project_id, [])
        for index, item in enumerate(edges):
            if item["id"] == edge.id:
                edges[index] = edge.model_dump(mode="json")
                self._write(db)
                return edge
        edges.append(edge.model_dump(mode="json"))
        self._write(db)
        return edge

    def list_timeline_nodes(self, project_id: str) -> list[TimelineNode]:
        db = self._read()
        items = db["timeline_nodes"].get(project_id, [])
        return [TimelineNode.model_validate(item) for item in items]

    def add_timeline_node(self, project_id: str, node: TimelineNode) -> TimelineNode:
        db = self._read()
        db["timeline_nodes"].setdefault(project_id, []).append(node.model_dump(mode="json"))
        self._write(db)
        return node

    def list_timeline_constraints(self, project_id: str) -> list[TimelineConstraint]:
        db = self._read()
        items = db["timeline_constraints"].get(project_id, [])
        return [TimelineConstraint.model_validate(item) for item in items]

    def _timeline_constraint_window(self, constraint: TimelineConstraint) -> int | None:
        if constraint.constraint_type == "patch":
            return None
        if constraint.constraint_type == "travel":
            return 2
        if constraint.constraint_type in {"ordering", "presence"}:
            return 1
        return 1

    def _timeline_constraint_signature(
        self,
        constraint: TimelineConstraint,
    ) -> tuple[str, str, str, str]:
        return (
            constraint.constraint_type,
            constraint.related_node_id or "",
            constraint.related_character_id or "",
            constraint.description,
        )

    def _timeline_constraint_evolution_key(self, constraint: TimelineConstraint) -> str:
        if constraint.evolution_key:
            return constraint.evolution_key
        evidence_key = "|".join(sorted(constraint.evidence[:4])) if constraint.constraint_type == "patch" else ""
        return "::".join(
            [
                constraint.constraint_type,
                constraint.related_character_id or "",
                constraint.description,
                evidence_key,
            ]
        )

    def add_timeline_constraint(self, project_id: str, constraint: TimelineConstraint) -> TimelineConstraint:
        db = self._read()
        db["timeline_constraints"].setdefault(project_id, []).append(constraint.model_dump(mode="json"))
        self._write(db)
        return constraint

    def save_timeline_constraint(self, project_id: str, constraint: TimelineConstraint) -> TimelineConstraint:
        db = self._read()
        constraints = db["timeline_constraints"].setdefault(project_id, [])
        for index, item in enumerate(constraints):
            if item["id"] == constraint.id:
                constraints[index] = constraint.model_dump(mode="json")
                self._write(db)
                return constraint
        constraints.append(constraint.model_dump(mode="json"))
        self._write(db)
        return constraint

    def _sync_timeline_constraints_in_db(
        self,
        db: dict[str, Any],
        project_id: str,
        chapter_number: int,
        constraints: list[TimelineConstraint],
    ) -> list[TimelineConstraint]:
        raw_items = db["timeline_constraints"].setdefault(project_id, [])
        existing = [
            TimelineConstraint.model_validate(item)
            for item in raw_items
            if item.get("chapter_number") == chapter_number
        ]
        other_constraints = [
            TimelineConstraint.model_validate(item)
            for item in raw_items
            if item.get("chapter_number") != chapter_number
        ]
        existing_by_signature = {
            self._timeline_constraint_signature(item): item for item in existing
        }
        next_signatures = {
            self._timeline_constraint_signature(item) for item in constraints
        }
        synced: list[TimelineConstraint] = []
        updated_other_constraints: dict[str, TimelineConstraint] = {}
        latest_active_by_evolution: dict[str, TimelineConstraint] = {}
        for item in other_constraints:
            evolution_key = self._timeline_constraint_evolution_key(item)
            if (
                item.is_current
                and item.status in {"warning", "violated"}
                and (
                    evolution_key not in latest_active_by_evolution
                    or latest_active_by_evolution[evolution_key].chapter_number < item.chapter_number
                )
            ):
                latest_active_by_evolution[evolution_key] = item

        for constraint in constraints:
            signature = self._timeline_constraint_signature(constraint)
            previous = existing_by_signature.get(signature)
            evolution_key = self._timeline_constraint_evolution_key(constraint)
            active_previous = latest_active_by_evolution.get(evolution_key)
            if previous is not None:
                synced.append(
                    constraint.model_copy(
                        update={
                            "id": previous.id,
                            "created_at": previous.created_at,
                            "evolution_key": previous.evolution_key or evolution_key,
                            "previous_constraint_id": previous.previous_constraint_id,
                            "is_current": previous.is_current,
                            "resolved_in_chapter": previous.resolved_in_chapter,
                        }
                    )
                )
            else:
                updates: dict[str, object] = {
                    "evolution_key": evolution_key,
                    "is_current": True,
                }
                if active_previous is not None:
                    updates["previous_constraint_id"] = active_previous.id
                    if constraint.status == "clear":
                        updated_other_constraints[active_previous.id] = active_previous.model_copy(
                            update={
                                "status": "resolved",
                                "is_current": False,
                                "resolved_in_chapter": chapter_number,
                                "recommendation": active_previous.recommendation
                                or "后续章节已补足该时间线约束。",
                            }
                        )
                    else:
                        updated_other_constraints[active_previous.id] = active_previous.model_copy(
                            update={"is_current": False}
                        )
                synced.append(constraint.model_copy(update=updates))

        resolved_existing = [
            item.model_copy(
                update={
                    "status": "resolved",
                    "is_current": False,
                    "resolved_in_chapter": chapter_number,
                    "recommendation": item.recommendation or "同章时间线约束已被更新版本覆盖。",
                }
            )
            for item in existing
            if self._timeline_constraint_signature(item) not in next_signatures and item.status != "resolved"
        ]

        normalized_other = [
            updated_other_constraints.get(item.id, item).model_dump(mode="json")
            for item in other_constraints
        ]
        db["timeline_constraints"][project_id] = normalized_other + [
            item.model_dump(mode="json") for item in [*synced, *resolved_existing]
        ]
        return synced

    def sync_timeline_constraints(
        self,
        project_id: str,
        chapter_number: int,
        constraints: list[TimelineConstraint],
    ) -> list[TimelineConstraint]:
        db = self._read()
        synced = self._sync_timeline_constraints_in_db(db, project_id, chapter_number, constraints)
        self._write(db)
        return synced

    def resolve_patch_timeline_constraints(
        self,
        project_id: str,
        patch_id: str,
        resolved_in_chapter: int | None = None,
    ) -> int:
        db = self._read()
        constraints = db["timeline_constraints"].setdefault(project_id, [])
        resolved_count = 0
        for index, item in enumerate(constraints):
            constraint = TimelineConstraint.model_validate(item)
            if (
                constraint.constraint_type == "patch"
                and constraint.status in {"warning", "violated"}
                and patch_id in constraint.evidence
            ):
                constraints[index] = constraint.model_copy(
                    update={
                        "status": "resolved",
                        "is_current": False,
                        "resolved_in_chapter": resolved_in_chapter or constraint.chapter_number,
                        "recommendation": "对应补丁已完成 rerun，风险已闭合。",
                    }
                ).model_dump(mode="json")
                resolved_count += 1
        if resolved_count:
            self._write(db)
        return resolved_count

    def _resolve_stale_timeline_constraints_in_db(
        self,
        db: dict[str, Any],
        project_id: str,
        chapter_number: int,
    ) -> int:
        constraints = db["timeline_constraints"].setdefault(project_id, [])
        resolved_count = 0
        for index, item in enumerate(constraints):
            constraint = TimelineConstraint.model_validate(item)
            window = self._timeline_constraint_window(constraint)
            if (
                constraint.is_current
                and constraint.status in {"warning", "violated"}
                and window is not None
                and chapter_number - constraint.chapter_number > window
            ):
                constraints[index] = constraint.model_copy(
                    update={
                        "status": "resolved",
                        "is_current": False,
                        "resolved_in_chapter": chapter_number,
                        "recommendation": (
                            constraint.recommendation
                            or "该时间线风险已超出持续观察窗口，转为历史约束记录。"
                        ),
                    }
                ).model_dump(mode="json")
                resolved_count += 1
        return resolved_count

    def resolve_stale_timeline_constraints(self, project_id: str, chapter_number: int) -> int:
        db = self._read()
        resolved_count = self._resolve_stale_timeline_constraints_in_db(db, project_id, chapter_number)
        if resolved_count:
            self._write(db)
        return resolved_count

    def list_active_timeline_constraints(
        self,
        project_id: str,
        chapter_number: int,
    ) -> list[TimelineConstraint]:
        active: list[TimelineConstraint] = []
        for constraint in self.list_timeline_constraints(project_id):
            if constraint.chapter_number > chapter_number:
                continue
            if not constraint.is_current:
                continue
            if constraint.status not in {"warning", "violated"}:
                continue
            window = self._timeline_constraint_window(constraint)
            if window is not None and chapter_number - constraint.chapter_number > window:
                continue
            active.append(constraint)
        return active

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

    def list_queue_jobs(self, project_id: str) -> list[QueueJob]:
        db = self._read()
        items = db["queue_jobs"].get(project_id, [])
        return [QueueJob.model_validate(item) for item in items]

    def list_all_queue_jobs(self) -> list[QueueJob]:
        db = self._read()
        items: list[QueueJob] = []
        for project_items in db["queue_jobs"].values():
            items.extend(QueueJob.model_validate(item) for item in project_items)
        return items

    def save_queue_job(self, project_id: str, job: QueueJob) -> QueueJob:
        db = self._read()
        jobs = db["queue_jobs"].setdefault(project_id, [])
        for index, item in enumerate(jobs):
            if item["id"] == job.id:
                jobs[index] = job.model_dump(mode="json")
                break
        else:
            jobs.append(job.model_dump(mode="json"))
        db["queue_jobs"][project_id] = jobs
        self._write(db)
        return job

    def get_queue_job(self, project_id: str, job_id: str) -> QueueJob | None:
        for job in self.list_queue_jobs(project_id):
            if job.id == job_id:
                return job
        return None

    def get_active_queue_job_for_task(self, project_id: str, task_id: str) -> QueueJob | None:
        candidates = [
            item
            for item in self.list_queue_jobs(project_id)
            if item.task_id == task_id and item.status in {"pending", "leased"}
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.available_at, item.created_at))
        return candidates[0]

    def enqueue_scheduler_task_job(self, project_id: str, task: SchedulerTask, payload_summary: str = "") -> QueueJob:
        existing = self.get_active_queue_job_for_task(project_id, task.id)
        if existing is not None:
            if payload_summary and not existing.payload_summary:
                updated = existing.model_copy(
                    update={
                        "payload_summary": payload_summary,
                        "updated_at": datetime.now(UTC),
                    }
                )
                return self.save_queue_job(project_id, updated)
            return existing

        job = QueueJob(
            project_id=project_id,
            task_id=task.id,
            payload_summary=payload_summary or f"执行调度任务 {task.id}",
        )
        self.save_queue_job(project_id, job)
        queued_task = task.model_copy(
            update={
                "status": "queued",
                "active_queue_job_id": job.id,
                "stage_message": task.stage_message or "任务已入队，等待 worker 执行",
                "updated_at": datetime.now(UTC),
            }
        )
        self.save_scheduler_task(project_id, queued_task)
        return job

    def claim_next_queue_job(self, worker_id: str, lease_seconds: int) -> QueueJob | None:
        db = self._read()
        now = datetime.now(UTC)
        best_project_id: str | None = None
        best_index: int | None = None
        best_job: QueueJob | None = None

        for project_id, items in db["queue_jobs"].items():
            for index, raw in enumerate(items):
                job = QueueJob.model_validate(raw)
                lease_expired = job.lease_expires_at is not None and job.lease_expires_at <= now
                if job.status not in {"pending", "leased"}:
                    continue
                if job.status == "leased" and not lease_expired:
                    continue
                if job.available_at > now:
                    continue
                if best_job is None or (job.available_at, job.created_at) < (best_job.available_at, best_job.created_at):
                    best_project_id = project_id
                    best_index = index
                    best_job = job

        if best_job is None or best_project_id is None or best_index is None:
            return None

        claimed = best_job.model_copy(
            update={
                "status": "leased",
                "worker_id": worker_id,
                "attempt_count": best_job.attempt_count + 1,
                "lease_expires_at": now + timedelta(seconds=lease_seconds),
                "updated_at": now,
            }
        )
        db["queue_jobs"][best_project_id][best_index] = claimed.model_dump(mode="json")
        task = self.get_scheduler_task(best_project_id, claimed.task_id)
        if task is not None:
            db["scheduler_tasks"].setdefault(best_project_id, [])
            for task_index, raw_task in enumerate(db["scheduler_tasks"][best_project_id]):
                if raw_task["id"] == task.id:
                    db["scheduler_tasks"][best_project_id][task_index] = task.model_copy(
                        update={
                            "active_queue_job_id": claimed.id,
                            "status": "running" if task.status == "queued" else task.status,
                            "updated_at": now,
                        }
                    ).model_dump(mode="json")
                    break
        self._write(db)
        return claimed

    def finish_queue_job(
        self,
        project_id: str,
        job_id: str,
        *,
        status: str,
        result_summary: str = "",
        last_error: str = "",
    ) -> QueueJob | None:
        db = self._read()
        items = db["queue_jobs"].get(project_id, [])
        for index, raw in enumerate(items):
            if raw["id"] != job_id:
                continue
            job = QueueJob.model_validate(raw)
            updated = job.model_copy(
                update={
                    "status": status,
                    "lease_expires_at": None,
                    "result_summary": result_summary or job.result_summary,
                    "last_error": last_error,
                    "updated_at": datetime.now(UTC),
                }
            )
            items[index] = updated.model_dump(mode="json")
            task = self.get_scheduler_task(project_id, updated.task_id)
            if task is not None:
                for task_index, raw_task in enumerate(db["scheduler_tasks"].get(project_id, [])):
                    if raw_task["id"] == task.id:
                        db["scheduler_tasks"][project_id][task_index] = task.model_copy(
                            update={"active_queue_job_id": None, "updated_at": datetime.now(UTC)}
                        ).model_dump(mode="json")
                        break
            self._write(db)
            return updated
        return None

    def build_worker_snapshot(self, payload: dict[str, Any]) -> WorkerSnapshot:
        backlog = sum(1 for item in self.list_all_queue_jobs() if item.status in {"pending", "leased"})
        return WorkerSnapshot.model_validate(
            {
                **payload,
                "queue_backlog": backlog,
            }
        )

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

    def is_review_current(self, project_id: str, review: ReviewReport) -> bool:
        chapter = self.get_chapter(project_id, review.chapter_id)
        return chapter is not None and chapter.is_current

    def list_current_reviews(self, project_id: str) -> list[ReviewReport]:
        return [item for item in self.list_reviews(project_id) if self.is_review_current(project_id, item)]

    def is_continuity_report_current(self, project_id: str, report: ContinuityReport) -> bool:
        chapter = self.get_chapter(project_id, report.chapter_id)
        return chapter is not None and chapter.is_current

    def list_current_continuity_reports(self, project_id: str) -> list[ContinuityReport]:
        return [
            item
            for item in self.list_continuity_reports(project_id)
            if self.is_continuity_report_current(project_id, item)
        ]

    def is_reader_council_report_current(self, project_id: str, report: ReaderCouncilReport) -> bool:
        chapter = self.get_chapter(project_id, report.chapter_id)
        return chapter is not None and chapter.is_current

    def list_current_reader_council_reports(self, project_id: str) -> list[ReaderCouncilReport]:
        return [
            item
            for item in self.list_reader_council_reports(project_id)
            if self.is_reader_council_report_current(project_id, item)
        ]

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

    def list_llm_diagnostics(self) -> list[LLMDiagnosticResult]:
        db = self._read()
        items = db.get("llm_diagnostics", [])
        return [LLMDiagnosticResult.model_validate(item) for item in items]

    def add_llm_diagnostic(self, result: LLMDiagnosticResult) -> LLMDiagnosticResult:
        db = self._read()
        items = db.setdefault("llm_diagnostics", [])
        items.append(result.model_dump(mode="json"))
        limit = get_settings().llm_diagnostic_limit
        if limit > 0 and len(items) > limit:
            items = items[-limit:]
        db["llm_diagnostics"] = items
        self._write(db)
        return result

    def list_llm_test_runs(self) -> list[LLMTestRunResult]:
        db = self._read()
        items = db.get("llm_test_runs", [])
        return [LLMTestRunResult.model_validate(item) for item in items]

    def add_llm_test_run(self, result: LLMTestRunResult) -> LLMTestRunResult:
        db = self._read()
        items = db.setdefault("llm_test_runs", [])
        items.append(result.model_dump(mode="json"))
        limit = get_settings().llm_test_run_limit
        if limit > 0 and len(items) > limit:
            items = items[-limit:]
        db["llm_test_runs"] = items
        self._write(db)
        return result

    def list_llm_chapter_preflights(self, project_id: str | None = None) -> list[LLMChapterPreflightResult]:
        db = self._read()
        items = db.get("llm_chapter_preflights", [])
        results = [LLMChapterPreflightResult.model_validate(item) for item in items]
        if project_id is None:
            return results
        return [item for item in results if item.project_id == project_id]

    def add_llm_chapter_preflight(self, result: LLMChapterPreflightResult) -> LLMChapterPreflightResult:
        db = self._read()
        items = db.setdefault("llm_chapter_preflights", [])
        items.append(result.model_dump(mode="json"))
        limit = get_settings().llm_chapter_preflight_limit
        if limit > 0 and len(items) > limit:
            items = items[-limit:]
        db["llm_chapter_preflights"] = items
        self._write(db)
        return result

    def replace_chapter_canon_projection(self, project_id: str, chapter_number: int) -> dict[str, int]:
        db = self._read()
        removed_counts = self._replace_chapter_canon_projection_in_db(db, project_id, chapter_number)
        self._write(db)
        return removed_counts

    def _replace_chapter_canon_projection_in_db(
        self,
        db: dict[str, Any],
        project_id: str,
        chapter_number: int,
    ) -> dict[str, int]:
        projection_keys = [
            "events",
            "character_states",
            "relationship_edges",
            "timeline_nodes",
            "timeline_constraints",
            "extracted_updates",
            "snapshots",
            "versions",
            "hook_state_changes",
        ]
        removed_counts: dict[str, int] = {}
        for key in projection_keys:
            items = db[key].get(project_id, [])
            kept = [item for item in items if item.get("chapter_number") != chapter_number]
            removed_counts[key] = len(items) - len(kept)
            db[key][project_id] = kept

        db["relationship_edges"][project_id] = self._normalize_relationship_edges(
            db["relationship_edges"].get(project_id, [])
        )
        db["timeline_constraints"][project_id] = self._normalize_timeline_constraints(
            db["timeline_constraints"].get(project_id, [])
        )
        db["hook_records"][project_id] = self._rebuild_hook_records(
            project_id,
            db["hook_state_changes"].get(project_id, []),
        )
        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break
        return removed_counts

    def apply_chapter_canon_projection(
        self,
        project_id: str,
        chapter: ChapterDraft,
        active_character_ids: list[str],
        extracted_update: ExtractedUpdate,
        created_event: Event,
        created_state: CharacterState | None,
        relationship_edges: list[CharacterRelationshipEdge],
        timeline_node: TimelineNode,
        timeline_constraints: list[TimelineConstraint],
        hook_records: list[HookRecord],
        hook_state_changes: list[HookStateChange],
    ) -> tuple[ExtractedUpdate, Snapshot, VersionRecord]:
        db = self._read()
        self._replace_chapter_canon_projection_in_db(db, project_id, chapter.chapter_number)

        db["events"].setdefault(project_id, []).append(created_event.model_dump(mode="json"))
        if created_state is not None:
            db["character_states"].setdefault(project_id, []).append(created_state.model_dump(mode="json"))
        db["relationship_edges"].setdefault(project_id, []).extend(
            item.model_dump(mode="json") for item in relationship_edges
        )
        db["relationship_edges"][project_id] = self._normalize_relationship_edges(
            db["relationship_edges"].get(project_id, [])
        )

        db["timeline_nodes"].setdefault(project_id, []).append(timeline_node.model_dump(mode="json"))
        synced_constraints = self._sync_timeline_constraints_in_db(
            db,
            project_id,
            chapter.chapter_number,
            timeline_constraints,
        )
        self._resolve_stale_timeline_constraints_in_db(db, project_id, chapter.chapter_number)
        db["timeline_constraints"][project_id] = self._normalize_timeline_constraints(
            db["timeline_constraints"].get(project_id, [])
        )

        db["extracted_updates"].setdefault(project_id, []).append(extracted_update.model_dump(mode="json"))
        db["hook_state_changes"].setdefault(project_id, []).extend(
            item.model_dump(mode="json") for item in hook_state_changes
        )
        rebuilt_hook_records = {
            item["id"]: item for item in self._rebuild_hook_records(project_id, db["hook_state_changes"].get(project_id, []))
        }
        for record in hook_records:
            rebuilt_hook_records[record.id] = record.model_dump(mode="json")
        db["hook_records"][project_id] = list(rebuilt_hook_records.values())

        active_hook_ids = [
            item["id"]
            for item in db["hook_records"].get(project_id, [])
            if item.get("status") in {"open", "active"}
        ]
        normalized_relationship_edge_ids = [
            item["id"]
            for item in db["relationship_edges"].get(project_id, [])
            if item.get("chapter_number") == chapter.chapter_number
        ]
        normalized_timeline_node_ids = [
            item["id"]
            for item in db["timeline_nodes"].get(project_id, [])
            if item.get("chapter_number") == chapter.chapter_number
        ]
        normalized_constraint_descriptions = [
            item.description for item in synced_constraints
        ]
        normalized_extracted_update = extracted_update.model_copy(
            update={
                "relationship_edge_ids": normalized_relationship_edge_ids,
                "timeline_node_ids": normalized_timeline_node_ids,
                "timeline_constraints": normalized_constraint_descriptions,
            }
        )
        extracted_updates = db["extracted_updates"].setdefault(project_id, [])
        extracted_updates[-1] = normalized_extracted_update.model_dump(mode="json")

        snapshot = Snapshot(
            project_id=project_id,
            chapter_number=chapter.chapter_number,
            chapter_id=chapter.id,
            chapter_title=chapter.title,
            active_character_ids=active_character_ids,
            relationship_edge_ids=normalized_relationship_edge_ids,
            timeline_node_ids=normalized_timeline_node_ids,
            active_hook_ids=active_hook_ids,
            recent_event_ids=[created_event.id],
            summary=(
                f"第 {chapter.chapter_number} 章快照，包含 1 条事件、"
                f"{len(normalized_extracted_update.character_state_ids)} 条角色状态、"
                f"{len(normalized_relationship_edge_ids)} 条关系边、"
                f"{len(normalized_timeline_node_ids)} 个时间线节点，以及 "
                f"{len(normalized_extracted_update.new_hooks) + len(normalized_extracted_update.active_hooks)} 条活跃伏笔。"
            ),
        )
        db["snapshots"].setdefault(project_id, []).append(snapshot.model_dump(mode="json"))

        version = VersionRecord(
            project_id=project_id,
            chapter_number=chapter.chapter_number,
            chapter_id=chapter.id,
            snapshot_id=snapshot.id,
            extracted_update_id=normalized_extracted_update.id,
            version_label=f"chapter-{chapter.chapter_number}-v1",
            change_summary=f"生成《{chapter.title}》并写回 canon。",
        )
        db["versions"].setdefault(project_id, []).append(version.model_dump(mode="json"))

        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break
        self._write(db)
        return normalized_extracted_update, snapshot, version

    def _split_items_from_chapter(
        self,
        items: list[dict[str, Any]],
        first_removed_chapter: int,
        chapter_key: str = "chapter_number",
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        for item in items:
            chapter_number = item.get(chapter_key, 0)
            if chapter_number is None or chapter_number < first_removed_chapter:
                kept.append(item)
            else:
                removed.append(item)
        return kept, removed

    def _normalize_relationship_edges(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        edges = [CharacterRelationshipEdge.model_validate(item) for item in items]
        edges.sort(key=lambda item: (item.chapter_number, item.created_at, item.id))
        normalized: list[dict[str, Any]] = []
        latest_index_by_pair: dict[str, int] = {}
        for edge in edges:
            pair_key = edge.pair_key or "::".join(
                sorted([edge.source_character_id, edge.target_character_id])
            )
            previous_index = latest_index_by_pair.get(pair_key)
            previous_edge_id = None
            if previous_index is not None:
                previous = CharacterRelationshipEdge.model_validate(normalized[previous_index])
                normalized[previous_index] = previous.model_copy(
                    update={"is_current": False}
                ).model_dump(mode="json")
                previous_edge_id = previous.id
            normalized_edge = edge.model_copy(
                update={
                    "pair_key": pair_key,
                    "previous_edge_id": previous_edge_id,
                    "is_current": True,
                }
            )
            normalized.append(normalized_edge.model_dump(mode="json"))
            latest_index_by_pair[pair_key] = len(normalized) - 1
        return normalized

    def _normalize_timeline_constraints(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        constraints = [TimelineConstraint.model_validate(item) for item in items]
        constraints.sort(key=lambda item: (item.chapter_number, item.created_at, item.id))
        grouped: dict[str, list[TimelineConstraint]] = {}
        group_order: list[str] = []
        for constraint in constraints:
            evolution_key = self._timeline_constraint_evolution_key(constraint)
            if evolution_key not in grouped:
                grouped[evolution_key] = []
                group_order.append(evolution_key)
            grouped[evolution_key].append(constraint)

        normalized: list[dict[str, Any]] = []
        for evolution_key in group_order:
            chain = grouped[evolution_key]
            last_index = len(chain) - 1
            for index, constraint in enumerate(chain):
                previous = chain[index - 1] if index > 0 else None
                is_latest = index == last_index
                normalized_constraint = constraint.model_copy(
                    update={
                        "evolution_key": evolution_key,
                        "previous_constraint_id": previous.id if previous is not None else None,
                        "is_current": is_latest and constraint.status != "resolved",
                    }
                )
                normalized.append(normalized_constraint.model_dump(mode="json"))
        return normalized

    def _rebuild_hook_records(
        self,
        project_id: str,
        changes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rebuilt_hooks: dict[str, HookRecord] = {}
        for item in changes:
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
        return [item.model_dump(mode="json") for item in rebuilt_hooks.values()]

    def _truncate_project_records(
        self,
        db: dict[str, Any],
        project_id: str,
        first_removed_chapter: int,
    ) -> dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
        keys = [
            "chapters",
            "events",
            "character_states",
            "extracted_updates",
            "snapshots",
            "versions",
            "chapter_plans",
            "runs",
            "chapter_metrics",
            "reviews",
            "continuity_reports",
            "reader_council_reports",
            "hook_state_changes",
            "relationship_edges",
            "timeline_nodes",
            "timeline_constraints",
        ]
        truncated: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
        for key in keys:
            kept, removed = self._split_items_from_chapter(
                db[key].get(project_id, []),
                first_removed_chapter,
            )
            truncated[key] = (kept, removed)
            db[key][project_id] = kept
        db["relationship_edges"][project_id] = self._normalize_relationship_edges(
            db["relationship_edges"].get(project_id, [])
        )
        db["timeline_constraints"][project_id] = self._normalize_timeline_constraints(
            db["timeline_constraints"].get(project_id, [])
        )
        db["hook_records"][project_id] = self._rebuild_hook_records(
            project_id,
            db["hook_state_changes"].get(project_id, []),
        )
        return truncated

    def truncate_project_from_chapter(self, project_id: str, first_removed_chapter: int) -> dict[str, int]:
        db = self._read()
        truncated = self._truncate_project_records(db, project_id, first_removed_chapter)
        for index, project_data in enumerate(db["projects"]):
            if project_data["id"] == project_id:
                project_data["updated_at"] = datetime.now(UTC).isoformat()
                db["projects"][index] = project_data
                break
        self._write(db)
        return {key: len(removed) for key, (_, removed) in truncated.items()}

    def rollback_to_chapter(
        self,
        project_id: str,
        target_chapter_number: int,
        reason: str,
    ) -> tuple[RollbackResult, RetconPatch]:
        db = self._read()
        truncated = self._truncate_project_records(db, project_id, target_chapter_number + 1)
        _chapters_kept, chapters_removed = truncated["chapters"]
        _events_kept, events_removed = truncated["events"]
        _states_kept, states_removed = truncated["character_states"]
        _extracts_kept, _extracts_removed = truncated["extracted_updates"]
        _snapshots_kept, snapshots_removed = truncated["snapshots"]
        _versions_kept, versions_removed = truncated["versions"]
        _plans_kept, plans_removed = truncated["chapter_plans"]

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
