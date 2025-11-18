"""Structured logging and latency tracking helpers."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Any

try:  # pragma: no cover - optional dependency
    import structlog  # type: ignore
except Exception:  # pragma: no cover - fallback to bundled shim
    from . import _structlog_fallback as structlog


_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def _configure_structlog() -> None:
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        cache_logger_on_first_use=True,
    )


_configure_structlog()


def get_logger():
    """Return the project-wide structlog logger."""

    return structlog.get_logger("wargame_mcp")


logger = get_logger()


class LatencyRecorder:
    """In-memory aggregation of latency metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._latencies: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "total_ms": 0.0, "max_ms": 0.0, "errors": 0.0}
        )

    def observe(self, name: str, duration_ms: float, *, error: bool) -> None:
        with self._lock:
            entry = self._latencies[name]
            entry["count"] += 1
            entry["total_ms"] += duration_ms
            entry["max_ms"] = max(entry["max_ms"], duration_ms)
            if error:
                entry["errors"] += 1

    def summary(self) -> dict[str, dict[str, float]]:
        with self._lock:
            snapshot: dict[str, dict[str, float]] = {}
            for name, entry in self._latencies.items():
                avg = entry["total_ms"] / entry["count"] if entry["count"] else 0.0
                snapshot[name] = {
                    "count": entry["count"],
                    "avg_ms": avg,
                    "max_ms": entry["max_ms"],
                    "errors": entry["errors"],
                }
            return snapshot


latencies = LatencyRecorder()


@contextmanager
def correlation_scope(correlation_id: str | None = None):
    """Context manager that ensures a correlation id is propagated."""

    current = _correlation_id.get()
    if correlation_id is None:
        correlation_id = current
    if correlation_id is None:
        correlation_id = uuid.uuid4().hex
    token = _correlation_id.set(correlation_id)
    try:
        yield correlation_id
    finally:
        _correlation_id.reset(token)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


@contextmanager
def track_latency(operation: str, **fields: Any):
    """Record latency metrics and log them as JSON events."""

    start = time.perf_counter()
    error = False
    try:
        yield
    except Exception:
        error = True
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        latencies.observe(operation, duration_ms, error=error)
        logger.info(
            "latency",
            operation=operation,
            latency_ms=duration_ms,
            error=error,
            correlation_id=get_correlation_id(),
            **fields,
        )
