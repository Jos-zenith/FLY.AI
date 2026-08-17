from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.dashboard import router as dashboard_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models.usage_event import UsageEvent
from app.observability.llm_gateway import router as llm_gateway_router
from app.services.agent_tracker import compare_declared_vs_observed
from app.services.pii import detect_pii, redact

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0")
app.include_router(llm_gateway_router)
app.include_router(dashboard_router)

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
def chat(payload: dict, db: Session = Depends(get_db)):
    message = str(payload.get("message", ""))
    sanitized, pii_metadata = redact(message)
    findings = detect_pii(message)

    event = UsageEvent(
        application="chat",
        user_id=str(payload.get("user_id", "anonymous")),
        session_id=str(payload.get("session_id", "unknown")),
        event_type="chat_message",
        payload={"message": sanitized, "pii_detected": pii_metadata},
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "message": sanitized,
        "pii_detected": findings,
        "pii_metadata": pii_metadata,
        "event_id": event.id,
    }


@app.post("/agent/run")
def run_agent(payload: dict):
    declared = payload.get("declared_tools", [])
    observed = payload.get("observed_tools", [])
    return compare_declared_vs_observed(declared, observed)


@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(UsageEvent).count()
    return {"total_events": total, "applications": ["chat", "agent"]}


@app.get("/dashboard/usage")
def dashboard_usage(db: Session = Depends(get_db)):
    events = db.query(UsageEvent).order_by(UsageEvent.created_at.desc()).limit(10).all()
    return [{
        "id": event.id,
        "application": event.application,
        "event_type": event.event_type,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    } for event in events]
