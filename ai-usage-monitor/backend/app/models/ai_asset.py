from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class AiAsset(Base):
    """The AI asset registry: one row per monitored AI application/tool.

    This is what turns `ai_asset` from a free-text label attached to
    events into an actual registry entry with a declared purpose and
    declared data sources -- the thing governance needs to compare
    "what this asset is supposed to do" against real usage, the same
    shape as the agent-level declared-vs-observed check in
    `agent_tracker.py`, just at the asset level instead of the run level.
    """

    __tablename__ = "ai_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    declared_purpose = Column(String(500), nullable=True)
    # List[str], e.g. ["FAQ DB", "Orders DB"] -- what this asset is
    # declared to touch. Stored as JSON rather than a join table since a
    # handful of string labels per asset doesn't earn its own table for
    # a project this size.
    declared_data_sources = Column(JSON, nullable=False, default=list)
    # The runtime, employee-facing on/off switch -- separate from the
    # global `PROMPT_MONITORING_ENABLED` env var and the static
    # `PROMPT_MONITORING_DISABLED_ASSETS` list in Settings. Those are
    # deploy-time configuration; this is the one an end user can flip
    # from the app itself without redeploying.
    monitoring_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
