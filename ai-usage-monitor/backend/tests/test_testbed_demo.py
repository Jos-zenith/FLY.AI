import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testbed.customer_support_demo import (
    SCENARIOS,
    CustomerSupportScenario,
    drive_scenarios,
    to_agent_payload,
    to_chat_payload,
)

from app.main import app


def test_payload_builders_match_the_real_endpoint_shapes():
    scenario = CustomerSupportScenario(
        customer_id="CUST-104",
        ticket_id="TKT-104",
        intent="refund request",
        customer_message="My email is alice@example.com, please help with a refund.",
        user_id="user-104",
        mentions_orders=True,
    )

    chat_payload = to_chat_payload(scenario)
    assert chat_payload["message"] == scenario.customer_message
    assert chat_payload["ai_asset"] == scenario.asset

    agent_payload = to_agent_payload(scenario)
    assert agent_payload["query_orders"] is True
    assert agent_payload["ticket_id"] == scenario.ticket_id


def test_testbed_scenarios_drive_the_real_monitoring_pipeline():
    # This is the actual point of this test: SCENARIOS is not just data
    # sitting in a module -- posting it through the real app produces
    # real PII redaction and a real declared-vs-observed governance
    # verdict, the same pipeline the live dashboard reads from.
    client = TestClient(app)

    results = drive_scenarios(client, SCENARIOS)

    assert len(results) == len(SCENARIOS)

    email_scenario_result = results[0]
    assert "alice@example.com" not in email_scenario_result["chat"]["message"]
    assert email_scenario_result["chat"]["pii_metadata"].get("EMAIL") == 1

    orders_scenario_result = results[1]
    assert orders_scenario_result["agent_run"]["unexpected"] == ["Orders DB"]
    assert orders_scenario_result["agent_run"]["governance_alert"] is True

    clean_billing_result = results[2]
    assert clean_billing_result["agent_run"]["unexpected"] == []
    assert clean_billing_result["chat"]["pii_metadata"].get("CREDIT_CARD") == 1
