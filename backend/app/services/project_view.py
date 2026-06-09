from app.schemas.domain import ProjectDetail
from app.services.store import store


def get_project_detail(project_id: str) -> ProjectDetail:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("project not found")

    runs = store.list_runs(project_id)
    latest_run = runs[-1] if runs else None

    return ProjectDetail(
        project=project,
        story_bible=store.get_story_bible(project_id),
        characters=store.list_characters(project_id),
        character_states=store.list_character_states(project_id),
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
        reviews=store.list_reviews(project_id),
        continuity_reports=store.list_continuity_reports(project_id),
        reader_council_reports=store.list_reader_council_reports(project_id),
        chapter_metrics=store.list_chapter_metrics(project_id),
        metrics_summary=store.build_metrics_summary(project_id),
        latest_run=latest_run,
    )
