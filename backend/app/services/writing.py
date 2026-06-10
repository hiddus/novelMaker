import json
import time
from datetime import UTC, datetime
from urllib.parse import urljoin
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ChapterPlan,
    ContextPack,
    Project,
    ReviewReport,
    RewriteChapterRequest,
    WriteChapterRequest,
    WritingRun,
)


def _estimate_tokens(text: str) -> int:
    # A lightweight approximation good enough for budgeting and run logs.
    return max(1, len(text) // 4)


def _truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else f"{text[: max_chars - 3]}..."


def _provider_label() -> str:
    settings = get_settings()
    return "DeepSeek" if settings.llm_provider.lower() == "deepseek" else "OpenAI"


def estimate_tokens(text: str) -> int:
    return _estimate_tokens(text)


def provider_label() -> str:
    return _provider_label()


def resolve_writer_mode(requested_mode: str) -> str:
    settings = get_settings()
    if requested_mode == "auto":
        return "mock" if settings.use_mock_writer or not settings.openai_api_key else "openai"
    return requested_mode


def call_openai_compatible(messages: list[dict[str, str]], *, temperature: float = 0.9) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置，无法使用 LLM writer")

    request_body = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
    }

    request = Request(
        urljoin(settings.openai_base_url.rstrip("/") + "/", "chat/completions"),
        method="POST",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
    )

    last_error: Exception | None = None
    for attempt in range(settings.openai_max_retries + 1):
        try:
            with urlopen(request, timeout=settings.openai_timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except (HTTPError, URLError) as exc:
            last_error = exc
            if attempt >= settings.openai_max_retries:
                raise RuntimeError(f"{_provider_label()} 请求失败: {exc}") from exc
            time.sleep(settings.openai_retry_backoff_seconds * (attempt + 1))

    raise RuntimeError(f"{_provider_label()} 请求失败: {last_error}")


def _resolve_plan(payload: WriteChapterRequest, plans: list[ChapterPlan]) -> ChapterPlan | None:
    if payload.plan_id is not None:
        return next((plan for plan in plans if plan.id == payload.plan_id), None)
    return next((plan for plan in plans if plan.chapter_number == payload.chapter_number), None)


def _mock_chapter(
    project: Project,
    payload: WriteChapterRequest,
    matched_plan: ChapterPlan | None,
) -> ChapterDraft:
    settings = get_settings()

    title = f"第{payload.chapter_number}章 新的推进"
    summary = "根据章节规划生成的第一版草稿。"

    if matched_plan is None:
        content = (
            f"《{project.title}》第{payload.chapter_number}章草稿。\n\n"
            "当前未找到章节规划，因此本章仅生成一个最小示例正文。"
        )
    else:
        beat_lines = "\n".join(f"- {beat}" for beat in matched_plan.beats)
        content = (
            f"《{project.title}》第{payload.chapter_number}章草稿\n\n"
            f"章节目标：{matched_plan.goal}\n"
            f"核心冲突：{matched_plan.conflict}\n"
            f"结尾钩子：{matched_plan.hook}\n\n"
            "节奏设计：\n"
            f"{beat_lines}\n\n"
            "正文示例：\n"
            "主角在外部压力与内部欲望之间做出选择，推动本章核心冲突落地，"
            "并在结尾留下下一章的行动钩子。"
        )
        summary = matched_plan.goal

    return ChapterDraft(
        chapter_number=payload.chapter_number,
        title=title,
        content=content,
        summary=summary,
        source="mock" if settings.use_mock_writer else "llm",
    )


def _openai_prompt(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    plan_text = (
        "无章节规划"
        if context_pack.chapter_plan is None
        else (
            f"章节目标：{context_pack.chapter_plan.goal}\n"
            f"核心冲突：{context_pack.chapter_plan.conflict}\n"
            f"结尾钩子：{context_pack.chapter_plan.hook}"
        )
    )
    character_lines = "\n".join(
        f"- {character.name} / {character.role} / {character.realm}"
        for character in context_pack.active_characters
    ) or "- 暂无角色"
    hook_lines = "\n".join(
        f"- {item.status} / 第{item.created_in_chapter}章 / {item.content}"
        for item in context_pack.open_hooks
    ) or "- 暂无开放伏笔"
    constraint_lines = "\n".join(f"- {item}" for item in context_pack.hard_constraints) or "- 无"
    budget_lines = "\n".join(
        f"- {key}: {value}" for key, value in context_pack.token_budget.items()
    ) or "- 无"

    settings = get_settings()
    prompt = (
        f"你是网络小说写作 Agent，为《{project.title}》生成第{payload.chapter_number}章草稿。\n\n"
        f"题材：{project.genre}\n"
        f"基调：{payload.tone}\n"
        f"项目 premise：{project.premise}\n\n"
        f"{plan_text}\n\n"
        f"活跃角色：\n{character_lines}\n\n"
        f"开放伏笔：\n{hook_lines}\n\n"
        f"Story Bible 摘要：\n{context_pack.story_bible_summary}\n\n"
        f"最近事件摘要：\n{context_pack.event_summary}\n\n"
        f"角色状态摘要：\n{context_pack.character_state_summary}\n\n"
        f"补丁摘要：\n{context_pack.patch_summary}\n\n"
        f"检索优先级：\n{chr(10).join(f'- {item}' for item in context_pack.retrieval_priorities)}\n\n"
        f"上下文说明：\n{context_pack.context_summary}\n\n"
        f"硬约束：\n{constraint_lines}\n\n"
        f"预算说明：\n{budget_lines}\n\n"
        "请输出中文网络小说章节正文，包含标题和至少 6 段内容。"
    )
    return _truncate(prompt, settings.writer_max_prompt_chars)


def build_chapter_prompt(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    return _openai_prompt(project, payload, context_pack)


def _rewrite_prompt(
    project: Project,
    chapter: ChapterDraft,
    review: ReviewReport,
    payload: RewriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    character_lines = "\n".join(
        f"- {character.name} / {character.role} / {character.realm}"
        for character in context_pack.active_characters
    ) or "- 暂无角色"
    hook_lines = "\n".join(
        f"- {item.status} / 第{item.created_in_chapter}章 / {item.content}"
        for item in context_pack.open_hooks
    ) or "- 暂无开放伏笔"
    findings = "\n".join(f"- {item}" for item in review.findings) or "- 无"
    suggestions = "\n".join(f"- {item}" for item in review.rewrite_suggestions) or "- 无"
    constraint_lines = "\n".join(f"- {item}" for item in context_pack.hard_constraints) or "- 无"
    note = payload.note.strip() or "无额外说明"

    settings = get_settings()
    prompt = (
        f"你是网络小说 Rewrite Agent，请重写《{project.title}》第{chapter.chapter_number}章。\n\n"
        f"题材：{project.genre}\n"
        f"基调：{payload.tone}\n"
        f"项目 premise：{project.premise}\n\n"
        f"当前章节标题：{chapter.title}\n"
        f"当前章节摘要：{chapter.summary}\n\n"
        f"原正文：\n{chapter.content}\n\n"
        f"评审发现：\n{findings}\n\n"
        f"重写建议：\n{suggestions}\n\n"
        f"人工补充：\n- {note}\n\n"
        f"活跃角色：\n{character_lines}\n\n"
        f"开放伏笔：\n{hook_lines}\n\n"
        f"Story Bible 摘要：\n{context_pack.story_bible_summary}\n\n"
        f"最近事件摘要：\n{context_pack.event_summary}\n\n"
        f"角色状态摘要：\n{context_pack.character_state_summary}\n\n"
        f"硬约束：\n{constraint_lines}\n\n"
        "要求：保留可用剧情骨架，优先修复上述问题，不得破坏关键设定与连续性。"
        "请输出中文网络小说章节正文，包含标题和至少 6 段内容。"
    )
    return _truncate(prompt, settings.writer_max_prompt_chars)


def _generate_with_openai_prompt(
    prompt: str,
    chapter_number: int,
    summary: str,
) -> tuple[ChapterDraft, int, int]:
    content = call_openai_compatible(
        [
            {
                "role": "system",
                "content": "你是一个擅长中文长篇网文创作的写作 Agent。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.9,
    )
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    title = lines[0] if lines else f"第{chapter_number}章"
    summary = (
        summary
    )

    prompt_tokens_estimate = _estimate_tokens(prompt)
    completion_tokens_estimate = _estimate_tokens(content)

    return ChapterDraft(
        chapter_number=chapter_number,
        title=title,
        content=content,
        summary=summary,
        source="llm",
    ), prompt_tokens_estimate, completion_tokens_estimate


def _generate_with_openai(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> tuple[ChapterDraft, int, int]:
    prompt = _openai_prompt(project, payload, context_pack)
    summary = (
        context_pack.chapter_plan.goal
        if context_pack.chapter_plan is not None
        else "基于上下文生成的章节草稿"
    )
    return _generate_with_openai_prompt(prompt, payload.chapter_number, summary)


def create_chapter_draft(
    project: Project,
    payload: WriteChapterRequest,
    plans: list[ChapterPlan],
    context_pack: ContextPack,
) -> tuple[WritingRun, ChapterDraft]:
    matched_plan = _resolve_plan(payload, plans)
    settings = get_settings()
    requested_mode = payload.writer_mode
    writer_mode = resolve_writer_mode(requested_mode)

    run = WritingRun(
        project_id=project.id,
        chapter_number=payload.chapter_number,
        status="running",
        writer_mode=writer_mode,
        message="正在生成章节草稿",
        model_name=settings.openai_model if writer_mode == "openai" else "mock-writer",
    )

    try:
        if writer_mode == "openai":
            run.attempts = settings.openai_max_retries + 1
            chapter, prompt_tokens, completion_tokens = _generate_with_openai(
                project,
                payload,
                context_pack,
            )
            run.prompt_tokens_estimate = prompt_tokens
            run.completion_tokens_estimate = completion_tokens
            run.total_tokens_estimate = prompt_tokens + completion_tokens
        else:
            chapter = _mock_chapter(project, payload, matched_plan)
            run.prompt_tokens_estimate = _estimate_tokens(json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False))
            run.completion_tokens_estimate = _estimate_tokens(chapter.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate
        run.status = "completed"
        run.message = "章节草稿已生成"
        run.updated_at = datetime.now(UTC)
        return run, chapter
    except Exception as exc:
        run.error_history.append(str(exc))
        if requested_mode == "auto":
            fallback_chapter = _mock_chapter(project, payload, matched_plan)
            run.status = "completed"
            run.fallback_used = True
            run.message = f"{_provider_label()} 失败，已自动降级到 mock writer: {exc}"
            run.model_name = "mock-writer"
            run.prompt_tokens_estimate = _estimate_tokens(
                json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False)
            )
            run.completion_tokens_estimate = _estimate_tokens(fallback_chapter.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate
            run.updated_at = datetime.now(UTC)
            return run, fallback_chapter
        run.status = "failed"
        run.message = str(exc)
        run.updated_at = datetime.now(UTC)
        raise


def create_rewrite_draft(
    project: Project,
    payload: RewriteChapterRequest,
    chapter: ChapterDraft,
    review: ReviewReport,
    context_pack: ContextPack,
    revision_number: int,
) -> tuple[WritingRun, ChapterDraft]:
    settings = get_settings()
    requested_mode = payload.writer_mode
    writer_mode = resolve_writer_mode(requested_mode)

    run = WritingRun(
        project_id=project.id,
        chapter_number=chapter.chapter_number,
        status="running",
        writer_mode=writer_mode,
        message=f"正在重写第 {chapter.chapter_number} 章草稿",
        model_name=settings.openai_model if writer_mode == "openai" else "mock-rewriter",
    )

    rewrite_summary = f"{chapter.summary}（第 {revision_number} 版修订）"
    try:
        if writer_mode == "openai":
            run.attempts = settings.openai_max_retries + 1
            prompt = _rewrite_prompt(project, chapter, review, payload, context_pack)
            rewritten, prompt_tokens, completion_tokens = _generate_with_openai_prompt(
                prompt,
                chapter.chapter_number,
                rewrite_summary,
            )
            run.prompt_tokens_estimate = prompt_tokens
            run.completion_tokens_estimate = completion_tokens
            run.total_tokens_estimate = prompt_tokens + completion_tokens
        else:
            suggestions = "；".join(review.rewrite_suggestions) or "补强章节目标、冲突与钩子"
            rewritten = ChapterDraft(
                chapter_number=chapter.chapter_number,
                title=f"{chapter.title}（修订版）",
                content=(
                    f"{chapter.title}（修订版）\n\n"
                    f"原章节摘要：{chapter.summary}\n"
                    f"重点修复：{suggestions}\n"
                    f"人工补充：{payload.note or '无'}\n\n"
                    "修订正文：\n"
                    "本次重写会保留原有剧情推进骨架，补强章节目标的显性推进、冲突压迫感、"
                    "角色互动与结尾钩子，使章节更适合继续进入评审与后续 canon 写回。"
                ),
                summary=rewrite_summary,
                source="mock" if settings.use_mock_writer else "llm",
            )
            run.prompt_tokens_estimate = _estimate_tokens(
                json.dumps(
                    {
                        "chapter": chapter.model_dump(mode="json"),
                        "review": review.model_dump(mode="json"),
                        "context": context_pack.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                )
            )
            run.completion_tokens_estimate = _estimate_tokens(rewritten.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate

        rewritten = rewritten.model_copy(
            update={
                "revision_number": revision_number,
                "parent_chapter_id": chapter.id,
                "rewrite_source_review_id": review.id,
                "is_current": True,
            }
        )
        run.status = "completed"
        run.message = f"第 {chapter.chapter_number} 章修订稿已生成"
        run.updated_at = datetime.now(UTC)
        return run, rewritten
    except Exception as exc:
        run.error_history.append(str(exc))
        if requested_mode == "auto":
            fallback_payload = payload.model_copy(update={"writer_mode": "mock"})
            fallback_run, fallback_chapter = create_rewrite_draft(
                project,
                fallback_payload,
                chapter,
                review,
                context_pack,
                revision_number,
            )
            fallback_run.fallback_used = True
            fallback_run.error_history = run.error_history + fallback_run.error_history
            fallback_run.message = f"{_provider_label()} 失败，已自动降级到 mock rewriter: {exc}"
            return fallback_run, fallback_chapter
        run.status = "failed"
        run.message = str(exc)
        run.updated_at = datetime.now(UTC)
        raise
