from app.schemas.domain import (
    ChapterDraft,
    ChapterMetric,
    ExtractedUpdate,
    ReaderCouncilReport,
    ReviewReport,
    WritingRun,
)


def _estimated_cost_usd(run: WritingRun) -> float:
    # Rough blended estimate for budgeting and trend monitoring.
    return round(run.total_tokens_estimate * 0.000002, 6)


def build_chapter_metric(
    project_id: str,
    chapter: ChapterDraft,
    run: WritingRun,
    extracted_update: ExtractedUpdate,
    review: ReviewReport,
    reader_council_report: ReaderCouncilReport,
) -> ChapterMetric:
    warnings: list[str] = []
    content_length = len(chapter.content)

    quality_score = 5.0
    if content_length >= 600:
        quality_score += 2.0
    if extracted_update.hook_changes:
        quality_score += 1.0
    if chapter.source == "llm":
        quality_score += 1.0
    if run.fallback_used:
        quality_score -= 1.0
        warnings.append("发生了模型降级，当前章节来自 fallback。")
    if content_length < 300:
        warnings.append("章节内容偏短。")
        quality_score -= 1.0

    extraction_score = 3.0
    extraction_score += min(2.0, len(extracted_update.locations) * 0.5)
    extraction_score += min(2.0, len(extracted_update.emotions) * 0.5)
    extraction_score += min(2.0, len(extracted_update.relationship_signals) * 0.5)
    extraction_score += min(1.0, len(extracted_update.goals) * 0.5)

    hook_score = 3.0 + min(4.0, len(extracted_update.hook_changes) * 1.5)
    if not extracted_update.hook_changes:
        warnings.append("当前章节未识别到明确钩子。")
    if reader_council_report.status == "weak":
        warnings.append("Reader Council 认为当前章节追读驱动力不足。")

    return ChapterMetric(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        run_id=run.id,
        model_name=run.model_name,
        source=chapter.source,
        fallback_used=run.fallback_used,
        prompt_tokens_estimate=run.prompt_tokens_estimate,
        completion_tokens_estimate=run.completion_tokens_estimate,
        total_tokens_estimate=run.total_tokens_estimate,
        estimated_cost_usd=_estimated_cost_usd(run),
        content_length=content_length,
        quality_score=round(max(0.0, min(10.0, quality_score)), 2),
        extraction_score=round(max(0.0, min(10.0, extraction_score)), 2),
        hook_score=round(max(0.0, min(10.0, hook_score)), 2),
        review_score=review.overall_score,
        reader_score=reader_council_report.overall_score,
        warnings=warnings,
    )
