from __future__ import annotations

import time
from urllib.parse import urljoin

from app.core.config import get_settings
from app.schemas.domain import (
    GovernanceDecision,
    LLMChapterPreflightRequest,
    LLMChapterPreflightResult,
    LLMDiagnosticResult,
    LLMStatus,
    WriteChapterRequest,
    LLMTestRunRequest,
    LLMTestRunResult,
)
from app.services.context_engine import build_context_pack
from app.services.store import store
from app.services.writing import (
    build_chapter_prompt,
    call_openai_compatible,
    create_chapter_draft,
    estimate_tokens,
    provider_label,
    resolve_writer_mode,
)


def _mask_api_key(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def get_llm_status() -> LLMStatus:
    settings = get_settings()
    warnings: list[str] = []
    api_key_configured = bool(settings.openai_api_key)
    route = "mock" if settings.use_mock_writer or not api_key_configured else "openai"

    if settings.use_mock_writer:
        readiness = "degraded" if api_key_configured else "blocked"
        detail = "当前启用了 mock writer，自动写作不会走真实 LLM。"
        warnings.append("`NOVELMAKER_USE_MOCK_WRITER=true`，主链会优先走 mock writer。")
    elif api_key_configured:
        readiness = "ready"
        detail = "真实 OpenAI-compatible 写作链路已具备运行条件。"
    else:
        readiness = "blocked"
        detail = "缺少 OPENAI_API_KEY，无法执行真实 LLM 写作。"
        warnings.append("缺少 `OPENAI_API_KEY`。")

    if not settings.openai_base_url:
        readiness = "blocked"
        detail = "未配置 OpenAI-compatible base URL。"
        warnings.append("缺少 `NOVELMAKER_OPENAI_BASE_URL`。")

    if not settings.openai_model:
        readiness = "blocked"
        detail = "未配置模型名称。"
        warnings.append("缺少 `NOVELMAKER_OPENAI_MODEL`。")

    if settings.llm_provider.lower() == "deepseek":
        warnings.append("当前 provider 为 DeepSeek，经 OpenAI-compatible 协议接入。")

    return LLMStatus(
        provider=settings.llm_provider,
        provider_label=provider_label(),
        readiness=readiness,
        writer_route=route,
        use_mock_writer=settings.use_mock_writer,
        api_key_configured=api_key_configured,
        api_key_masked=_mask_api_key(settings.openai_api_key),
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        timeout_seconds=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
        can_run_live=api_key_configured and not settings.use_mock_writer,
        can_run_auto_mode=settings.use_mock_writer or api_key_configured,
        detail=detail,
        warnings=warnings,
    )


def ensure_writer_mode_available(requested_mode: str) -> None:
    status = get_llm_status()
    resolved_mode = status.writer_route if requested_mode == "auto" else requested_mode
    if resolved_mode != "openai":
        return
    if status.can_run_live:
        return
    raise ValueError(
        f"{status.provider_label} 未就绪，无法以 openai 模式运行。"
        "请检查 OPENAI_API_KEY、base_url、model，或改用 auto/mock。"
    )


def build_llm_block_decision(requested_mode: str) -> GovernanceDecision | None:
    status = get_llm_status()
    resolved_mode = status.writer_route if requested_mode == "auto" else requested_mode
    if resolved_mode != "openai" or status.can_run_live:
        return None
    return GovernanceDecision(
        action="pause",
        status="blocked",
        signal="llm",
        reason=f"{status.provider_label} 未就绪，任务已暂停",
        details=[
            status.detail,
            f"provider={status.provider}",
            f"model={status.model}",
            f"base_url={status.base_url}",
        ]
        + status.warnings[:3],
    )


def diagnose_llm() -> LLMDiagnosticResult:
    settings = get_settings()
    status = get_llm_status()
    endpoint = urljoin(settings.openai_base_url.rstrip("/") + "/", "chat/completions")
    warnings = list(status.warnings)

    if not status.can_run_live:
        result = LLMDiagnosticResult(
            status=status,
            connectivity_status="skipped",
            endpoint=endpoint,
            request_model=settings.openai_model,
            warnings=warnings,
            error="" if status.can_run_auto_mode else "真实 LLM 运行条件未满足",
            response_excerpt="",
        )
        return store.add_llm_diagnostic(result)

    started_at = time.perf_counter()
    try:
        content = call_openai_compatible(
            [
                {
                    "role": "system",
                    "content": "你是一个用于连通性验证的写作模型，请保持回答极短。",
                },
                {
                    "role": "user",
                    "content": "请只回复“LLM_OK”，不要输出其他内容。",
                },
            ],
            temperature=0,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        excerpt = content.strip().replace("\n", " ")[:160]
        if "LLM_OK" not in excerpt:
            warnings.append("探测响应可用，但未严格返回预期探针文本。")
        result = LLMDiagnosticResult(
            status=status,
            connectivity_status="ok",
            endpoint=endpoint,
            request_model=settings.openai_model,
            latency_ms=latency_ms,
            response_excerpt=excerpt,
            warnings=warnings,
        )
        return store.add_llm_diagnostic(result)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        result = LLMDiagnosticResult(
            status=status.model_copy(
                update={
                    "readiness": "degraded" if status.can_run_auto_mode else "blocked",
                    "detail": f"连通性探测失败：{exc}",
                }
            ),
            connectivity_status="error",
            endpoint=endpoint,
            request_model=settings.openai_model,
            latency_ms=latency_ms,
            error=str(exc),
            warnings=warnings,
        )
        return store.add_llm_diagnostic(result)


def run_llm_test(payload: LLMTestRunRequest) -> LLMTestRunResult:
    status = get_llm_status()
    prompt = payload.prompt.strip()
    if not prompt:
        raise ValueError("测试 prompt 不能为空")

    requested_mode = payload.writer_mode
    if requested_mode == "auto":
        writer_mode = status.writer_route
    else:
        writer_mode = requested_mode

    if writer_mode == "openai" and not status.can_run_live:
        raise ValueError("当前真实 LLM 未就绪，请先检查 provider 配置或关闭 mock writer")

    if writer_mode == "mock":
        response_text = (
            "Mock Test Run\n\n"
            f"收到测试提示：{prompt[:120]}\n"
            "模拟返回：当前链路可完成前端联调，但未实际请求远端模型。"
        )
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = estimate_tokens(response_text)
        result = LLMTestRunResult(
            status="completed",
            provider=status.provider,
            provider_label=status.provider_label,
            writer_mode="mock",
            model_name="mock-writer",
            prompt_tokens_estimate=prompt_tokens,
            completion_tokens_estimate=completion_tokens,
            total_tokens_estimate=prompt_tokens + completion_tokens,
            response_text=response_text,
            detail="本次为 mock 试运行，不会访问远端 LLM。",
        )
        return store.add_llm_test_run(result)

    started_at = time.perf_counter()
    response_text = call_openai_compatible(
        [
            {
                "role": "system",
                "content": "你是长篇中文网络小说生产系统的 provider 试运行模型，请输出简洁、可读的中文结果。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(response_text)
    result = LLMTestRunResult(
        status="completed",
        provider=status.provider,
        provider_label=status.provider_label,
        writer_mode="openai",
        model_name=get_settings().openai_model,
        latency_ms=latency_ms,
        prompt_tokens_estimate=prompt_tokens,
        completion_tokens_estimate=completion_tokens,
        total_tokens_estimate=prompt_tokens + completion_tokens,
        response_text=response_text,
        detail="试运行已完成，可据此判断真实 OpenAI-compatible 输出链是否可用。",
    )
    return store.add_llm_test_run(result)


def run_project_chapter_preflight(project_id: str, payload: LLMChapterPreflightRequest) -> LLMChapterPreflightResult:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("project not found")

    write_payload = WriteChapterRequest(
        chapter_number=payload.chapter_number,
        tone=payload.tone,
        writer_mode=payload.writer_mode,
    )
    context_pack = build_context_pack(project_id, payload.chapter_number)
    prompt = build_chapter_prompt(project, write_payload, context_pack)
    resolved_mode = resolve_writer_mode(payload.writer_mode)
    if resolved_mode == "openai":
        ensure_writer_mode_available(payload.writer_mode)

    plans = store.list_chapter_plans(project_id)
    started_at = time.perf_counter()
    try:
        run, chapter = create_chapter_draft(project, write_payload, plans, context_pack)
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        result = LLMChapterPreflightResult(
            status="completed",
            project_id=project.id,
            project_title=project.title,
            chapter_number=payload.chapter_number,
            tone=payload.tone,
            provider=get_llm_status().provider,
            provider_label=get_llm_status().provider_label,
            writer_mode_requested=payload.writer_mode,
            writer_mode_resolved=run.writer_mode,
            fallback_used=run.fallback_used,
            model_name=run.model_name,
            chapter_plan_found=context_pack.chapter_plan is not None,
            active_character_count=len(context_pack.active_characters),
            recent_event_count=len(context_pack.recent_events),
            recent_state_count=len(context_pack.recent_character_states),
            memory_hit_count=len(context_pack.long_term_memories),
            relationship_count=len(context_pack.relationship_edges),
            timeline_node_count=len(context_pack.timeline_nodes),
            timeline_constraint_count=len(context_pack.active_timeline_constraints),
            open_hook_count=len(context_pack.open_hooks),
            open_patch_count=len(context_pack.open_retcon_patches),
            prompt_chars=len(prompt),
            prompt_excerpt=prompt[:1200],
            context_summary=context_pack.context_summary,
            prompt_tokens_estimate=run.prompt_tokens_estimate,
            completion_tokens_estimate=run.completion_tokens_estimate,
            total_tokens_estimate=run.total_tokens_estimate,
            latency_ms=latency_ms,
            response_excerpt=chapter.content[:1600],
            detail=run.message,
        )
        return store.add_llm_chapter_preflight(result)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        result = LLMChapterPreflightResult(
            status="failed",
            project_id=project.id,
            project_title=project.title,
            chapter_number=payload.chapter_number,
            tone=payload.tone,
            provider=get_llm_status().provider,
            provider_label=get_llm_status().provider_label,
            writer_mode_requested=payload.writer_mode,
            writer_mode_resolved="openai" if resolved_mode == "openai" else "mock",
            chapter_plan_found=context_pack.chapter_plan is not None,
            active_character_count=len(context_pack.active_characters),
            recent_event_count=len(context_pack.recent_events),
            recent_state_count=len(context_pack.recent_character_states),
            memory_hit_count=len(context_pack.long_term_memories),
            relationship_count=len(context_pack.relationship_edges),
            timeline_node_count=len(context_pack.timeline_nodes),
            timeline_constraint_count=len(context_pack.active_timeline_constraints),
            open_hook_count=len(context_pack.open_hooks),
            open_patch_count=len(context_pack.open_retcon_patches),
            prompt_chars=len(prompt),
            prompt_excerpt=prompt[:1200],
            context_summary=context_pack.context_summary,
            prompt_tokens_estimate=estimate_tokens(prompt),
            latency_ms=latency_ms,
            detail="章节级 preflight 执行失败",
            error=str(exc),
        )
        return store.add_llm_chapter_preflight(result)
