from app.schemas.domain import ProjectDetail
from app.services.memory import get_memory_index_status
from app.services.ops import build_run_ops_summary
from app.services.state_graph_diagnostics import build_state_graph_diagnostics
from app.services.state_graph_repair import attach_state_graph_repair_suggestions, build_state_graph_recovery_plan
from app.services.store import store


def get_project_detail(project_id: str) -> ProjectDetail:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("project not found")

    runs = store.list_runs(project_id)
    latest_run = runs[-1] if runs else None
    state_graph_diagnostics = attach_state_graph_repair_suggestions(
        project_id,
        build_state_graph_diagnostics(project_id),
    )
    state_graph_recovery_plan = build_state_graph_recovery_plan(state_graph_diagnostics)

    return ProjectDetail(
        project=project,
        story_bible=store.get_story_bible(project_id),
        governance_policy=store.get_governance_policy(project_id),
        characters=store.list_characters(project_id),
        character_states=store.list_character_states(project_id),
        relationship_edges=store.list_relationship_edges(project_id),
        timeline_nodes=store.list_timeline_nodes(project_id),
        timeline_constraints=store.list_timeline_constraints(project_id),
        events=store.list_events(project_id),
        chapter_plans=store.list_chapter_plans(project_id),
        chapters=store.list_chapters(project_id),
        extracted_updates=store.list_extracted_updates(project_id),
        snapshots=store.list_snapshots(project_id),
        versions=store.list_versions(project_id),
        task_runs=store.list_task_runs(project_id),
        retcon_patches=store.list_retcon_patches(project_id),
        hook_records=store.list_hook_records(project_id),
        hook_state_changes=store.list_hook_state_changes(project_id),
        scheduler_tasks=store.list_scheduler_tasks(project_id),
        queue_jobs=store.list_queue_jobs(project_id),
        reviews=store.list_reviews(project_id),
        continuity_reports=store.list_continuity_reports(project_id),
        reader_council_reports=store.list_reader_council_reports(project_id),
        governance_events=store.list_governance_events(project_id),
        long_term_memories=store.list_long_term_memories(project_id),
        memory_retrieval_traces=store.list_memory_retrieval_traces(project_id),
        memory_index_status=get_memory_index_status(project_id),
        chapter_metrics=store.list_chapter_metrics(project_id),
        metrics_summary=store.build_metrics_summary(project_id),
        ops_summary=build_run_ops_summary(project_id),
        state_graph_diagnostics=state_graph_diagnostics,
        state_graph_recovery_plan=state_graph_recovery_plan,
        latest_run=latest_run,
    )
