from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func

from app.core.config import settings
from app.db.session import get_db
from app.models import AgentRun, PromptLog
from app.services.agent_tracker import diff_run
from app.services.prompt_capture import purge_expired_prompt_logs


def require_dashboard_access(x_api_key: str | None = Header(default=None, alias="X-API-Key"), authorization: str | None = Header(default=None)):
    if not settings.access_control_enabled:
        return

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    else:
        token = x_api_key

    if token != settings.monitor_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Demo mode protected: provide the configured X-API-Key or Authorization: Bearer token.",
        )

router = APIRouter(prefix="/dashboard")


@router.get("/prompts")
def list_prompts(
    ai_asset: str | None = None,
    search: str | None = None,
    has_pii: bool | None = None,
    limit: int = 50,
    _=Depends(require_dashboard_access),
):
    db = next(get_db())
    purge_expired_prompt_logs(db)
    q = db.query(PromptLog)
    if ai_asset:
        q = q.filter(PromptLog.ai_asset == ai_asset)
    if search:
        q = q.filter(PromptLog.sanitized_prompt.ilike(f"%{search}%"))
    if has_pii is True:
        q = q.filter(PromptLog.pii_detected != {})
    logs = q.order_by(PromptLog.id.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "ai_asset": log.ai_asset,
            "model": log.model,
            "sanitized_prompt": log.sanitized_prompt,
            "pii_detected": log.pii_detected,
            "tokens": {"input": log.input_tokens, "output": log.output_tokens},
            "latency_ms": log.latency_ms,
        }
        for log in logs
    ]


@router.get("/prompts/pii-summary")
def pii_summary_by_asset(_=Depends(require_dashboard_access)):
    db = next(get_db())
    logs = db.query(PromptLog).all()
    summary: dict[str, dict[str, int]] = {}
    for log in logs:
        bucket = summary.setdefault(log.ai_asset, {})
        for label, count in (log.pii_detected or {}).items():
            bucket[label] = bucket.get(label, 0) + count
    return summary


@router.get("/analytics")
def usage_analytics(_=Depends(require_dashboard_access)):
    db = next(get_db())

    request_rows = db.query(
        func.date(PromptLog.created_at).label("date"),
        func.count(PromptLog.id).label("requests"),
        func.sum(case((PromptLog.pii_detected.isnot(None), 1), else_=0)).label("pii_events"),
        func.coalesce(func.sum(PromptLog.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(PromptLog.output_tokens), 0).label("output_tokens"),
        func.avg(PromptLog.latency_ms).label("avg_latency_ms"),
        func.sum(case((PromptLog.status >= 400, 1), else_=0)).label("failed"),
    ).group_by(func.date(PromptLog.created_at)).order_by(func.date(PromptLog.created_at)).all()

    usage_over_time = []
    for row in request_rows:
        total_tokens = (row.input_tokens or 0) + (row.output_tokens or 0)
        usage_over_time.append(
            {
                "date": row.date,
                "requests": int(row.requests or 0),
                "pii_events": int(row.pii_events or 0),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "total_tokens": int(total_tokens),
                "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
                "failed": int(row.failed or 0),
            }
        )

    model_rows = db.query(
        PromptLog.model,
        func.count(PromptLog.id).label("requests"),
        func.coalesce(func.sum(PromptLog.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(PromptLog.output_tokens), 0).label("output_tokens"),
        func.avg(PromptLog.latency_ms).label("avg_latency_ms"),
    ).group_by(PromptLog.model).order_by(func.count(PromptLog.id).desc()).all()

    model_usage = [
        {
            "model": row.model or "unknown",
            "requests": int(row.requests or 0),
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
        }
        for row in model_rows
    ]

    asset_rows = db.query(
        PromptLog.ai_asset,
        func.count(PromptLog.id).label("requests"),
        func.sum(case((PromptLog.pii_detected.isnot(None), 1), else_=0)).label("pii_events"),
        func.coalesce(func.sum(PromptLog.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(PromptLog.output_tokens), 0).label("output_tokens"),
        func.avg(PromptLog.latency_ms).label("avg_latency_ms"),
        func.sum(case((PromptLog.status >= 400, 1), else_=0)).label("failed"),
    ).group_by(PromptLog.ai_asset).order_by(func.count(PromptLog.id).desc()).all()

    asset_comparison = [
        {
            "asset": row.ai_asset,
            "requests": int(row.requests or 0),
            "pii_events": int(row.pii_events or 0),
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
            "failed": int(row.failed or 0),
        }
        for row in asset_rows
    ]

    total_requests = db.query(PromptLog).count()
    total_failures = db.query(PromptLog).filter(PromptLog.status >= 400).count()
    total_input = db.query(func.coalesce(func.sum(PromptLog.input_tokens), 0)).scalar() or 0
    total_output = db.query(func.coalesce(func.sum(PromptLog.output_tokens), 0)).scalar() or 0
    avg_latency = db.query(func.avg(PromptLog.latency_ms)).scalar() or 0

    duration_rows = db.query(
        AgentRun.agent_id,
        func.count(AgentRun.id).label("runs"),
        func.avg(
            (func.extract("epoch", AgentRun.finished_at) - func.extract("epoch", AgentRun.started_at))
        ).label("avg_seconds"),
        func.sum(case((AgentRun.status == "failed", 1), else_=0)).label("failed"),
        func.sum(case((AgentRun.status == "completed", 1), else_=0)).label("completed"),
    ).group_by(AgentRun.agent_id).all()

    agent_run_durations = [
        {
            "agent_id": row.agent_id,
            "runs": int(row.runs or 0),
            "avg_seconds": round(float(row.avg_seconds or 0), 2),
            "failed": int(row.failed or 0),
            "completed": int(row.completed or 0),
        }
        for row in duration_rows
    ]

    return {
        "usage_over_time": usage_over_time,
        "model_usage": model_usage,
        "asset_comparison": asset_comparison,
        "token_usage": {
            "input_tokens": int(total_input),
            "output_tokens": int(total_output),
            "total_tokens": int(total_input + total_output),
        },
        "latency": {
            "avg_latency_ms": round(float(avg_latency), 2),
            "samples": total_requests,
        },
        "failure_rate": {
            "failed": total_failures,
            "total": total_requests,
            "rate": round((total_failures / total_requests * 100) if total_requests else 0.0, 2),
        },
        "agent_run_durations": agent_run_durations,
    }


@router.get("/runs")
def list_runs(agent_id: str | None = None, only_unexpected: bool = False, limit: int = 50, _=Depends(require_dashboard_access)):
    db = next(get_db())
    q = db.query(AgentRun)
    if agent_id:
        q = q.filter(AgentRun.agent_id == agent_id)
    runs = q.order_by(AgentRun.id.desc()).limit(limit).all()
    results = [diff_run(str(run.id)) for run in runs]
    if only_unexpected:
        results = [run for run in results if run["unexpected"]]
    return results


@router.get("/runs/{run_id}")
def get_run(run_id: str, _=Depends(require_dashboard_access)):
    return diff_run(run_id)
