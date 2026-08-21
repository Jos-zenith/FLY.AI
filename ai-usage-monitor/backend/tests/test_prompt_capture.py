from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

provider = trace.get_tracer_provider()
if provider.__class__.__name__ == "ProxyTracerProvider":
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

import app.api.dashboard as dashboard_module
import app.observability.llm_gateway as llm_gateway_module
from app.core.database import Base
from app.main import app
from app.models.prompt_log import PromptLog
from app.services.agent_tracker import AgentRunContext, diff_run, record_access
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


def test_gateway_emits_otel_spans_for_llm_calls(monkeypatch):
    Session, _ = _shared_session()
    session = Session()

    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))
    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    async def fake_post(self, url, json, headers, timeout):
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    client = TestClient(app)
    response = client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Contact alice@example.com"}]},
        headers={"x-ai-asset": "customer-support"},
    )

    assert response.status_code == 200
    span_names = [span.name for span in exporter.get_finished_spans()]
    assert "llm_gateway.call" in span_names
    assert any("customer-support" in str(attr) for span in exporter.get_finished_spans() for attr in span.attributes.values())


def test_gateway_filters_sensitive_headers(monkeypatch):
    Session, _ = _shared_session()
    session = Session()
    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))

    captured = {}

    async def fake_post(self, url, json, headers, timeout):
        captured.update(headers)
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    response = client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Contact alice@example.com"}]},
        headers={
            "x-ai-asset": "customer-support",
            "x-secret-token": "abc123",
            "authorization": "Bearer secret-token",
            "cookie": "session=abc",
            "x-forwarded-for": "1.2.3.4",
        },
    )

    assert response.status_code == 200
    assert "x-ai-asset" in captured
    assert "x-secret-token" not in captured
    assert "authorization" not in captured
    assert "cookie" not in captured
    assert "x-forwarded-for" not in captured


def test_failed_upstream_request_returns_502_and_does_not_store_raw_pii(monkeypatch):
    Session, _ = _shared_session()
    session = Session()
    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))

    async def fake_post(self, url, json, headers, timeout):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    response = client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Contact alice@example.com"}]},
        headers={"x-ai-asset": "customer-support"},
    )

    assert response.status_code == 502
    assert session.query(PromptLog).count() == 0
    assert "alice@example.com" not in response.text


def test_raw_pii_is_absent_from_every_stored_location(monkeypatch):
    Session, _ = _shared_session()
    session = Session()
    monkeypatch.setattr(llm_gateway_module, "get_db", lambda: iter([session]))

    async def fake_post(self, url, json, headers, timeout):
        return _FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    client.post(
        "/gateway/v1/messages",
        json={"model": "claude-3", "messages": [{"role": "user", "content": "Call alice@example.com"}]},
        headers={"x-ai-asset": "customer-support"},
    )

    log = session.query(PromptLog).one()
    assert "alice@example.com" not in log.sanitized_prompt
    assert "alice@example.com" not in str(log.pii_detected)


def test_multiple_agent_runs_remain_distinct(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    monkeypatch.setattr("app.services.agent_tracker.db_session.get_db", lambda: iter([session]))

    with AgentRunContext(agent_id="alpha", declared_sources=["faq_db"]) as first:
        record_access("faq_db")
    with AgentRunContext(agent_id="beta", declared_sources=["orders_db"]) as second:
        record_access("orders_db")

    first_result = diff_run(first.run_id, db=session)
    second_result = diff_run(second.run_id, db=session)

    assert first_result["agent_id"] == "alpha"
    assert second_result["agent_id"] == "beta"
    assert first_result["observed"] == ["faq_db"]
    assert second_result["observed"] == ["orders_db"]


def test_sqlite_fallback_is_used_when_postgres_is_unavailable(monkeypatch):
    import app.core.database as database_module

    monkeypatch.setattr(database_module, "settings", type("S", (), {"database_url": "postgresql+psycopg://postgres:postgres@localhost:5432/demo"})())

    fallback_engine = database_module._make_engine("sqlite:///./pytest_ai_usage_monitor.db")
    assert str(fallback_engine.url).startswith("sqlite")


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


def test_chat_endpoint_traffic_is_visible_in_dashboard_analytics(monkeypatch):
    from app.core.database import get_db as real_get_db

    Session, _ = _shared_session()
    session = Session()

    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))
    def _override_get_db():
        yield session

    app.dependency_overrides[real_get_db] = _override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/chat",
            json={"message": "Contact alice@example.com", "user_id": "u-1", "session_id": "s-1"},
        )
        assert response.status_code == 200

        # /chat should feed the same PromptLog-backed pipeline as /gateway,
        # so it shows up in the sanitized prompt list and the analytics
        # endpoint instead of only living in the UsageEvent table.
        prompts = client.get("/dashboard/prompts", params={"ai_asset": "chat"}).json()
        assert prompts
        assert "alice@example.com" not in prompts[0]["sanitized_prompt"]
        assert prompts[0]["pii_detected"] == {"EMAIL": 1}

        analytics = client.get("/dashboard/analytics").json()
        chat_row = next((row for row in analytics["asset_comparison"] if row["asset"] == "chat"), None)
        assert chat_row is not None
        assert chat_row["requests"] == 1
    finally:
        app.dependency_overrides.pop(real_get_db, None)


def test_chat_endpoint_respects_per_asset_monitoring_disable(monkeypatch):
    from app.core.database import get_db as real_get_db

    Session, _ = _shared_session()
    session = Session()

    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))
    monkeypatch.setattr("app.services.prompt_capture.settings.prompt_monitoring_disabled_assets", "chat")
    def _override_get_db():
        yield session

    app.dependency_overrides[real_get_db] = _override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/chat",
            json={"message": "Call Ramesh", "user_id": "u-1", "session_id": "s-1"},
        )
        assert response.status_code == 200
        assert client.get("/dashboard/prompts", params={"ai_asset": "chat"}).json() == []
    finally:
        app.dependency_overrides.pop(real_get_db, None)


def test_usage_analytics_counts_only_real_pii_detects(monkeypatch):
    import app.api.dashboard as dashboard_module

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    dashboard_module.Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add_all(
        [
            PromptLog(ai_asset="support", model="model-a", sanitized_prompt="hello", pii_detected={}, created_at=now),
            PromptLog(ai_asset="support", model="model-a", sanitized_prompt="hello", pii_detected={"EMAIL": 1}, created_at=now),
            PromptLog(ai_asset="sales", model="model-b", sanitized_prompt="hello", pii_detected={"PHONE": 2}, created_at=now),
            PromptLog(ai_asset="sales", model="model-b", sanitized_prompt="hello", pii_detected=None, created_at=now),
        ]
    )
    session.commit()

    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    result = dashboard_module.usage_analytics()

    assert result["usage_over_time"][0]["pii_events"] == 3
    assert result["asset_comparison"][0]["pii_events"] == 3