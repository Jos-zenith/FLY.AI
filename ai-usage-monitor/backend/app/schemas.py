"""Request/response contracts for the public API.

These exist for two reasons that matter more here than in most demos:

1. `/chat` and `/agent/run` are the exact two endpoints an evaluator will
   hit first (see /docs). Untyped `dict` payloads mean FastAPI can't
   validate input, can't render a real request schema in Swagger, and
   silently accepts garbage. Typed models fix all three.
2. This project's whole pitch is "trustworthy governance layer." A
   governance tool with unvalidated inputs undercuts its own premise.

Endpoints whose payload shape is genuinely dynamic (per-asset PII label
counts, per-day analytics buckets) are intentionally left as typed dicts
inside a model (e.g. `dict[str, int]`) rather than forced into rigid
fields that would just be wrong the next time a new PII label is added.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(default="", description="Raw prompt text, exactly as a user would type it.")
    ai_asset: str = Field(default="chat", description="Which monitored AI tool this prompt is simulating.")
    model: str = Field(default="mock-model", description="Model name to record against this request.")
    user_id: str = Field(default="anonymous")
    session_id: str = Field(default="unknown")


class ChatResponse(BaseModel):
    message: str = Field(description="The sanitized prompt, with any detected PII replaced by <TYPE> markers.")
    pii_detected: list[dict] = Field(description="Structured findings: type, detection source, confidence score.")
    pii_metadata: dict[str, int] = Field(description="Counts per PII label, e.g. {'EMAIL': 1, 'PHONE': 1}.")
    response: str
    model: str
    event_id: int


class AgentRunRequest(BaseModel):
    agent_id: str = Field(default="testbed-agent")
    message: str | None = Field(default=None, description="Simulated customer message the agent is responding to.")
    ticket_id: str | None = None
    query_orders: bool = Field(
        default=False,
        description="Force the agent to also query Orders DB, a source it never declared -- reproduces a scope violation on demand.",
    )
    customer_mentions_orders: bool = Field(
        default=False,
        description="Alternate trigger name for the same scope-violation path, kept for testbed compatibility.",
    )


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict


class AgentRunResponse(BaseModel):
    run_id: str
    agent_id: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    declared: list[str]
    observed: list[str]
    unexpected: list[str] = Field(description="Sources touched but never declared -- the scope-violation signal.")
    unused_declared: list[str] = Field(description="Sources declared but never actually touched this run.")
    tools_invoked: list[str]
    tool_calls: list[ToolCall]
    governance_alert: bool = Field(description="True when this run touched at least one undeclared source.")
    governance_alert_reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str


class DashboardSummary(BaseModel):
    total_events: int
    applications: list[str]


class UsageEventOut(BaseModel):
    id: int
    application: str
    event_type: str
    created_at: datetime | None


class AiAssetOut(BaseModel):
    name: str
    declared_purpose: str | None
    declared_data_sources: list[str]
    monitoring_enabled: bool
    updated_at: datetime | None


class AssetMonitoringUpdate(BaseModel):
    monitoring_enabled: bool = Field(description="Turn prompt monitoring on/off for this asset at runtime.")
