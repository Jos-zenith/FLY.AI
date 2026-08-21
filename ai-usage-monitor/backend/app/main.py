import json

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.dashboard import router as dashboard_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models.usage_event import UsageEvent
from app.observability.llm_gateway import router as llm_gateway_router
from app.observability.otel import initialize_observability
from app.services.agent_tracker import AgentRunContext, diff_run, record_access, record_tool_invocation
from app.services.llm_client import LLMClient
from app.services.pii import detect_pii, redact
from app.services.prompt_capture import capture_prompt_log

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0")
initialize_observability(app)
app.include_router(llm_gateway_router)
app.include_router(dashboard_router)


def require_monitor_access(x_api_key: str | None = Header(default=None, alias="X-API-Key"), authorization: str | None = Header(default=None)):
    if not settings.access_control_enabled:
        return

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    else:
        token = x_api_key

    if token != settings.monitor_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Demo access protected: provide the configured X-API-Key or Authorization: Bearer token.",
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.post("/chat")
def chat(payload: dict, db: Session = Depends(get_db), _=Depends(require_monitor_access)):
    message = str(payload.get("message", ""))
    ai_asset = str(payload.get("ai_asset", "chat"))
    model_name = str(payload.get("model", "mock-model"))

    sanitized, pii_metadata = redact(message)
    findings = detect_pii(message)
    client = LLMClient(model_name=model_name)
    llm_result = client.generate(sanitized)

    event = UsageEvent(
        application="chat",
        user_id=str(payload.get("user_id", "anonymous")),
        session_id=str(payload.get("session_id", "unknown")),
        event_type="chat_message",
        payload=json.dumps({"message": sanitized, "pii_detected": pii_metadata, "llm_response": llm_result}),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Route through the same safe-capture pipeline the /gateway path uses,
    # so /chat traffic also shows up in /dashboard/analytics and
    # /dashboard/prompts, and respects the same per-asset monitoring
    # toggle and retention policy as every other AI asset instead of being
    # invisible to governance queries.
    capture_prompt_log(
        db,
        ai_asset=ai_asset,
        model=model_name,
        prompt_text=message,
        status=200,
    )

    return {
        "message": sanitized,
        "pii_detected": findings,
        "pii_metadata": pii_metadata,
        "response": llm_result["response"],
        "model": llm_result["model"],
        "event_id": event.id,
    }


@app.post("/agent/run")
def run_agent(payload: dict, _=Depends(require_monitor_access)):
    agent_id = str(payload.get("agent_id", "testbed-agent"))
    declared = ["FAQ DB"]
    should_query_orders = bool(payload.get("query_orders") or payload.get("customer_mentions_orders") or False)

    tools_invoked = ["faq_lookup"]
    if should_query_orders:
        tools_invoked.append("orders_lookup")

    with AgentRunContext(agent_id=agent_id, declared_sources=declared, tools_invoked=tools_invoked) as run:
        record_tool_invocation("faq_lookup", {"query": payload.get("message", "support ticket")})
        record_access("FAQ DB")
        if should_query_orders:
            record_tool_invocation(
                "orders_lookup",
                {"reason": "customer_mentions_orders", "ticket_id": payload.get("ticket_id")},
            )
            record_access("Orders DB")

    return diff_run(run.run_id)


@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), _=Depends(require_monitor_access)):
    total = db.query(UsageEvent).count()
    return {"total_events": total, "applications": ["chat", "agent"]}


@app.get("/dashboard/usage")
def dashboard_usage(db: Session = Depends(get_db), _=Depends(require_monitor_access)):
    events = db.query(UsageEvent).order_by(UsageEvent.created_at.desc()).limit(10).all()
    return [{
        "id": event.id,
        "application": event.application,
        "event_type": event.event_type,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    } for event in events]
