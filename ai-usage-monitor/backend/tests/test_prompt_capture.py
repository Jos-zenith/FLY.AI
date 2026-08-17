from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dashboard as dashboard_module
import app.observability.llm_gateway as llm_gateway_module
from app.core.database import Base
from app.main import app
from app.models.prompt_log import PromptLog
from app.services.prompt_capture import purge_expired_prompt_logs


class _FakeResponse:
    status_code = 200
    content = b'{"usage": {"input_tokens": 11, "output_tokens": 22}}'

    def json(self):
        return {"usage": {"input_tokens": 11, "output_tokens": 22}}


def _shared_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine), engine


def test_prompt_capture_sanitizes_and_searches(monkeypatch):
    Session, _ = _shared_session()
    session = Session()

    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))
    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    async def fake_post(self, url, json, headers, timeout):
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    response = client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Contact alice@example.com"}]},
        headers={"x-ai-asset": "customer-support"},
    )

    assert response.status_code == 200

    rows = client.get("/dashboard/prompts", params={"search": "Contact"}).json()
    assert rows
    assert rows[0]["sanitized_prompt"] == "Contact <EMAIL>"
    assert "alice@example.com" not in rows[0]["sanitized_prompt"]
    assert rows[0]["pii_detected"] == {"EMAIL": 1}


def test_prompt_monitoring_can_be_disabled_per_asset(monkeypatch):
    Session, _ = _shared_session()
    session = Session()

    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))
    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    async def fake_post(self, url, json, headers, timeout):
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    monkeypatch.setattr("app.services.prompt_capture.settings.prompt_monitoring_disabled_assets", "customer-support")

    client = TestClient(app)
    response = client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Call Ramesh"}]},
        headers={"x-ai-asset": "customer-support"},
    )

    assert response.status_code == 200
    assert client.get("/dashboard/prompts").json() == []


def test_retention_purges_old_prompt_logs():
    Session, _ = _shared_session()
    session = Session()

    log = PromptLog(
        ai_asset="customer-support",
        model="claude-3",
        sanitized_prompt="hello <EMAIL>",
        pii_detected={"EMAIL": 1},
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    session.query(PromptLog).filter(PromptLog.id == log.id).update(
        {PromptLog.created_at: datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=40)}
    )
    session.commit()

    deleted = purge_expired_prompt_logs(session, retention_days=30)
    assert deleted == 1
    assert session.query(PromptLog).count() == 0