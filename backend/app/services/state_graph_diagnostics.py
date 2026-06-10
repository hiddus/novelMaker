from __future__ import annotations

from collections import defaultdict

from app.schemas.domain import StateGraphDiagnostic
from app.services.store import store


def _issue(
    *,
    category: str,
    severity: str,
    summary: str,
    detail: str = "",
    chapter_number: int | None = None,
    entity_type: str = "",
    entity_id: str = "",
) -> StateGraphDiagnostic:
    return StateGraphDiagnostic(
        category=category,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        chapter_number=chapter_number,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        detail=detail,
    )


def _missing_ids(ids: list[str], existing_ids: set[str]) -> list[str]:
    return [item for item in ids if item not in existing_ids]


def build_state_graph_diagnostics(project_id: str) -> list[StateGraphDiagnostic]:
    chapters = store.list_chapters(project_id)
    current_chapters = [item for item in chapters if item.is_current]
    reviews = store.list_current_reviews(project_id)
    continuity_reports = store.list_current_continuity_reports(project_id)
    reader_reports = store.list_current_reader_council_reports(project_id)
    relationship_edges = store.list_relationship_edges(project_id)
    timeline_nodes = store.list_timeline_nodes(project_id)
    timeline_constraints = store.list_timeline_constraints(project_id)
    events = store.list_events(project_id)
    states = store.list_character_states(project_id)
    extracted_updates = store.list_extracted_updates(project_id)
    snapshots = store.list_snapshots(project_id)
    versions = store.list_versions(project_id)
    hook_records = store.list_hook_records(project_id)

    diagnostics: list[StateGraphDiagnostic] = []

    review_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    continuity_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    reader_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    snapshot_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    version_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    node_by_chapter_id: dict[str, list[object]] = defaultdict(list)
    for item in reviews:
        review_by_chapter_id[item.chapter_id].append(item)
    for item in continuity_reports:
        continuity_by_chapter_id[item.chapter_id].append(item)
    for item in reader_reports:
        reader_by_chapter_id[item.chapter_id].append(item)
    for item in snapshots:
        snapshot_by_chapter_id[item.chapter_id].append(item)
    for item in versions:
        version_by_chapter_id[item.chapter_id].append(item)
    for item in timeline_nodes:
        if item.chapter_id:
            node_by_chapter_id[item.chapter_id].append(item)

    event_ids = {item.id for item in events}
    events_by_id = {item.id: item for item in events}
    state_ids = {item.id for item in states}
    edge_ids = {item.id for item in relationship_edges}
    edges_by_id = {item.id: item for item in relationship_edges}
    node_ids = {item.id for item in timeline_nodes}
    nodes_by_id = {item.id: item for item in timeline_nodes}
    constraint_ids = {item.id for item in timeline_constraints}
    constraints_by_id = {item.id: item for item in timeline_constraints}
    snapshot_ids = {item.id for item in snapshots}
    extracted_update_ids = {item.id for item in extracted_updates}
    hook_ids = {item.id for item in hook_records}

    for chapter in current_chapters:
        chapter_number = chapter.chapter_number
        current_reviews = review_by_chapter_id.get(chapter.id, [])
        current_continuity = continuity_by_chapter_id.get(chapter.id, [])
        current_readers = reader_by_chapter_id.get(chapter.id, [])
        current_snapshots = snapshot_by_chapter_id.get(chapter.id, [])
        current_versions = version_by_chapter_id.get(chapter.id, [])
        current_nodes = node_by_chapter_id.get(chapter.id, [])

        if not current_reviews:
            diagnostics.append(
                _issue(
                    category="revision",
                    severity="critical",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节缺少 review",
                    detail="每个 current revision 都应绑定 review 结果，否则治理与人工审核链会断开。",
                )
            )
        elif len(current_reviews) > 1:
            diagnostics.append(
                _issue(
                    category="revision",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节存在多条 current review",
                    detail=f"检测到 {len(current_reviews)} 条 current review，可能存在重复审批分支。",
                )
            )

        if not current_continuity:
            diagnostics.append(
                _issue(
                    category="projection",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节缺少 continuity report",
                    detail="一致性审查结果缺失，后续治理与工作台判断会降级。",
                )
            )
        elif len(current_continuity) > 1:
            diagnostics.append(
                _issue(
                    category="projection",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节存在多条 current continuity report",
                    detail=f"检测到 {len(current_continuity)} 条 current continuity report。",
                )
            )

        if not current_readers:
            diagnostics.append(
                _issue(
                    category="projection",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节缺少 reader report",
                    detail="读者反馈链缺失，追读驱动力治理只能依赖旧数据。",
                )
            )
        elif len(current_readers) > 1:
            diagnostics.append(
                _issue(
                    category="projection",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="当前章节存在多条 current reader report",
                    detail=f"检测到 {len(current_readers)} 条 current reader report。",
                )
            )

        if chapter.status == "approved":
            if not current_snapshots:
                diagnostics.append(
                    _issue(
                        category="projection",
                        severity="critical",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节缺少 snapshot",
                        detail="approved 章节应已写回快照，否则上下文和记忆视图会断链。",
                    )
                )
            elif len(current_snapshots) > 1:
                diagnostics.append(
                    _issue(
                        category="projection",
                        severity="warning",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节存在多份 snapshot",
                        detail=f"检测到 {len(current_snapshots)} 份 snapshot，可能发生重复写回。",
                    )
                )

            if not current_versions:
                diagnostics.append(
                    _issue(
                        category="projection",
                        severity="critical",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节缺少 version",
                        detail="approved 章节应生成 version 记录，否则 canon 审计链不完整。",
                    )
                )
            elif len(current_versions) > 1:
                diagnostics.append(
                    _issue(
                        category="projection",
                        severity="warning",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节存在多份 version",
                        detail=f"检测到 {len(current_versions)} 份 version，可能发生重复 approve 或重复写回。",
                    )
                )

            if not current_nodes:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="critical",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节缺少 timeline node",
                        detail="approved 章节应写回时间线节点，否则 timeline constraint 和 context 会断链。",
                    )
                )
            elif len(current_nodes) > 1:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="warning",
                        chapter_number=chapter_number,
                        entity_type="chapter",
                        entity_id=chapter.id,
                        summary="已批准章节存在多个 timeline node",
                        detail=f"检测到 {len(current_nodes)} 个时间线节点，可能发生重复写回。",
                    )
                )
        elif current_versions:
            diagnostics.append(
                _issue(
                    category="revision",
                    severity="warning",
                    chapter_number=chapter_number,
                    entity_type="chapter",
                    entity_id=chapter.id,
                    summary="未批准 current 章节存在 version",
                    detail="当前章节仍未 approved，但已经存在 version 记录，可能有旧投影残留。",
                )
            )

    for item in extracted_updates:
        missing_events = _missing_ids(item.event_ids, event_ids)
        missing_states = _missing_ids(item.character_state_ids, state_ids)
        missing_edges = _missing_ids(item.relationship_edge_ids, edge_ids)
        missing_nodes = _missing_ids(item.timeline_node_ids, node_ids)
        if missing_events or missing_states or missing_edges or missing_nodes:
            diagnostics.append(
                _issue(
                    category="reference",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="extracted_update",
                    entity_id=item.id,
                    summary="ExtractedUpdate 存在悬空引用",
                    detail=(
                        f"events={','.join(missing_events) or 'ok'} / "
                        f"states={','.join(missing_states) or 'ok'} / "
                        f"edges={','.join(missing_edges) or 'ok'} / "
                        f"timeline_nodes={','.join(missing_nodes) or 'ok'}"
                    ),
                )
            )

    for item in snapshots:
        missing_events = _missing_ids(item.recent_event_ids, event_ids)
        missing_edges = _missing_ids(item.relationship_edge_ids, edge_ids)
        missing_nodes = _missing_ids(item.timeline_node_ids, node_ids)
        missing_hooks = _missing_ids(item.active_hook_ids, hook_ids)
        if missing_events or missing_edges or missing_nodes or missing_hooks:
            diagnostics.append(
                _issue(
                    category="reference",
                    severity="critical" if missing_events or missing_edges or missing_nodes else "warning",
                    chapter_number=item.chapter_number,
                    entity_type="snapshot",
                    entity_id=item.id,
                    summary="Snapshot 存在悬空引用",
                    detail=(
                        f"events={','.join(missing_events) or 'ok'} / "
                        f"edges={','.join(missing_edges) or 'ok'} / "
                        f"timeline_nodes={','.join(missing_nodes) or 'ok'} / "
                        f"hooks={','.join(missing_hooks) or 'ok'}"
                    ),
                )
            )

    for item in versions:
        missing_snapshot = item.snapshot_id not in snapshot_ids
        missing_extract = item.extracted_update_id not in extracted_update_ids
        if missing_snapshot or missing_extract:
            diagnostics.append(
                _issue(
                    category="reference",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="version",
                    entity_id=item.id,
                    summary="VersionRecord 存在悬空引用",
                    detail=(
                        f"snapshot={'missing' if missing_snapshot else 'ok'} / "
                        f"extracted_update={'missing' if missing_extract else 'ok'}"
                    ),
                )
            )

    relationship_edges_by_pair: dict[str, list[object]] = defaultdict(list)
    current_edges_by_pair: dict[str, list[object]] = defaultdict(list)
    for item in relationship_edges:
        pair_key = item.pair_key or "::".join(sorted([item.source_character_id, item.target_character_id]))
        relationship_edges_by_pair[pair_key].append(item)
        if item.previous_edge_id and item.previous_edge_id not in edge_ids:
            diagnostics.append(
                _issue(
                    category="relationship",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="relationship_edge",
                    entity_id=item.id,
                    summary="关系边 previous_edge_id 断链",
                    detail=f"缺失前序边 {item.previous_edge_id}",
                )
            )
        elif item.previous_edge_id:
            previous = edges_by_id[item.previous_edge_id]
            previous_pair_key = previous.pair_key or "::".join(
                sorted([previous.source_character_id, previous.target_character_id])
            )
            if previous_pair_key != pair_key:
                diagnostics.append(
                    _issue(
                        category="relationship",
                        severity="critical",
                        chapter_number=item.chapter_number,
                        entity_type="relationship_edge",
                        entity_id=item.id,
                        summary="关系边 previous_edge_id 指向不同角色对",
                        detail=f"当前={pair_key} / previous={previous_pair_key}",
                    )
                )
            if previous.chapter_number >= item.chapter_number:
                diagnostics.append(
                    _issue(
                        category="relationship",
                        severity="critical",
                        chapter_number=item.chapter_number,
                        entity_type="relationship_edge",
                        entity_id=item.id,
                        summary="关系边演化链章节顺序倒挂",
                        detail=f"previous ch{previous.chapter_number} 不应晚于或等于当前 ch{item.chapter_number}",
                    )
                )
        if item.is_current:
            current_edges_by_pair[pair_key].append(item)

    for pair_key, items in relationship_edges_by_pair.items():
        if items and not current_edges_by_pair.get(pair_key):
            diagnostics.append(
                _issue(
                    category="relationship",
                    severity="critical",
                    chapter_number=max(item.chapter_number for item in items),
                    entity_type="relationship_pair",
                    entity_id=pair_key,
                    summary="关系链存在历史边但缺少 current relationship edge",
                    detail=f"{pair_key} 共 {len(items)} 条关系边，但当前没有任何 current head。",
                )
            )

    for pair_key, items in current_edges_by_pair.items():
        if len(items) > 1:
            diagnostics.append(
                _issue(
                    category="relationship",
                    severity="critical",
                    chapter_number=max(item.chapter_number for item in items),
                    entity_type="relationship_pair",
                    entity_id=pair_key,
                    summary="同一角色对存在多条 current relationship edge",
                    detail=f"{pair_key} 同时存在 {len(items)} 条 current 边。",
                )
            )

    for item in timeline_nodes:
        missing_predecessors = _missing_ids(item.predecessor_node_ids, node_ids)
        if item.event_id and item.event_id not in event_ids:
            diagnostics.append(
                _issue(
                    category="timeline",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="timeline_node",
                    entity_id=item.id,
                    summary="时间线节点 event_id 断链",
                    detail=f"event_id={item.event_id} 未命中 event。",
                )
            )
        elif item.event_id:
            event = events_by_id[item.event_id]
            if event.chapter_number != item.chapter_number:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="warning",
                        chapter_number=item.chapter_number,
                        entity_type="timeline_node",
                        entity_id=item.id,
                        summary="时间线节点 event 章节号不一致",
                        detail=f"timeline node ch{item.chapter_number} 指向 event ch{event.chapter_number}",
                    )
                )
        if missing_predecessors:
            diagnostics.append(
                _issue(
                    category="timeline",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="timeline_node",
                    entity_id=item.id,
                    summary="时间线节点 predecessor_node_ids 断链",
                    detail=f"缺失前序节点 {','.join(missing_predecessors)}",
                )
            )
        for predecessor_id in item.predecessor_node_ids:
            predecessor = nodes_by_id.get(predecessor_id)
            if predecessor is None:
                continue
            if predecessor.chapter_number >= item.chapter_number:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="critical",
                        chapter_number=item.chapter_number,
                        entity_type="timeline_node",
                        entity_id=item.id,
                        summary="时间线节点 predecessor 指向同章或未来章节",
                        detail=f"previous ch{predecessor.chapter_number} 不应晚于或等于当前 ch{item.chapter_number}",
                    )
                )
                break

    current_constraints_by_evolution: dict[str, list[object]] = defaultdict(list)
    for item in timeline_constraints:
        evolution_key = item.evolution_key or f"{item.constraint_type}:{item.description}"
        if item.previous_constraint_id and item.previous_constraint_id not in constraint_ids:
            diagnostics.append(
                _issue(
                    category="timeline",
                    severity="critical",
                    chapter_number=item.chapter_number,
                    entity_type="timeline_constraint",
                    entity_id=item.id,
                    summary="时间线约束 previous_constraint_id 断链",
                    detail=f"缺失前序约束 {item.previous_constraint_id}",
                )
            )
        elif item.previous_constraint_id:
            previous = constraints_by_id[item.previous_constraint_id]
            previous_evolution_key = previous.evolution_key or f"{previous.constraint_type}:{previous.description}"
            if previous_evolution_key != evolution_key:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="critical",
                        chapter_number=item.chapter_number,
                        entity_type="timeline_constraint",
                        entity_id=item.id,
                        summary="时间线约束 previous_constraint_id 指向不同演化链",
                        detail=f"当前={evolution_key} / previous={previous_evolution_key}",
                    )
                )
            if previous.chapter_number >= item.chapter_number:
                diagnostics.append(
                    _issue(
                        category="timeline",
                        severity="critical",
                        chapter_number=item.chapter_number,
                        entity_type="timeline_constraint",
                        entity_id=item.id,
                        summary="时间线约束演化链章节顺序倒挂",
                        detail=f"previous ch{previous.chapter_number} 不应晚于或等于当前 ch{item.chapter_number}",
                    )
                )
        if item.related_node_id and item.related_node_id not in node_ids:
            diagnostics.append(
                _issue(
                    category="timeline",
                    severity="warning",
                    chapter_number=item.chapter_number,
                    entity_type="timeline_constraint",
                    entity_id=item.id,
                    summary="时间线约束关联节点不存在",
                    detail=f"related_node_id={item.related_node_id} 未命中 timeline node。",
                )
            )
        if item.is_current:
            current_constraints_by_evolution[evolution_key].append(item)

    for evolution_key, items in current_constraints_by_evolution.items():
        if len(items) > 1:
            diagnostics.append(
                _issue(
                    category="timeline",
                    severity="critical",
                    chapter_number=max(item.chapter_number for item in items),
                    entity_type="timeline_chain",
                    entity_id=evolution_key,
                    summary="同一时间线演化链存在多条 current constraint",
                    detail=f"evolution_key={evolution_key} 同时存在 {len(items)} 条 current constraint。",
                )
            )

    severity_rank = {"critical": 0, "warning": 1}
    diagnostics.sort(
        key=lambda item: (
            severity_rank.get(item.severity, 9),
            -(item.chapter_number or 0),
            item.category,
            item.entity_type,
            item.entity_id,
            item.summary,
        )
    )
    return diagnostics
