from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

import app.db.session as db_session
from app.models.access_event import AccessEvent
from app.models.agent_run import AgentRun
from app.services.pii import redact

_current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)
_current_tools_invoked: ContextVar[list[str] | None] = ContextVar("current_tools_invoked", default=None)
_current_tool_calls: ContextVar[list[dict[str, Any]] | None] = ContextVar("current_tool_calls", default=None)


class AgentRunContext:
    """Wrap an agent execution so every access inside it gets attributed."""

    def __init__(
        self,
        agent_id: str,
        declared_sources: list[str],
        tools_invoked: list[str] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ):
        self.agent_id = agent_id
        self.declared_sources = declared_sources
        self.tools_invoked = tools_invoked or []
        self.tool_calls = tool_calls or []
        self.run_id = None

    def __enter__(self):
        db = next(db_session.get_db())
        run = AgentRun(
            agent_id=self.agent_id,
            declared_sources=",".join(self.declared_sources),
            tools_invoked=list(self.tools_invoked),
            tool_calls=list(self.tool_calls),
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        self.run_id = str(run.id)
        self._token = _current_run_id.set(self.run_id)
        self._tools_token = _current_tools_invoked.set(list(self.tools_invoked))
        self._tool_calls_token = _current_tool_calls.set(list(self.tool_calls))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        db = next(db_session.get_db())
        run = db.get(AgentRun, int(self.run_id))
        if run is not None:
            run.status = "failed" if exc_type else "completed"
            run.finished_at = datetime.now(timezone.utc)
            run.tools_invoked = list(_current_tools_invoked.get())
            run.tool_calls = list(_current_tool_calls.get() or [])
            db.commit()
        _current_run_id.reset(self._token)
        _current_tools_invoked.reset(self._tools_token)
        _current_tool_calls.reset(self._tool_calls_token)


def record_access(source_name: str, source_type: str = "database"):
    """Call this from inside every tool/DB wrapper the agent can reach."""
    run_id = _current_run_id.get()
    if run_id is None:
        return
    db = next(db_session.get_db())
    db.add(
        AccessEvent(
            run_id=int(run_id),
            source_name=source_name,
            source_type=source_type,
            accessed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def _redact_tool_arguments(value: Any):
    if isinstance(value, str):
        redacted, _ = redact(value)
        return redacted
    if isinstance(value, dict):
        return {key: _redact_tool_arguments(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_tool_arguments(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_tool_arguments(item) for item in value)
    return value


def record_tool_invocation(tool_name: str, arguments: dict[str, Any] | None = None):
    run_id = _current_run_id.get()
    if run_id is None:
        return
    invoked = list(_current_tools_invoked.get() or [])
    if tool_name not in invoked:
        invoked.append(tool_name)
    _current_tools_invoked.set(invoked)

    calls = list(_current_tool_calls.get() or [])
    sanitized_args = _redact_tool_arguments(arguments or {})
    calls.append({"tool_name": tool_name, "arguments": sanitized_args})
    _current_tool_calls.set(calls)


def diff_run(run_id: str, db: Any | None = None) -> dict:
    if db is None:
        db = next(db_session.get_db())

    run = db.get(AgentRun, int(run_id))
    if run is None:
        raise ValueError(f"Unknown run_id: {run_id}")

    declared = set((run.declared_sources or "").split(",")) - {""}
    observed = {event.source_name for event in run.access_events}
    tools_invoked = list(run.tools_invoked or [])
    tool_calls = list(run.tool_calls or [])
    unexpected = sorted(observed - declared)
    return {
        "run_id": run_id,
        "agent_id": run.agent_id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "declared": sorted(declared),
        "observed": sorted(observed),
        "tools_invoked": tools_invoked,
        "tool_calls": tool_calls,
        "unexpected": unexpected,
        "unused_declared": sorted(declared - observed),
        "governance_alert": bool(unexpected),
        "governance_alert_reason": (
            f"Observed sources not declared: {', '.join(unexpected)}" if unexpected else None
        ),
    }


def compare_declared_vs_observed(declared_tools: list[str], observed_tools: list[str]):
    declared_set = set(declared_tools or [])
    observed_set = set(observed_tools or [])

    missing = sorted(declared_set - observed_set)
    unexpected = sorted(observed_set - declared_set)

    return {
        "declared": declared_tools,
        "observed": observed_tools,
        "missing": missing,
        "unexpected": unexpected,
        "match": not missing and not unexpected,
    }
