"""The AI asset registry: declared purpose/data sources per monitored asset,
plus the runtime monitoring on/off switch each asset exposes.

Kept separate from prompt_capture.py (which is about what happens to one
prompt) and agent_tracker.py (which is about one agent run) -- this module
is about the standing registry of assets themselves.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ai_asset import AiAsset

# Seeded once, on first startup against an empty table -- these are the
# same asset names used throughout the demo (ChatHero's asset dropdown,
# seed_demo_data.py, the testbed scenarios), so the registry actually
# describes what the rest of the app already produces traffic for,
# instead of being a second, disconnected list of asset names.
DEFAULT_ASSETS = [
    {
        "name": "customer-support",
        "declared_purpose": "Handle customer support tickets: refunds, account issues, order questions.",
        "declared_data_sources": ["FAQ DB"],
    },
    {
        "name": "billing-agent",
        "declared_purpose": "Answer billing and payment questions, and process refund requests.",
        "declared_data_sources": ["Billing DB"],
    },
    {
        "name": "chat",
        "declared_purpose": "General-purpose assistant chat with no dedicated backend data source.",
        "declared_data_sources": [],
    },
]


def ensure_default_assets(db: Session) -> None:
    """Idempotently seed the registry with the default assets above.

    Safe to call on every startup: only inserts assets that don't already
    exist by name, and never overwrites a monitoring_enabled flag someone
    has already toggled.
    """
    existing_names = {name for (name,) in db.query(AiAsset.name).all()}
    created = False
    for asset in DEFAULT_ASSETS:
        if asset["name"] in existing_names:
            continue
        db.add(AiAsset(**asset, monitoring_enabled=True))
        created = True
    if created:
        db.commit()


def get_or_register_asset(db: Session, name: str) -> AiAsset:
    """Fetch an asset's registry row, auto-registering it (declared as
    empty/unknown) if traffic arrives for a name nobody registered yet.

    This mirrors how the rest of the app already behaves: `/chat` accepts
    any `ai_asset` string without requiring pre-registration, so the
    registry has to be able to catch up rather than reject unknown
    traffic -- an unregistered asset just starts with no declared purpose
    or sources until someone fills them in.
    """
    normalized = (name or "unknown").strip()
    row = db.query(AiAsset).filter(AiAsset.name == normalized).first()
    if row is None:
        row = AiAsset(name=normalized, declared_purpose=None, declared_data_sources=[], monitoring_enabled=True)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row
