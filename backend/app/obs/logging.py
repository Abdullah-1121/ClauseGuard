"""Structured logging + a lightweight span helper.

This is the seam where Langfuse / OpenTelemetry tracing plugs in (see SPEC §9.2).
Today it emits structured, timed events; the `span` context manager is where
per-clause spans get exported once observability keys are configured.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog

log = structlog.get_logger("clauseguard")


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    """Time a unit of work and log its duration. Yields a mutable attrs dict."""
    started = time.perf_counter()
    payload: dict[str, Any] = dict(attrs)
    try:
        yield payload
    finally:
        payload["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
        log.info(name, **payload)
