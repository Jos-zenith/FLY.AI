from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.services.agent_tracker as agent_tracker_module
from app.core.database import Base
from app.main import app
from app.models.agent_run import AccessEvent, AgentRun
from app.services.agent_tracker import AgentRunContext, diff_run, record_access


class _FakeResponse:
    status_code = 200
    content = b'{"usage": {"input_tokens": 11, "output_tokens": 22}}'

    def json(self):
        return {"usage": {"input_tokens": 11, "output_tokens": 22}}


def test_agent_run_context_tracks_declared_vs_observed():
    engine = create_engine("sqlite:///:memory:")
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
