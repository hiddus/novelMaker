from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from app.core.config import get_settings
from app.schemas.domain import LongTermMemoryRecord, MemoryIndexStatus, MemoryRetrievalHit
from app.services.retrieval_features import (
    build_sparse_vector,
    dense_vector_from_sparse,
    sparse_cosine_similarity,
    sparse_norm,
    split_terms,
)


def _normalize_backend_name(value: str) -> str:
    return value.strip().lower() if value else "local"


def _configured_backend() -> str:
    backend = _normalize_backend_name(get_settings().retrieval_backend)
    return backend if backend in {"local", "qdrant"} else "local"


def _project_index_path(project_id: str) -> Path:
    settings = get_settings()
    return settings.vector_index_root() / f"{project_id}.json"


def _collection_name(project_id: str) -> str:
    settings = get_settings()
    return f"{settings.qdrant_collection_prefix}_{project_id}".replace("-", "_")


def _record_sparse_vector(record: LongTermMemoryRecord) -> dict[int, float]:
    settings = get_settings()
    return build_sparse_vector(
        record.title,
        record.content,
        keywords=record.keywords,
        dimensions=settings.vector_dimensions,
    )


def _record_display_terms(record: LongTermMemoryRecord) -> set[str]:
    return set(split_terms(" ".join([record.title, record.content] + record.keywords)))


def _serialize_vector(vector: dict[int, float]) -> dict[str, float]:
    return {str(index): round(value, 6) for index, value in vector.items()}


def _deserialize_vector(vector: dict[str, float]) -> dict[int, float]:
    return {int(index): float(value) for index, value in vector.items()}


def _load_index_payload(project_id: str) -> dict[str, Any]:
    path = _project_index_path(project_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_index_payload(project_id: str, payload: dict[str, Any]) -> None:
    path = _project_index_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _http_json(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    headers = {"Content-Type": "application/json"}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(url, data=payload, method=method, headers=headers)
    with request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _prepare_index_documents(records: list[LongTermMemoryRecord]) -> list[dict[str, Any]]:
    settings = get_settings()
    documents: list[dict[str, Any]] = []
    for record in records:
        sparse_vector = _record_sparse_vector(record)
        documents.append(
            {
                "record_id": record.id,
                "chapter_number": record.chapter_number,
                "memory_type": record.memory_type,
                "importance_score": record.importance_score,
                "keywords": record.keywords,
                "display_terms": sorted(_record_display_terms(record)),
                "norm": round(sparse_norm(sparse_vector), 6),
                "sparse_vector": _serialize_vector(sparse_vector),
                "dense_vector": [round(value, 6) for value in dense_vector_from_sparse(sparse_vector, settings.vector_dimensions)],
            }
        )
    return documents


def _sync_qdrant(project_id: str, documents: list[dict[str, Any]]) -> tuple[str, str, datetime | None]:
    settings = get_settings()
    if not settings.qdrant_url:
        return "unavailable", "未配置 Qdrant URL，已保留本地向量后备。", None

    base_url = settings.qdrant_url.rstrip("/")
    collection_name = _collection_name(project_id)
    try:
        _http_json(
            "POST",
            f"{base_url}/collections/{parse.quote(collection_name)}",
            {
                "vectors_config": {
                    "size": settings.vector_dimensions,
                    "distance": "Cosine",
                }
            },
        )
    except error.HTTPError as exc:
        if exc.code != 409:
            return "unavailable", f"Qdrant collection 创建失败：HTTP {exc.code}", None
    except Exception as exc:  # pragma: no cover - network path
        return "unavailable", f"Qdrant collection 创建失败：{exc}", None

    points = [
        {
            "id": item["record_id"],
            "vector": item["dense_vector"],
            "payload": {
                "record_id": item["record_id"],
                "chapter_number": item["chapter_number"],
                "memory_type": item["memory_type"],
                "importance_score": item["importance_score"],
            },
        }
        for item in documents
    ]
    try:
        _http_json(
            "PUT",
            f"{base_url}/collections/{parse.quote(collection_name)}/points?wait=true",
            {"points": points},
        )
    except Exception as exc:  # pragma: no cover - network path
        return "unavailable", f"Qdrant upsert 失败：{exc}", None

    return "ready", "Qdrant collection 已同步，可直接执行远端向量检索。", datetime.now(UTC)


def rebuild_memory_index(project_id: str, records: list[LongTermMemoryRecord]) -> MemoryIndexStatus:
    backend = _configured_backend()
    documents = _prepare_index_documents(records)
    qdrant_status = {"status": "unavailable", "detail": "", "synced_at": None}
    if backend == "qdrant":
        status, detail, synced_at = _sync_qdrant(project_id, documents)
        qdrant_status = {
            "status": status,
            "detail": detail,
            "synced_at": synced_at.isoformat() if synced_at else None,
        }

    now = datetime.now(UTC)
    payload = {
        "project_id": project_id,
        "configured_backend": backend,
        "dimensions": get_settings().vector_dimensions,
        "indexed_at": now.isoformat(),
        "record_count": len(records),
        "collection_name": _collection_name(project_id),
        "documents": documents,
        "qdrant": qdrant_status,
    }
    _write_index_payload(project_id, payload)
    return get_memory_index_status(project_id)


def get_memory_index_status(project_id: str) -> MemoryIndexStatus:
    backend = _configured_backend()
    payload = _load_index_payload(project_id)
    path = _project_index_path(project_id)
    if not payload:
        return MemoryIndexStatus(
            project_id=project_id,
            backend=backend,  # type: ignore[arg-type]
            backend_status="unavailable",
            ready=False,
            indexed_records=0,
            index_location=str(path),
            collection_name=_collection_name(project_id),
            detail="尚未构建向量索引。",
        )

    backend_status = "ready"
    detail = "本地稀疏向量索引可用。"
    if backend == "qdrant":
        qdrant = payload.get("qdrant") or {}
        if qdrant.get("status") == "ready":
            backend_status = "ready"
            detail = str(qdrant.get("detail") or "Qdrant 远端索引可用。")
        else:
            backend_status = "degraded"
            detail = str(qdrant.get("detail") or "Qdrant 不可用，当前回退到本地向量索引。")

    indexed_at = payload.get("indexed_at")
    return MemoryIndexStatus(
        project_id=project_id,
        backend=backend,  # type: ignore[arg-type]
        backend_status=backend_status,  # type: ignore[arg-type]
        ready=bool(payload.get("documents")),
        indexed_records=int(payload.get("record_count") or 0),
        last_indexed_at=datetime.fromisoformat(indexed_at) if indexed_at else None,
        index_location=str(path),
        collection_name=str(payload.get("collection_name") or _collection_name(project_id)),
        detail=detail,
    )


def _local_search(
    project_id: str,
    records: list[LongTermMemoryRecord],
    *,
    chapter_number: int,
    query_text: str,
    limit: int,
) -> tuple[list[MemoryRetrievalHit], list[str]]:
    settings = get_settings()
    payload = _load_index_payload(project_id)
    documents = payload.get("documents", [])
    record_map = {item.id: item for item in records}
    query_keywords = split_terms(query_text)
    query_sparse = build_sparse_vector(query_text, keywords=query_keywords, dimensions=settings.vector_dimensions)
    query_norm = sparse_norm(query_sparse)
    scored: list[tuple[float, MemoryRetrievalHit]] = []
    for document in documents:
        record = record_map.get(str(document.get("record_id")))
        if record is None or record.chapter_number > chapter_number:
            continue
        vector_score = sparse_cosine_similarity(
            query_sparse,
            _deserialize_vector(document.get("sparse_vector", {})),
            left_norm=query_norm,
            right_norm=float(document.get("norm") or 0.0),
        )
        display_terms = set(document.get("display_terms") or [])
        matched_terms = [term for term in query_keywords if term in display_terms][:8]
        lexical_score = len(matched_terms) * 0.9 + len(set(query_keywords) & set(record.keywords)) * 0.7
        recency_score = max(0.0, 10 - abs(chapter_number - record.chapter_number) * 0.8)
        total = vector_score * 12 + lexical_score + recency_score * 0.6 + record.importance_score
        if record.memory_type in {"foreshadow", "risk"}:
            total += 0.6
        if total <= record.importance_score + 0.3:
            continue
        hit = MemoryRetrievalHit(
            record_id=record.id,
            chapter_number=record.chapter_number,
            source_type=record.source_type,
            memory_type=record.memory_type,
            title=record.title,
            content=record.content,
            retrieval_score=round(total, 3),
            retrieval_backend="local",
            vector_score=round(vector_score, 4),
            lexical_score=round(lexical_score, 3),
            matched_terms=matched_terms,
            reasons=[
                "backend=local",
                f"vector={round(vector_score, 4)}",
                f"lexical={round(lexical_score, 3)}",
                f"recency={round(recency_score, 2)}",
                f"importance={record.importance_score}",
            ],
        )
        scored.append((total, hit))

    scored.sort(key=lambda item: (item[0], item[1].chapter_number, item[1].vector_score), reverse=True)
    return [item for _, item in scored[:limit]], query_keywords


def _search_qdrant(
    project_id: str,
    *,
    chapter_number: int,
    query_text: str,
    limit: int,
) -> tuple[dict[str, Any], list[str]]:
    settings = get_settings()
    query_keywords = split_terms(query_text)
    query_sparse = build_sparse_vector(query_text, keywords=query_keywords, dimensions=settings.vector_dimensions)
    body = {
        "vector": dense_vector_from_sparse(query_sparse, settings.vector_dimensions),
        "limit": max(limit * 4, settings.vector_candidate_limit),
        "with_payload": True,
        "with_vector": False,
    }
    base_url = settings.qdrant_url.rstrip("/")
    collection_name = _collection_name(project_id)
    response = _http_json(
        "POST",
        f"{base_url}/collections/{parse.quote(collection_name)}/points/query",
        body,
    )
    return response, query_keywords


def search_memory_records(
    project_id: str,
    records: list[LongTermMemoryRecord],
    *,
    chapter_number: int,
    query_text: str,
    limit: int,
) -> tuple[list[MemoryRetrievalHit], MemoryIndexStatus, str, list[str]]:
    status = get_memory_index_status(project_id)
    backend = "local"
    if status.backend == "qdrant" and status.backend_status == "ready":
        try:
            response, query_keywords = _search_qdrant(
                project_id,
                chapter_number=chapter_number,
                query_text=query_text,
                limit=limit,
            )
            record_map = {item.id: item for item in records}
            points = response.get("points") or response.get("result") or []
            hits: list[MemoryRetrievalHit] = []
            for point in points:
                payload = point.get("payload") or {}
                record = record_map.get(str(payload.get("record_id") or point.get("id")))
                if record is None or record.chapter_number > chapter_number:
                    continue
                matched_terms = [term for term in query_keywords if term in _record_display_terms(record)][:8]
                lexical_score = len(matched_terms) * 0.8 + len(set(query_keywords) & set(record.keywords)) * 0.6
                similarity = float(point.get("score") or 0.0)
                total = similarity * 12 + lexical_score + record.importance_score
                if record.memory_type in {"foreshadow", "risk"}:
                    total += 0.6
                hits.append(
                    MemoryRetrievalHit(
                        record_id=record.id,
                        chapter_number=record.chapter_number,
                        source_type=record.source_type,
                        memory_type=record.memory_type,
                        title=record.title,
                        content=record.content,
                        retrieval_score=round(total, 3),
                        retrieval_backend="qdrant",
                        vector_score=round(similarity, 4),
                        lexical_score=round(lexical_score, 3),
                        matched_terms=matched_terms,
                        reasons=[
                            "backend=qdrant",
                            f"vector={round(similarity, 4)}",
                            f"lexical={round(lexical_score, 3)}",
                            f"importance={record.importance_score}",
                        ],
                    )
                )
                if len(hits) >= limit:
                    break
            return hits, status, "qdrant", query_keywords
        except Exception:
            degraded_status = status.model_copy(
                update={
                    "backend_status": "degraded",
                    "detail": "Qdrant 查询失败，已自动回退到本地向量索引。",
                }
            )
            hits, query_keywords = _local_search(
                project_id,
                records,
                chapter_number=chapter_number,
                query_text=query_text,
                limit=limit,
            )
            return hits, degraded_status, "local", query_keywords

    hits, query_keywords = _local_search(
        project_id,
        records,
        chapter_number=chapter_number,
        query_text=query_text,
        limit=limit,
    )
    return hits, status, backend, query_keywords
