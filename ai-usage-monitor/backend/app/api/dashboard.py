from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func

from app.core.database import Base
from app.core.config import settings
from app.db.session import get_db
from app.models import AgentRun, PromptLog
from app.services.agent_tracker import diff_run
from app.services.prompt_capture import purge_expired_prompt_logs


def _pii_total_for_log(log: PromptLog) -> int:
    if not log.pii_detected:
        return 0
    if isinstance(log.pii_detected, dict):
        return sum(int(value) for value in log.pii_detected.values() if value)
    return 0


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

    logs = db.query(PromptLog).all()

    usage_by_day = defaultdict(lambda: {"requests": 0, "pii_events": 0, "input_tokens": 0, "output_tokens": 0, "failed": 0})
    model_usage = defaultdict(lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "avg_latency_ms": 0.0, "latency_samples": 0})
    asset_usage = defaultdict(lambda: {"requests": 0, "pii_events": 0, "input_tokens": 0, "output_tokens": 0, "failed": 0, "avg_latency_ms": 0.0, "latency_samples": 0})

    for log in logs:
        day = log.created_at.date().isoformat() if log.created_at else "unknown"
        usage = usage_by_day[day]
        usage["requests"] += 1
        usage["pii_events"] += _pii_total_for_log(log)
        usage["input_tokens"] += int(log.input_tokens or 0)
        usage["output_tokens"] += int(log.output_tokens or 0)
        usage["failed"] += 1 if (log.status or 0) >= 400 else 0

        model = model_usage.setdefault((log.model or "unknown"), {"requests": 0, "input_tokens": 0, "output_tokens": 0, "avg_latency_ms": 0.0, "latency_samples": 0})
        model["requests"] += 1
        model["input_tokens"] += int(log.input_tokens or 0)
        model["output_tokens"] += int(log.output_tokens or 0)
        model["avg_latency_ms"] += float(log.latency_ms or 0)
        model["latency_samples"] += 1

        asset = asset_usage.setdefault(log.ai_asset or "unknown", {"requests": 0, "pii_events": 0, "input_tokens": 0, "output_tokens": 0, "failed": 0, "avg_latency_ms": 0.0, "latency_samples": 0})
        asset["requests"] += 1
        asset["pii_events"] += _pii_total_for_log(log)
        asset["input_tokens"] += int(log.input_tokens or 0)
        asset["output_tokens"] += int(log.output_tokens or 0)
        asset["failed"] += 1 if (log.status or 0) >= 400 else 0
        asset["avg_latency_ms"] += float(log.latency_ms or 0)
        asset["latency_samples"] += 1

    usage_over_time = []
    for date_key in sorted(usage_by_day):
        row = usage_by_day[date_key]
        usage_over_time.append(
            {
                "date": date_key,
                "requests": int(row["requests"]),
                "pii_events": int(row["pii_events"]),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "total_tokens": int(row["input_tokens"] + row["output_tokens"]),
                "avg_latency_ms": 0.0,
                "failed": int(row["failed"]),
            }
        )

    model_usage_rows = []
    for model_name, row in sorted(model_usage.items(), key=lambda item: item[1]["requests"], reverse=True):
        model_usage_rows.append(
            {
                "model": model_name,
                "requests": int(row["requests"]),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "avg_latency_ms": round(float(row["avg_latency_ms"] / row["latency_samples"]) if row["latency_samples"] else 0.0, 2),
            }
        )

    asset_rows = []
    for asset_name, row in sorted(asset_usage.items(), key=lambda item: item[1]["requests"], reverse=True):
        asset_rows.append(
            {
                "asset": asset_name,
                "requests": int(row["requests"]),
                "pii_events": int(row["pii_events"]),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "avg_latency_ms": round(float(row["avg_latency_ms"] / row["latency_samples"]) if row["latency_samples"] else 0.0, 2),
                "failed": int(row["failed"]),
            }
        )

    total_requests = len(logs)
    total_failures = sum(1 for log in logs if (log.status or 0) >= 400)
    total_input = sum(int(log.input_tokens or 0) for log in logs)
    total_output = sum(int(log.output_tokens or 0) for log in logs)
    avg_latency = sum(float(log.latency_ms or 0) for log in logs) / total_requests if total_requests else 0

    total_pii_events = sum(_pii_total_for_log(log) for log in logs)

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
        "model_usage": model_usage_rows,
        # Per-asset rows only -- no synthetic "all assets" row mixed in.
        # Anything that wants the grand total reads it explicitly from
        # token_usage/latency/failure_rate below instead of having to know
        # to filter a magic asset name out of this list.
        "asset_comparison": asset_rows,
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
        "pii_events": {
            "total": total_pii_events,
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
