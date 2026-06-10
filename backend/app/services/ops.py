from __future__ import annotations

from app.schemas.domain import RunOpsSummary
from app.services.llm_diagnostics import get_llm_status
from app.services.state_graph_diagnostics import build_state_graph_diagnostics
from app.services.state_graph_repair import attach_state_graph_repair_suggestions, build_state_graph_recovery_plan
from app.services.store import store


CONFIG_ISSUE_KEYWORDS = (
    "openai_api_key",
    "api key",
    "api_key",
    "base url",
    "base_url",
    "model",
    "未配置",
    "缺少",
    "未就绪",
    "运行条件未满足",
)

CONNECTIVITY_ISSUE_KEYWORDS = (
    "timeout",
    "timed out",
    "connection",
    "connect",
    "network",
    "dns",
    "ssl",
    "socket",
    "refused",
    "reset",
    "502",
    "503",
    "504",
    "429",
    "401",
    "403",
    "rate limit",
    "service unavailable",
    "连通性",
    "超时",
    "连接",
    "网络",
    "鉴权",
    "网关",
)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in keywords)


def _issue_text(*parts: str) -> str:
    return " ".join(part for part in parts if part).strip()


def build_run_ops_summary(project_id: str) -> RunOpsSummary:
    chapters = store.list_chapters(project_id)
    metrics = store.list_chapter_metrics(project_id)
    scheduler_tasks = store.list_scheduler_tasks(project_id)
    queue_jobs = store.list_queue_jobs(project_id)
    governance_events = store.list_governance_events(project_id)
    retcon_patches = store.list_retcon_patches(project_id)
    timeline_constraints = store.list_timeline_constraints(project_id)
    llm_diagnostics = store.list_llm_diagnostics()
    llm_preflights = store.list_llm_chapter_preflights(project_id)
    metrics_summary = store.build_metrics_summary(project_id)
    policy = store.get_governance_policy(project_id)
    llm_status = get_llm_status()
    state_graph_diagnostics = attach_state_graph_repair_suggestions(
        project_id,
        build_state_graph_diagnostics(project_id),
    )
    state_graph_recovery_plan = build_state_graph_recovery_plan(state_graph_diagnostics)

    approved_chapters = [item for item in chapters if item.status == "approved" and item.is_current]
    review_required_chapters = [item for item in chapters if item.status == "review_required" and item.is_current]
    current_chapters = [item for item in chapters if item.is_current]
    blocked_tasks = [
        item
        for item in scheduler_tasks
        if item.stage == "governance_blocked" or item.governance_status == "blocked"
    ]
    latest_metrics = metrics[-10:]
    active_stop_reasons = [
        item.governance_reason
        for item in blocked_tasks
        if item.governance_reason
    ][:8]
    recent_critical_events = [
        f"{item.signal} / {item.action} / ch{item.chapter_number or 'n/a'} / {item.summary}"
        for item in governance_events[-8:]
        if item.level == "critical"
    ][:6]
    recent_task_summaries = [
        f"{item.id} / {item.status} / {item.stage} / next={item.next_chapter} / {item.stage_message or '无说明'}"
        for item in scheduler_tasks[-6:]
    ]
    pending_retcon_patches = [item for item in retcon_patches if item.status == "open"]
    replanned_retcon_patches = [item for item in retcon_patches if item.status == "replanned"]
    patch_alerts = [
        f"{item.id} / {item.status} / rerun-from {item.recommended_rerun_from} / ch{item.target_chapter_number}"
        for item in (pending_retcon_patches + replanned_retcon_patches)[-6:]
    ]
    active_timeline_constraints = [
        item
        for item in timeline_constraints
        if item.is_current and item.status in {"warning", "violated"}
    ]
    continuing_timeline_constraints = [
        item for item in active_timeline_constraints if item.previous_constraint_id
    ]
    resolved_timeline_constraints = [
        item for item in timeline_constraints if item.status == "resolved"
    ]
    timeline_risk_alerts = [
        f"{'continuing' if item.previous_constraint_id else 'new'}"
        f" / {item.constraint_type} / ch{item.chapter_number} / {item.status} / {item.description}"
        for item in active_timeline_constraints[-6:]
    ]
    critical_state_graph_diagnostics = [
        item for item in state_graph_diagnostics if item.severity == "critical"
    ]
    state_graph_alerts = [
        f"{item.severity} / {item.category} / ch{item.chapter_number or 'n/a'} / {item.summary}"
        for item in state_graph_diagnostics[:6]
    ]
    recent_fallback_runs = sum(1 for item in metrics[-10:] if item.fallback_used)
    latest_diagnostic = llm_diagnostics[-1] if llm_diagnostics else None
    latest_preflight = llm_preflights[-1] if llm_preflights else None
    llm_recent_preflight_failures = sum(1 for item in llm_preflights[-5:] if item.status == "failed")
    llm_config_issue_count = 0
    llm_connectivity_issue_count = 0
    llm_preflight_issue_count = sum(1 for item in llm_preflights[-8:] if item.status == "failed")
    llm_fallback_issue_count = sum(1 for item in metrics[-10:] if item.fallback_used) + sum(
        1 for item in llm_preflights[-8:] if item.fallback_used
    )
    llm_alerts: list[str] = []
    if _contains_any(_issue_text(llm_status.detail, " ".join(llm_status.warnings)), CONFIG_ISSUE_KEYWORDS):
        llm_config_issue_count += 1
    if llm_status.detail:
        llm_alerts.append(llm_status.detail)
    llm_alerts.extend(llm_status.warnings[:3])
    if latest_diagnostic is not None:
        if latest_diagnostic.error:
            llm_alerts.append(f"最近诊断失败：{latest_diagnostic.error}")
        elif latest_diagnostic.connectivity_status == "ok":
            llm_alerts.append(
                f"最近诊断通过：{latest_diagnostic.request_model} / {latest_diagnostic.latency_ms}ms"
            )
    if latest_preflight is not None:
        if latest_preflight.status == "failed":
            llm_alerts.append(
                f"最近章节 preflight 失败：ch{latest_preflight.chapter_number} / {latest_preflight.error or latest_preflight.detail}"
            )
        elif latest_preflight.fallback_used:
            llm_alerts.append(
                f"最近章节 preflight 发生 fallback：ch{latest_preflight.chapter_number} / {latest_preflight.detail}"
            )
        else:
            llm_alerts.append(
                f"最近章节 preflight 完成：ch{latest_preflight.chapter_number} / {latest_preflight.writer_mode_resolved}"
            )
    for item in llm_diagnostics[-8:]:
        issue_text = _issue_text(
            item.status.detail,
            item.error,
            " ".join(item.status.warnings),
            " ".join(item.warnings),
        )
        if item.connectivity_status in {"skipped", "error"} and _contains_any(
            issue_text, CONFIG_ISSUE_KEYWORDS
        ):
            llm_config_issue_count += 1
        elif item.connectivity_status == "error":
            llm_connectivity_issue_count += 1
    for item in llm_preflights[-8:]:
        issue_text = _issue_text(item.detail, item.error)
        if item.status == "failed" and item.writer_mode_resolved == "openai":
            if _contains_any(issue_text, CONFIG_ISSUE_KEYWORDS):
                llm_config_issue_count += 1
            elif _contains_any(issue_text, CONNECTIVITY_ISSUE_KEYWORDS):
                llm_connectivity_issue_count += 1
    llm_health_events: list[tuple[object, str]] = []
    for item in llm_diagnostics[-5:]:
        if item.connectivity_status == "ok":
            message = f"diagnose ok / {item.request_model or 'n/a'} / {item.latency_ms}ms"
        elif item.connectivity_status == "skipped":
            message = f"diagnose skipped / {item.error or item.status.detail or 'provider not ready'}"
        else:
            message = f"diagnose error / {item.error or item.status.detail or 'unknown'}"
        llm_health_events.append((item.tested_at, message))
    for item in llm_preflights[-5:]:
        if item.status == "failed":
            message = f"preflight failed / ch{item.chapter_number} / {item.error or item.detail or 'unknown'}"
        elif item.fallback_used:
            message = f"preflight fallback / ch{item.chapter_number} / {item.writer_mode_resolved}"
        else:
            message = f"preflight ok / ch{item.chapter_number} / {item.writer_mode_resolved}"
        llm_health_events.append((item.tested_at, message))
    for item in metrics[-5:]:
        if item.fallback_used:
            llm_health_events.append(
                (item.created_at, f"run fallback / ch{item.chapter_number} / {item.model_name or item.source}")
            )
    for item in governance_events[-5:]:
        if item.signal == "llm":
            llm_health_events.append(
                (item.created_at, f"governance {item.action} / ch{item.chapter_number or 'n/a'} / {item.summary}")
            )
    llm_health_trend = [
        summary
        for _, summary in sorted(llm_health_events, key=lambda pair: pair[0], reverse=True)[:8]
    ]
    warnings = list(
        dict.fromkeys(
            metrics_summary.latest_warnings
            + active_stop_reasons
            + llm_alerts
            + timeline_risk_alerts[:4]
            + state_graph_alerts[:4]
            + ([state_graph_recovery_plan.title] if state_graph_recovery_plan is not None else [])
        )
    )[:10]
    queue_pending_jobs = sum(1 for item in queue_jobs if item.status == "pending")
    queue_leased_jobs = sum(1 for item in queue_jobs if item.status == "leased")

    def _avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    return RunOpsSummary(
        project_id=project_id,
        chapter_count=len(current_chapters),
        approved_chapter_count=len(approved_chapters),
        review_required_chapter_count=len(review_required_chapters),
        total_estimated_cost_usd=metrics_summary.total_estimated_cost_usd,
        budget_limit_usd=policy.max_total_estimated_cost_usd,
        budget_used_ratio=round(
            metrics_summary.total_estimated_cost_usd / policy.max_total_estimated_cost_usd,
            4,
        )
        if policy.max_total_estimated_cost_usd > 0
        else 0.0,
        total_scheduler_tasks=len(scheduler_tasks),
        queued_tasks=sum(1 for item in scheduler_tasks if item.status == "queued"),
        running_tasks=sum(1 for item in scheduler_tasks if item.status == "running"),
        paused_tasks=sum(1 for item in scheduler_tasks if item.status == "paused"),
        blocked_tasks=len(blocked_tasks),
        queue_pending_jobs=queue_pending_jobs,
        queue_leased_jobs=queue_leased_jobs,
        last_completed_chapter=max((item.chapter_number for item in current_chapters), default=0),
        average_quality_score_last_10=_avg([item.quality_score for item in latest_metrics]),
        average_reader_score_last_10=_avg([item.reader_score for item in latest_metrics]),
        average_review_score_last_10=_avg([item.review_score for item in latest_metrics]),
        active_timeline_risk_count=len(active_timeline_constraints),
        continuing_timeline_risk_count=len(continuing_timeline_constraints),
        resolved_timeline_risk_count=len(resolved_timeline_constraints),
        timeline_risk_alerts=timeline_risk_alerts,
        state_graph_issue_count=len(state_graph_diagnostics),
        critical_state_graph_issue_count=len(critical_state_graph_diagnostics),
        state_graph_alerts=state_graph_alerts,
        pending_retcon_patch_count=len(pending_retcon_patches),
        replanned_retcon_patch_count=len(replanned_retcon_patches),
        patch_alerts=patch_alerts,
        llm_provider=llm_status.provider,
        llm_provider_label=llm_status.provider_label,
        llm_readiness=llm_status.readiness,
        llm_writer_route=llm_status.writer_route,
        llm_last_diagnostic_status=latest_diagnostic.connectivity_status if latest_diagnostic is not None else "not_run",
        llm_last_diagnostic_at=latest_diagnostic.tested_at if latest_diagnostic is not None else None,
        llm_last_preflight_status=latest_preflight.status if latest_preflight is not None else "not_run",
        llm_last_preflight_at=latest_preflight.tested_at if latest_preflight is not None else None,
        llm_last_preflight_chapter=latest_preflight.chapter_number if latest_preflight is not None else 0,
        llm_recent_preflight_failures=llm_recent_preflight_failures,
        llm_recent_fallback_runs=recent_fallback_runs,
        llm_config_issue_count=llm_config_issue_count,
        llm_connectivity_issue_count=llm_connectivity_issue_count,
        llm_fallback_issue_count=llm_fallback_issue_count,
        llm_preflight_issue_count=llm_preflight_issue_count,
        llm_alerts=list(dict.fromkeys(llm_alerts))[:8],
        llm_health_trend=llm_health_trend,
        active_stop_reasons=active_stop_reasons,
        recent_critical_events=recent_critical_events,
        recent_task_summaries=recent_task_summaries,
        warnings=warnings,
        state_graph_recovery_plan=state_graph_recovery_plan,
    )
