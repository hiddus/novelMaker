from __future__ import annotations

import re
from collections.abc import Iterable

from app.core.config import get_settings
from app.schemas.domain import (
    LongTermMemoryRecord,
    MemoryRetrievalHit,
    MemoryRetrievalTrace,
)
from app.services.store import store

_SEPARATORS = re.compile(r"[\s，。；：、,:;()\[\]（）【】\-_/]+")


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _split_terms(text: str) -> list[str]:
    tokens = [item.strip() for item in _SEPARATORS.split(text) if len(item.strip()) >= 2]
    return list(dict.fromkeys(tokens))


def _char_ngrams(text: str, size: int = 2) -> list[str]:
    compact = "".join(ch for ch in text if not ch.isspace())
    if len(compact) < size:
        return []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]


def extract_memory_terms(*parts: str) -> list[str]:
    items: list[str] = []
    for part in parts:
        normalized = _normalize(part)
        if not normalized:
            continue
        items.extend(_split_terms(normalized))
        items.extend(_char_ngrams(normalized, size=2))
    return list(dict.fromkeys(item for item in items if len(item) >= 2))


def _memory_record(
    project_id: str,
    *,
    source_type: str,
    source_id: str,
    chapter_number: int,
    memory_type: str,
    title: str,
    content: str,
    keywords: Iterable[str],
    importance_score: float,
) -> LongTermMemoryRecord:
    return LongTermMemoryRecord(
        project_id=project_id,
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        chapter_number=chapter_number,
        memory_type=memory_type,  # type: ignore[arg-type]
        title=title,
        content=_normalize(content),
        keywords=list(dict.fromkeys(item for item in keywords if item)),
        importance_score=round(importance_score, 2),
    )


def rebuild_long_term_memory(project_id: str) -> list[LongTermMemoryRecord]:
    chapters = [item for item in store.list_chapters(project_id) if item.is_current]
    events = store.list_events(project_id)
    states = store.list_character_states(project_id)
    snapshots = store.list_snapshots(project_id)
    hooks = store.list_hook_records(project_id)
    patches = store.list_retcon_patches(project_id)
    reviews = store.list_reviews(project_id)
    continuity_reports = store.list_continuity_reports(project_id)
    reader_reports = store.list_reader_council_reports(project_id)

    records: list[LongTermMemoryRecord] = []

    for chapter in chapters:
        content = f"{chapter.title} {chapter.summary} {chapter.content[:400]}"
        records.append(
            _memory_record(
                project_id,
                source_type="chapter",
                source_id=chapter.id,
                chapter_number=chapter.chapter_number,
                memory_type="summary",
                title=chapter.title,
                content=content,
                keywords=extract_memory_terms(chapter.title, chapter.summary, chapter.content[:200]),
                importance_score=3.2 if chapter.status == "approved" else 2.4,
            )
        )

    for event in events:
        records.append(
            _memory_record(
                project_id,
                source_type="event",
                source_id=event.id,
                chapter_number=event.chapter_number,
                memory_type="fact",
                title=f"第{event.chapter_number}章事件",
                content=event.summary,
                keywords=extract_memory_terms(event.summary, event.event_type, event.location or ""),
                importance_score=2.8,
            )
        )

    for state in states:
        text = "；".join(
            item
            for item in [
                f"角色={state.character_id}",
                f"地点={state.location}" if state.location else "",
                f"情绪={state.emotion}" if state.emotion else "",
                f"目标={state.goal}" if state.goal else "",
                f"关系={state.relationship_signal}" if state.relationship_signal else "",
                f"推进={state.progress_signal}" if state.progress_signal else "",
                state.note,
            ]
            if item
        )
        records.append(
            _memory_record(
                project_id,
                source_type="character_state",
                source_id=state.id,
                chapter_number=state.chapter_number,
                memory_type="state",
                title=f"第{state.chapter_number}章角色状态",
                content=text,
                keywords=extract_memory_terms(text),
                importance_score=2.6,
            )
        )

    for snapshot in snapshots:
        records.append(
            _memory_record(
                project_id,
                source_type="snapshot",
                source_id=snapshot.id,
                chapter_number=snapshot.chapter_number,
                memory_type="summary",
                title=snapshot.chapter_title,
                content=snapshot.summary,
                keywords=extract_memory_terms(snapshot.chapter_title, snapshot.summary),
                importance_score=2.3,
            )
        )

    for hook in hooks:
        content = f"状态={hook.status}；内容={hook.content}；预期回收={hook.expected_resolution_arc}；备注={hook.note}"
        records.append(
            _memory_record(
                project_id,
                source_type="hook",
                source_id=hook.id,
                chapter_number=hook.last_touched_chapter or hook.created_in_chapter,
                memory_type="foreshadow",
                title=f"伏笔 {hook.status}",
                content=content,
                keywords=extract_memory_terms(hook.content, hook.expected_resolution_arc, hook.note),
                importance_score=3.0 if hook.status in {"open", "active"} else 2.2,
            )
        )

    for patch in patches:
        content = "；".join(
            [
                patch.reason,
                f"目标章节={patch.target_chapter_number}",
                f"建议重跑={patch.recommended_rerun_from}",
                f"影响章节={','.join(str(item) for item in patch.affected_chapter_numbers[:8])}",
            ]
        )
        records.append(
            _memory_record(
                project_id,
                source_type="patch",
                source_id=patch.id,
                chapter_number=patch.target_chapter_number,
                memory_type="risk",
                title=f"补丁 {patch.id}",
                content=content,
                keywords=extract_memory_terms(content, " ".join(patch.impact_summary[:3])),
                importance_score=3.1,
            )
        )

    for review in reviews:
        content = "；".join([review.decision_reason] + review.findings[:4])
        records.append(
            _memory_record(
                project_id,
                source_type="review",
                source_id=review.id,
                chapter_number=review.chapter_number,
                memory_type="risk",
                title=f"第{review.chapter_number}章评审",
                content=content,
                keywords=extract_memory_terms(content),
                importance_score=3.0 if review.status == "review_required" else 2.1,
            )
        )

    for report in continuity_reports:
        content = "；".join([report.summary] + [issue.title for issue in report.issues[:4]])
        records.append(
            _memory_record(
                project_id,
                source_type="continuity",
                source_id=report.id,
                chapter_number=report.chapter_number,
                memory_type="risk",
                title=f"第{report.chapter_number}章连续性",
                content=content,
                keywords=extract_memory_terms(content, " ".join(report.judges_triggered)),
                importance_score=3.2 if report.status == "review_required" else 2.0,
            )
        )

    for report in reader_reports:
        content = "；".join([report.summary] + report.concerns[:3] + report.highlights[:2])
        records.append(
            _memory_record(
                project_id,
                source_type="reader",
                source_id=report.id,
                chapter_number=report.chapter_number,
                memory_type="summary",
                title=f"第{report.chapter_number}章读者反馈",
                content=content,
                keywords=extract_memory_terms(content),
                importance_score=2.9 if report.status == "weak" else 1.9,
            )
        )

    records = sorted(
        records,
        key=lambda item: (item.chapter_number, item.importance_score, item.updated_at),
        reverse=False,
    )
    return store.replace_long_term_memories(project_id, records)


def retrieve_long_term_memories(
    project_id: str,
    *,
    chapter_number: int,
    query_text: str,
    limit: int | None = None,
) -> tuple[list[MemoryRetrievalHit], MemoryRetrievalTrace]:
    settings = get_settings()
    limit = limit or settings.context_max_memories
    records = rebuild_long_term_memory(project_id)
    query_terms = extract_memory_terms(query_text)

    scored: list[tuple[float, LongTermMemoryRecord, list[str]]] = []
    for record in records:
        if record.chapter_number > chapter_number:
            continue
        matched_terms = [term for term in query_terms if term in record.content or term in record.keywords]
        overlap = float(len(matched_terms))
        keyword_overlap = float(len(set(query_terms) & set(record.keywords)))
        recency = max(0.0, 10 - abs(chapter_number - record.chapter_number) * 0.8)
        score = overlap * 2.4 + keyword_overlap * 1.6 + recency + record.importance_score
        if record.memory_type in {"foreshadow", "risk"}:
            score += 0.8
        if score <= record.importance_score + 0.5:
            continue
        reasons = [
            f"matched_terms={', '.join(matched_terms[:6]) or '无'}",
            f"recency={round(recency, 1)}",
            f"importance={record.importance_score}",
        ]
        scored.append((round(score, 2), record, reasons))

    scored.sort(key=lambda item: (item[0], item[1].chapter_number, item[1].importance_score), reverse=True)
    hits = [
        MemoryRetrievalHit(
            record_id=record.id,
            chapter_number=record.chapter_number,
            source_type=record.source_type,
            memory_type=record.memory_type,
            title=record.title,
            content=record.content,
            retrieval_score=score,
            matched_terms=[term for term in query_terms if term in record.content or term in record.keywords][:8],
            reasons=reasons,
        )
        for score, record, reasons in scored[:limit]
    ]
    trace = MemoryRetrievalTrace(
        project_id=project_id,
        chapter_number=chapter_number,
        query_text=query_text,
        query_terms=query_terms[:20],
        selected_record_ids=[item.record_id for item in hits],
        hits=hits,
    )
    store.add_memory_retrieval_trace(project_id, trace)
    return hits, trace
