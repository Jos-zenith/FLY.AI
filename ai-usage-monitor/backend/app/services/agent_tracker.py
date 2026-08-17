from contextvars import ContextVar
from datetime import datetime
from typing import Any

import app.db.session as db_session
from app.models.agent_run import AccessEvent, AgentRun

_current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)


class AgentRunContext:
    """Wrap an agent execution so every access inside it gets attributed."""

    def __init__(self, agent_id: str, declared_sources: list[str]):
        self.agent_id = agent_id
        self.declared_sources = declared_sources
        self.run_id = None

    def __enter__(self):
        db = next(db_session.get_db())
        run = AgentRun(
            agent_id=self.agent_id,
            declared_sources=",".join(self.declared_sources),
            started_at=datetime.utcnow(),
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        self.run_id = str(run.id)
        self._token = _current_run_id.set(self.run_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        db = next(db_session.get_db())
        run = db.get(AgentRun, int(self.run_id))
        if run is not None:
            run.status = "failed" if exc_type else "completed"
            run.finished_at = datetime.utcnow()
            db.commit()
        _current_run_id.reset(self._token)


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
            accessed_at=datetime.utcnow(),
        )
    )
    db.commit()


def diff_run(run_id: str, db: Any | None = None) -> dict:
    if db is None:
        db = next(db_session.get_db())

    run = db.get(AgentRun, int(run_id))
    if run is None:
        raise ValueError(f"Unknown run_id: {run_id}")

    declared = set((run.declared_sources or "").split(",")) - {""}
    observed = {event.source_name for event in run.access_events}
    return {
        "run_id": run_id,
        "declared": sorted(declared),
        "observed": sorted(observed),
        "unexpected": sorted(observed - declared),
        "unused_declared": sorted(declared - observed),
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
