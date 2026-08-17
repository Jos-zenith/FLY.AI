from fastapi import APIRouter, Query

from app.db.session import get_db
from app.models import AgentRun, PromptLog
from app.services.agent_tracker import diff_run

router = APIRouter(prefix="/dashboard")


@router.get("/prompts")
def list_prompts(ai_asset: str | None = None, has_pii: bool | None = None, limit: int = 50):
    db = next(get_db())
    q = db.query(PromptLog)
    if ai_asset:
        q = q.filter(PromptLog.ai_asset == ai_asset)
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
def pii_summary_by_asset():
    db = next(get_db())
    logs = db.query(PromptLog).all()
    summary: dict[str, dict[str, int]] = {}
    for log in logs:
        bucket = summary.setdefault(log.ai_asset, {})
        for label, count in (log.pii_detected or {}).items():
            bucket[label] = bucket.get(label, 0) + count
    return summary


@router.get("/runs")
def list_runs(agent_id: str | None = None, only_unexpected: bool = False, limit: int = 50):
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
def get_run(run_id: str):
    return diff_run(run_id)
