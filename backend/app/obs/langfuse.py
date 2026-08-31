"""Langfuse tracing seam.

`observe` is a drop-in decorator that sends a span to Langfuse when credentials
are configured, and is a harmless no-op otherwise — so the offline test suite
(no keys) and the traced demo (keys set) run through the same code path.

Keys come from our Settings (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / host);
we mirror them into the LANGFUSE_* env vars the langfuse SDK reads, then reuse
its `observe` decorator. See AGENTS.md obs seam.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, cast

from app.config import get_settings

_LANGFUSE_READY = False


def _point_langfuse_at_settings() -> bool:
    """Provision Langfuse from our settings; no-op when unconfigured."""
    global _LANGFUSE_READY
    if _LANGFUSE_READY:
        return True
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return False
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", s.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", s.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", s.langfuse_host)
    _LANGFUSE_READY = True
    return True


def _decorator(**kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Return a generic decorator that traces when configured, else passes through."""

    def apply[F: Callable[..., Any]](func: F) -> F:
        if not _point_langfuse_at_settings():
            return func
        from langfuse import observe as _langfuse_observe

        # `observe` is itself a decorator; calling it applies the tracing wrapper.
        # Cast: langfuse's public type is overload-heavy, but the decorated fn
        # keeps its own signature.
        return cast(F, _langfuse_observe(func, **kwargs))

    return apply


def observe(func: Callable[..., Any] | None = None, **kwargs: Any) -> Callable[..., Any]:
    """Trace `func` with Langfuse when configured; otherwise pass through.

    Usable as `@observe` or `@observe(name=..., as_type=...)`.
    """
    if func is not None:
        return _decorator(**kwargs)(func)
    return _decorator(**kwargs)


def flush() -> None:
    """Deliver buffered traces; call before a short-lived process exits."""
    if _point_langfuse_at_settings():
        from langfuse import get_client

        get_client().flush()


def is_enabled() -> bool:
    return _point_langfuse_at_settings()
