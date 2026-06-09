"""Per-request context propagated into tools without rebuilding the graph."""

from __future__ import annotations

from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id")
context_id_var: ContextVar[str] = ContextVar("context_id")
depth_var: ContextVar[int] = ContextVar("depth", default=0)
