from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.services.agent_tracker as agent_tracker_module
from app.core.database import Base
from app.main import app
from app.models.access_event import AccessEvent
from app.models.agent_run import AgentRun
from app.services.agent_tracker import AgentRunContext, diff_run, record_access


class _FakeResponse:
    status_code = 200
    content = b'{"usage": {"input_tokens": 11, "output_tokens": 22}}'

    def json(self):
        return {"usage": {"input_tokens": 11, "output_tokens": 22}}


def test_agent_run_context_tracks_declared_vs_observed():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    original_get_db = agent_tracker_module.db_session.get_db
    agent_tracker_module.db_session.get_db = lambda: iter([Session()])

    try:
        with AgentRunContext(agent_id="customer-support", declared_sources=["faq_db"]) as run:
            record_access("faq_db")
            record_access("orders_db")

        result = diff_run(run.run_id, db=Session())
        assert result["declared"] == ["faq_db"]
        assert result["observed"] == ["faq_db", "orders_db"]
        assert result["unexpected"] == ["orders_db"]
        assert result["unused_declared"] == []
    finally:
        agent_tracker_module.db_session.get_db = original_get_db


def test_gateway_logs_prompt_and_dashboard_lists_summary(monkeypatch):
    async def fake_post(self, url, json, headers, timeout):
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    payload = {
        "model": "claude-3",
        "messages": [{"role": "user", "content": "Contact alice@example.com"}],
    }

    response = client.post(
        "/gateway/v1/messages",
        json=payload,
        headers={"x-ai-asset": "customer-support"},
    )

    assert response.status_code == 200
    summary = client.get("/dashboard/prompts/pii-summary")
    assert summary.status_code == 200
    data = summary.json()
    assert "customer-support" in data
    assert "EMAIL" in data["customer-support"]

    list_resp = client.get("/dashboard/prompts")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows and rows[0]["ai_asset"] == "customer-support"


def test_chat_endpoint_calls_mock_llm_and_logs_event():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Contact alice@example.com about order 123",
            "user_id": "u-1",
            "session_id": "s-1",
            "model": "mock-model",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "This is a mock LLM response for usage tracking."
    assert data["model"] == "mock-model"
    assert data["event_id"] > 0
    assert "alice@example.com" not in data["message"]
    assert "alice@example.com" not in data["pii_detected"]


def test_agent_endpoint_records_declared_vs_observed(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    original_get_db = agent_tracker_module.db_session.get_db
    agent_tracker_module.db_session.get_db = lambda: iter([Session()])

    try:
        client = TestClient(app)
        response = client.post(
            "/agent/run",
            json={
                "agent_id": "customer-support",
                "query_orders": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["declared"] == ["FAQ DB"]
        assert data["observed"] == ["FAQ DB", "Orders DB"]
        assert data["tools_invoked"] == ["faq_lookup", "orders_lookup"]
        assert data["tool_calls"][0]["tool_name"] == "faq_lookup"
        assert data["tool_calls"][1]["arguments"]["reason"] == "customer_mentions_orders"
        assert data["unexpected"] == ["Orders DB"]
        assert data["unused_declared"] == []
        assert data["governance_alert"] is True
        assert "Orders DB" in data["governance_alert_reason"]
    finally:
        agent_tracker_module.db_session.get_db = original_get_db


