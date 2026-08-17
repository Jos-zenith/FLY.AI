from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(200), nullable=False)
    declared_sources = Column(Text, nullable=False)
    tools_invoked = Column(JSON, nullable=True, default=list)
    tool_calls = Column(JSON, nullable=True, default=list)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="running")

    access_events = relationship("AccessEvent", back_populates="run", cascade="all, delete-orphan")
