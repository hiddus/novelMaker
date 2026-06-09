from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.domain import ChapterDraft, ContextPack, ExtractedUpdate, HookRecord, HookStateChange


RESOLVE_HINTS = ["真相", "揭晓", "终于", "找到", "得到", "收回", "兑现", "开启"]
ABANDON_HINTS = ["作罢", "放弃", "销毁", "遗失", "舍弃", "不再追查"]


def _normalized(text: str) -> str:
    return text.strip().replace(" ", "")


def _expected_resolution_arc(context_pack: ContextPack) -> str:
    if context_pack.chapter_plan is None:
        return ""
    return context_pack.chapter_plan.goal or context_pack.chapter_plan.conflict or ""


def build_hook_updates(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> tuple[ExtractedUpdate, list[HookRecord], list[HookStateChange]]:
    content = chapter.content
    summary = chapter.summary
    plan_hook = context_pack.chapter_plan.hook if context_pack.chapter_plan and context_pack.chapter_plan.hook else ""
    open_hooks = context_pack.open_hooks
    now = datetime.now(UTC)

    new_hooks: list[str] = []
    active_hooks: list[str] = []
    resolved_hooks: list[str] = []
    abandoned_hooks: list[str] = []
    updated_records: list[HookRecord] = []
    changes: list[HookStateChange] = []

    matched_by_content = {_normalized(item.content): item for item in open_hooks}

    if plan_hook:
        normalized_plan_hook = _normalized(plan_hook)
        if normalized_plan_hook not in matched_by_content:
            record = HookRecord(
                project_id=project_id,
                content=plan_hook,
                created_in_chapter=chapter.chapter_number,
                source_chapter_id=chapter.id,
                source_plan_id=context_pack.chapter_plan.id if context_pack.chapter_plan else None,
                expected_resolution_arc=_expected_resolution_arc(context_pack),
                status="open",
                last_touched_chapter=chapter.chapter_number,
                note=f"在《{chapter.title}》中创建的新伏笔。",
                updated_at=now,
            )
            updated_records.append(record)
            changes.append(
                HookStateChange(
                    project_id=project_id,
                    hook_id=record.id,
                    chapter_number=chapter.chapter_number,
                    chapter_id=chapter.id,
                    action="create",
                    content=record.content,
                    expected_resolution_arc=record.expected_resolution_arc,
                    note=record.note,
                )
            )
            new_hooks.append(record.content)

    for item in open_hooks:
        normalized_content = _normalized(item.content)
        if not normalized_content:
            continue
        hit_in_text = item.content in content or item.content in summary
        resolve_hit = hit_in_text and any(hint in content for hint in RESOLVE_HINTS)
        abandon_hit = hit_in_text and any(hint in content for hint in ABANDON_HINTS)

        if resolve_hit:
            updated = item.model_copy(
                update={
                    "status": "resolved",
                    "last_touched_chapter": chapter.chapter_number,
                    "resolution_chapter": chapter.chapter_number,
                    "updated_at": now,
                }
            )
            updated_records.append(updated)
            changes.append(
                HookStateChange(
                    project_id=project_id,
                    hook_id=item.id,
                    chapter_number=chapter.chapter_number,
                    chapter_id=chapter.id,
                    action="resolve",
                    content=item.content,
                    expected_resolution_arc=item.expected_resolution_arc,
                    note=f"在《{chapter.title}》中回收伏笔。",
                )
            )
            resolved_hooks.append(item.content)
            continue

        if abandon_hit:
            updated = item.model_copy(
                update={
                    "status": "abandoned",
                    "last_touched_chapter": chapter.chapter_number,
                    "resolution_chapter": chapter.chapter_number,
                    "updated_at": now,
                }
            )
            updated_records.append(updated)
            changes.append(
                HookStateChange(
                    project_id=project_id,
                    hook_id=item.id,
                    chapter_number=chapter.chapter_number,
                    chapter_id=chapter.id,
                    action="abandon",
                    content=item.content,
                    expected_resolution_arc=item.expected_resolution_arc,
                    note=f"在《{chapter.title}》中放弃该伏笔。",
                )
            )
            abandoned_hooks.append(item.content)
            continue

        if hit_in_text:
            updated = item.model_copy(
                update={
                    "status": "active",
                    "last_touched_chapter": chapter.chapter_number,
                    "updated_at": now,
                }
            )
            updated_records.append(updated)
            changes.append(
                HookStateChange(
                    project_id=project_id,
                    hook_id=item.id,
                    chapter_number=chapter.chapter_number,
                    chapter_id=chapter.id,
                    action="activate",
                    content=item.content,
                    expected_resolution_arc=item.expected_resolution_arc,
                    note=f"在《{chapter.title}》中再次激活伏笔。",
                )
            )
            active_hooks.append(item.content)

    extracted_update = extracted_update.model_copy(
        update={
            "hook_changes": list(dict.fromkeys(new_hooks + active_hooks + resolved_hooks + abandoned_hooks)),
            "new_hooks": list(dict.fromkeys(new_hooks)),
            "active_hooks": list(dict.fromkeys(active_hooks)),
            "resolved_hooks": list(dict.fromkeys(resolved_hooks)),
            "abandoned_hooks": list(dict.fromkeys(abandoned_hooks)),
            "summary": (
                extracted_update.summary
                + f" Hook 变化：新增 {len(new_hooks)} / 激活 {len(active_hooks)} / 回收 {len(resolved_hooks)} / 废弃 {len(abandoned_hooks)}。"
            ),
        }
    )
    return extracted_update, updated_records, changes


def materialize_hook_updates(
    project_id: str,
    chapter: ChapterDraft,
    context_pack: ContextPack,
    extracted_update: ExtractedUpdate,
) -> tuple[list[HookRecord], list[HookStateChange]]:
    now = datetime.now(UTC)
    records: list[HookRecord] = []
    changes: list[HookStateChange] = []
    open_hook_map = {item.content: item for item in context_pack.open_hooks}

    for content in extracted_update.new_hooks:
        record = HookRecord(
            project_id=project_id,
            content=content,
            created_in_chapter=chapter.chapter_number,
            source_chapter_id=chapter.id,
            source_plan_id=context_pack.chapter_plan.id if context_pack.chapter_plan else None,
            expected_resolution_arc=_expected_resolution_arc(context_pack),
            status="open",
            last_touched_chapter=chapter.chapter_number,
            note=f"在《{chapter.title}》中创建的新伏笔。",
            updated_at=now,
        )
        records.append(record)
        changes.append(
            HookStateChange(
                project_id=project_id,
                hook_id=record.id,
                chapter_number=chapter.chapter_number,
                chapter_id=chapter.id,
                action="create",
                content=record.content,
                expected_resolution_arc=record.expected_resolution_arc,
                note=record.note,
            )
        )

    for action, contents in [
        ("activate", extracted_update.active_hooks),
        ("resolve", extracted_update.resolved_hooks),
        ("abandon", extracted_update.abandoned_hooks),
    ]:
        for content in contents:
            existing = open_hook_map.get(content)
            if existing is None:
                continue
            if action == "activate":
                updated = existing.model_copy(
                    update={
                        "status": "active",
                        "last_touched_chapter": chapter.chapter_number,
                        "updated_at": now,
                    }
                )
            elif action == "resolve":
                updated = existing.model_copy(
                    update={
                        "status": "resolved",
                        "last_touched_chapter": chapter.chapter_number,
                        "resolution_chapter": chapter.chapter_number,
                        "updated_at": now,
                    }
                )
            else:
                updated = existing.model_copy(
                    update={
                        "status": "abandoned",
                        "last_touched_chapter": chapter.chapter_number,
                        "resolution_chapter": chapter.chapter_number,
                        "updated_at": now,
                    }
                )
            records.append(updated)
            changes.append(
                HookStateChange(
                    project_id=project_id,
                    hook_id=existing.id,
                    chapter_number=chapter.chapter_number,
                    chapter_id=chapter.id,
                    action=action,  # type: ignore[arg-type]
                    content=existing.content,
                    expected_resolution_arc=existing.expected_resolution_arc,
                    note=f"在《{chapter.title}》中执行 Hook 状态变更：{action}。",
                )
            )

    return records, changes
