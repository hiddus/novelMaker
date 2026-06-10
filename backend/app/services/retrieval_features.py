from __future__ import annotations

import hashlib
import math
import re

_SEPARATORS = re.compile(r"[\s，。；：、,:;()\[\]（）【】\-_/]+")


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def split_terms(text: str) -> list[str]:
    tokens = [item.strip() for item in _SEPARATORS.split(text) if len(item.strip()) >= 2]
    return list(dict.fromkeys(tokens))


def char_ngrams(text: str, size: int = 2) -> list[str]:
    compact = "".join(ch for ch in text if not ch.isspace())
    if len(compact) < size:
        return []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]


def extract_memory_terms(*parts: str) -> list[str]:
    items: list[str] = []
    for part in parts:
        normalized = normalize_text(part)
        if not normalized:
            continue
        items.extend(split_terms(normalized))
        items.extend(char_ngrams(normalized, size=2))
    return list(dict.fromkeys(item for item in items if len(item) >= 2))


def _stable_index(token: str, dimensions: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % max(1, dimensions)


def build_sparse_vector(
    *parts: str,
    keywords: list[str] | None = None,
    dimensions: int,
) -> dict[int, float]:
    vector: dict[int, float] = {}
    for token in extract_memory_terms(*parts):
        index = _stable_index(token, dimensions)
        vector[index] = vector.get(index, 0.0) + 1.0

    for token in keywords or []:
        normalized = normalize_text(token)
        if len(normalized) < 2:
            continue
        index = _stable_index(normalized, dimensions)
        vector[index] = vector.get(index, 0.0) + 1.35

    return vector


def sparse_norm(vector: dict[int, float]) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))


def sparse_cosine_similarity(
    left: dict[int, float],
    right: dict[int, float],
    *,
    left_norm: float | None = None,
    right_norm: float | None = None,
) -> float:
    if not left or not right:
        return 0.0

    numerator = 0.0
    for index, value in left.items():
        numerator += value * right.get(index, 0.0)

    denominator = (left_norm or sparse_norm(left)) * (right_norm or sparse_norm(right))
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def dense_vector_from_sparse(vector: dict[int, float], dimensions: int) -> list[float]:
    dense = [0.0] * dimensions
    for index, value in vector.items():
        dense[index] = value
    return dense
