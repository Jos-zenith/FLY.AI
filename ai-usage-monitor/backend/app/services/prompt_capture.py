from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_asset import AiAsset
from app.models.prompt_log import PromptLog
from app.services.pii import detect_pii, redact


def _disabled_assets() -> set[str]:
    return {
        asset.strip().lower()
        for asset in settings.prompt_monitoring_disabled_assets.split(",")
        if asset.strip()
    }


def prompt_monitoring_disabled(ai_asset: str | None, db: Session | None = None) -> bool:
    """Whether prompt monitoring is off for this asset.

    Two independent switches can disable monitoring, and either is
    sufficient: the deploy-time `PROMPT_MONITORING_DISABLED_ASSETS` env
    var (set once, requires a redeploy to change), and the per-asset
    `AiAsset.monitoring_enabled` registry flag (toggleable at runtime from
    the app itself -- see `app/services/asset_registry.py`). `db` is
    optional so this stays callable in contexts with no DB session; the
    registry check is simply skipped when it's not provided.
    """
    if not settings.prompt_monitoring_enabled:
        return True
    asset = (ai_asset or "unknown").strip().lower()
    if asset in _disabled_assets():
        return True
    if db is not None:
        row = db.query(AiAsset).filter(AiAsset.name == (ai_asset or "unknown").strip()).first()
        if row is not None and not row.monitoring_enabled:
            return True
    return False


def purge_expired_prompt_logs(db: Session, retention_days: int | None = None) -> int:
    days = settings.prompt_log_retention_days if retention_days is None else retention_days
    if days <= 0:
        return 0

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    deleted = db.query(PromptLog).filter(PromptLog.created_at < cutoff).delete(synchronize_session=False)
    if deleted:
        db.commit()
    return deleted


def capture_prompt_log(
    db: Session,
    *,
    ai_asset: str,
    model: str | None,
    prompt_text: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: float | None = None,
    status: int | None = None,
) -> PromptLog | None:
    purge_expired_prompt_logs(db)
    if prompt_monitoring_disabled(ai_asset, db=db):
        return None

    sanitized_prompt, pii_counts = redact(prompt_text)
    prompt_log = PromptLog(
        ai_asset=ai_asset or "unknown",
        model=model,
        sanitized_prompt=sanitized_prompt,
        pii_detected=pii_counts,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=status,
    )
    db.add(prompt_log)
    db.commit()
    db.refresh(prompt_log)
    return prompt_log


def capture_prompt_preview(text: str) -> dict:
    sanitized_prompt, pii_counts = redact(text)
    return {
        "sanitized_prompt": sanitized_prompt,
        "pii_detected": pii_counts,
        "entities": detect_pii(text),
    }