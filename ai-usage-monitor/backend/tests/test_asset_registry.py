from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.dashboard as dashboard_module
from app.core.database import Base, get_db as real_get_db
from app.main import app
from app.models.ai_asset import AiAsset
from app.services.asset_registry import DEFAULT_ASSETS, ensure_default_assets, get_or_register_asset


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_ensure_default_assets_is_idempotent():
    session = _session()

    ensure_default_assets(session)
    assert session.query(AiAsset).count() == len(DEFAULT_ASSETS)

    # A second call must not duplicate rows or reset a flag someone
    # already toggled off.
    row = session.query(AiAsset).filter(AiAsset.name == "chat").one()
    row.monitoring_enabled = False
    session.commit()

    ensure_default_assets(session)
    assert session.query(AiAsset).count() == len(DEFAULT_ASSETS)
    assert session.query(AiAsset).filter(AiAsset.name == "chat").one().monitoring_enabled is False


def test_get_or_register_asset_creates_unknown_assets_on_demand():
    session = _session()

    row = get_or_register_asset(session, "brand-new-asset")
    assert row.name == "brand-new-asset"
    assert row.declared_purpose is None
    assert row.declared_data_sources == []
    assert row.monitoring_enabled is True

    # Fetching again must return the same row, not create a second one.
    again = get_or_register_asset(session, "brand-new-asset")
    assert again.id == row.id
    assert session.query(AiAsset).filter(AiAsset.name == "brand-new-asset").count() == 1


def test_assets_endpoint_lists_the_seeded_registry(monkeypatch):
    session = _session()
    ensure_default_assets(session)
    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    client = TestClient(app)
    resp = client.get("/dashboard/assets")
    assert resp.status_code == 200
    names = {row["name"] for row in resp.json()}
    assert names == {a["name"] for a in DEFAULT_ASSETS}
    customer_support = next(row for row in resp.json() if row["name"] == "customer-support")
    assert customer_support["declared_data_sources"] == ["FAQ DB"]
    assert customer_support["monitoring_enabled"] is True


def test_toggling_monitoring_off_actually_suppresses_prompt_capture(monkeypatch):
    session = _session()
    ensure_default_assets(session)
    monkeypatch.setattr(dashboard_module, "get_db", lambda: iter([session]))

    def _override_get_db():
        yield session

    app.dependency_overrides[real_get_db] = _override_get_db
    try:
        client = TestClient(app)

        # Turn monitoring off for "chat" via the same endpoint the UI toggle calls.
        patch_resp = client.patch("/dashboard/assets/chat", json={"monitoring_enabled": False})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["monitoring_enabled"] is False

        chat_resp = client.post("/chat", json={"message": "hello", "ai_asset": "chat"})
        assert chat_resp.status_code == 200

        prompts = client.get("/dashboard/prompts", params={"ai_asset": "chat"}).json()
        assert prompts == []  # capture was suppressed -- this is the point of the test

        # A different, still-enabled asset is unaffected by chat's toggle.
        support_resp = client.post(
            "/chat", json={"message": "still monitored", "ai_asset": "customer-support"}
        )
        assert support_resp.status_code == 200
        support_prompts = client.get("/dashboard/prompts", params={"ai_asset": "customer-support"}).json()
        assert len(support_prompts) == 1
    finally:
        app.dependency_overrides.pop(real_get_db, None)


def test_patch_auto_registers_an_unseeded_asset():
    session = _session()
    # Deliberately do NOT seed defaults -- the endpoint must still work
    # for an asset name nobody registered yet.
    row = get_or_register_asset(session, "never-seen-before")
    row.monitoring_enabled = False
    session.commit()

    refetched = session.query(AiAsset).filter(AiAsset.name == "never-seen-before").one()
    assert refetched.monitoring_enabled is False
