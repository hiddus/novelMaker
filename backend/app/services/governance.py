from __future__ import annotations

from typing import TypeVar

from app.schemas.domain import (
    CharacterState,
    ContinuityIssue,
    ContinuityReport,
    GovernanceDecision,
    GovernanceEvent,
    GovernancePolicy,
    ReaderCouncilReport,
    ReviewReport,
    SchedulerTask,
)
from app.services.store import store

T = TypeVar("T")


def _continuity_issue_weight(issue: ContinuityIssue) -> float:
    if issue.severity == "high":
        return 4.0
    if issue.severity == "medium":
        return 2.0
    return 1.0


def calculate_conflict_score(report: ContinuityReport) -> float:
    base = sum(_continuity_issue_weight(issue) for issue in report.issues)
    if report.overall_risk == "high":
        base += 1.0
    elif report.overall_risk == "medium":
        base += 0.5
    return round(base, 2)


def _latest_item_by_chapter(items: list[T], chapter_number: int) -> T | None:
    for item in reversed(items):
        if getattr(item, "chapter_number", None) == chapter_number:
            return item
    return None


def _find_state_anomalies(states: list[CharacterState], keywords: list[str]) -> list[str]:
    findings: list[str] = []
    for state in states:
        fields = [
            state.location or "",
            state.emotion or "",
            state.goal or "",
            state.relationship_signal or "",
            state.progress_signal or "",
            state.note,
        ]
        merged = " / ".join(part for part in fields if part).strip()
        if not merged:
            continue
        for keyword in keywords:
            if keyword in merged:
                findings.append(f"角色 {state.character_id} 在第 {state.chapter_number} 章触发异常词 `{keyword}`：{merged}")
                break
    return findings


def load_governance_policy(project_id: str) -> GovernancePolicy:
    return store.get_governance_policy(project_id)


def evaluate_governance_before_step(project_id: str, task: SchedulerTask) -> tuple[GovernancePolicy, GovernanceDecision]:
    policy = load_governance_policy(project_id)
    summary = store.build_metrics_summary(project_id)

    if not policy.enabled:
        return policy, GovernanceDecision(action="continue", status="clear", signal="manual", reason="治理策略未启用")

    if summary.total_estimated_cost_usd >= policy.max_total_estimated_cost_usd:
        return policy, GovernanceDecision(
            action="stop",
            status="blocked",
            signal="budget",
            reason="累计成本已超过治理预算上限",
            details=[
                f"当前累计成本 {summary.total_estimated_cost_usd} USD",
                f"预算上限 {policy.max_total_estimated_cost_usd} USD",
            ],
        )

    if task.consecutive_failures >= policy.max_consecutive_failures:
        return policy, GovernanceDecision(
            action="stop",
            status="blocked",
            signal="failure",
            reason="连续失败次数超过治理阈值",
            details=[
                f"连续失败 {task.consecutive_failures} 次",
                f"治理阈值 {policy.max_consecutive_failures} 次",
            ],
        )

    details: list[str] = []
    if policy.max_total_estimated_cost_usd > 0:
        budget_ratio = summary.total_estimated_cost_usd / policy.max_total_estimated_cost_usd
        if budget_ratio >= 0.8:
            details.append(
                f"累计成本已使用 {round(budget_ratio * 100, 1)}%，接近预算上限 {policy.max_total_estimated_cost_usd} USD"
            )
    if details:
        return policy, GovernanceDecision(
            action="continue",
            status="warning",
            signal="budget",
            reason="任务可继续，但预算接近上限",
            details=details,
        )

    return policy, GovernanceDecision(action="continue", status="clear", signal="manual", reason="治理检查通过")


def evaluate_governance_after_chapter(
    project_id: str,
    task: SchedulerTask,
    chapter_number: int,
) -> tuple[GovernancePolicy, GovernanceDecision]:
    policy = load_governance_policy(project_id)
    summary = store.build_metrics_summary(project_id)

    if not policy.enabled:
        return policy, GovernanceDecision(
            action="continue",
            status="clear",
            signal="manual",
            reason="治理策略未启用",
            chapter_number=chapter_number,
        )

    metrics = store.list_chapter_metrics(project_id)
    reviews = store.list_reviews(project_id)
    continuity_reports = store.list_continuity_reports(project_id)
    reader_reports = store.list_reader_council_reports(project_id)
    states = store.list_character_states(project_id)

    metric = _latest_item_by_chapter(metrics, chapter_number)
    review = _latest_item_by_chapter(reviews, chapter_number)
    continuity = _latest_item_by_chapter(continuity_reports, chapter_number)
    reader = _latest_item_by_chapter(reader_reports, chapter_number)
    chapter_states = [item for item in states if item.chapter_number == chapter_number]

    if metric and metric.estimated_cost_usd >= policy.max_chapter_cost_usd:
        return policy, GovernanceDecision(
            action="stop",
            status="blocked",
            signal="budget",
            reason=f"第 {chapter_number} 章成本超过单章预算阈值",
            details=[
                f"单章成本 {metric.estimated_cost_usd} USD",
                f"阈值 {policy.max_chapter_cost_usd} USD",
            ],
            chapter_number=chapter_number,
        )

    if summary.total_estimated_cost_usd >= policy.max_total_estimated_cost_usd:
        return policy, GovernanceDecision(
            action="stop",
            status="blocked",
            signal="budget",
            reason="累计成本达到治理预算上限",
            details=[
                f"当前累计成本 {summary.total_estimated_cost_usd} USD",
                f"预算上限 {policy.max_total_estimated_cost_usd} USD",
            ],
            chapter_number=chapter_number,
        )

    if continuity is not None:
        conflict_score = calculate_conflict_score(continuity)
        if conflict_score >= policy.max_conflict_score:
            return policy, GovernanceDecision(
                action="stop",
                status="blocked",
                signal="continuity",
                reason=f"第 {chapter_number} 章冲突分超过阈值",
                details=[
                    f"冲突分 {conflict_score}",
                    f"阈值 {policy.max_conflict_score}",
                    continuity.summary or "Continuity Board 触发高风险",
                ],
                chapter_number=chapter_number,
            )

    if review is not None:
        if policy.pause_on_review_required and review.status == "review_required":
            return policy, GovernanceDecision(
                action="pause",
                status="blocked",
                signal="review",
                reason=f"第 {chapter_number} 章进入人工审核，任务自动暂停",
                details=review.findings[:5],
                chapter_number=chapter_number,
            )
        if review.overall_score < policy.min_review_score:
            return policy, GovernanceDecision(
                action="pause",
                status="warning",
                signal="review",
                reason=f"第 {chapter_number} 章评审分低于治理阈值",
                details=[
                    f"评审分 {review.overall_score}",
                    f"阈值 {policy.min_review_score}",
                ]
                + review.findings[:3],
                chapter_number=chapter_number,
            )

    if reader is not None and reader.overall_score < policy.min_reader_score:
        action = "pause" if policy.pause_on_reader_weak else "continue"
        status = "warning" if action == "pause" else "clear"
        return policy, GovernanceDecision(
            action=action,
            status=status,
            signal="reader",
            reason=f"第 {chapter_number} 章读者分低于治理阈值",
            details=[
                f"读者分 {reader.overall_score}",
                f"阈值 {policy.min_reader_score}",
                reader.summary or "Reader Council 判定追读驱动力偏弱",
            ]
            + reader.concerns[:3],
            chapter_number=chapter_number,
        )

    anomalies = _find_state_anomalies(chapter_states, policy.state_anomaly_keywords)
    if anomalies and policy.pause_on_state_anomaly:
        return policy, GovernanceDecision(
            action="pause",
            status="blocked",
            signal="state",
            reason=f"第 {chapter_number} 章命中关键状态异常",
            details=anomalies[:5],
            chapter_number=chapter_number,
        )

    details: list[str] = []
    if continuity is not None:
        details.append(f"冲突分 {calculate_conflict_score(continuity)} / 阈值 {policy.max_conflict_score}")
    if metric is not None:
        details.append(
            f"累计成本 {summary.total_estimated_cost_usd} USD / 预算 {policy.max_total_estimated_cost_usd} USD"
        )
    return policy, GovernanceDecision(
        action="continue",
        status="clear",
        signal="manual",
        reason=f"第 {chapter_number} 章通过治理检查",
        details=details,
        chapter_number=chapter_number,
    )


def emit_governance_event(
    project_id: str,
    task: SchedulerTask,
    policy: GovernancePolicy,
    decision: GovernanceDecision,
) -> GovernanceEvent:
    level = "info"
    if decision.status == "warning":
        level = "warning"
    if decision.action == "stop" or decision.status == "blocked":
        level = "critical"
    event = GovernanceEvent(
        project_id=project_id,
        task_id=task.id,
        policy_id=policy.id,
        chapter_number=decision.chapter_number,
        level=level,  # type: ignore[arg-type]
        signal=decision.signal,
        action=decision.action,
        summary=decision.reason or "治理事件",
        details=decision.details,
    )
    return store.add_governance_event(project_id, event)
