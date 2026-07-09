"""Deterministic clause segmentation.

Splits a contract into clauses on blank-line boundaries while preserving exact
character offsets, so every clause's (start, end) round-trips: text[start:end]
== clause.text. Those offsets become the grounded citations downstream.

An LLM-assisted segmenter for messy documents is planned (see SPEC §8); this
heuristic version is deliberately simple and fully deterministic so it is
trivially testable.
"""

from __future__ import annotations

import re

from app.models.schemas import Clause

_SPLIT = re.compile(r"\n\s*\n")


def segment(text: str) -> list[Clause]:
    clauses: list[Clause] = []
    index = 0
    cursor = 0
    for chunk in _SPLIT.split(text):
        # Locate this chunk from the current cursor to keep offsets exact even
        # when the delimiter run varies in length.
        chunk_start = text.find(chunk, cursor)
        if chunk_start == -1:  # pragma: no cover - defensive
            chunk_start = cursor
        stripped = chunk.strip()
        if stripped:
            lead = len(chunk) - len(chunk.lstrip())
            start = chunk_start + lead
            end = start + len(stripped)
            clauses.append(Clause(index=index, text=text[start:end], start=start, end=end))
            index += 1
        cursor = chunk_start + len(chunk)
    return clauses
