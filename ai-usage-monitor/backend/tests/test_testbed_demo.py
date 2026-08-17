import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testbed.customer_support_demo import CustomerSupportScenario, generate_customer_support_activity


def test_testbed_demo_generates_realistic_customer_support_activity():
    scenario = CustomerSupportScenario(
        customer_id="CUST-104",
        ticket_id="TKT-104",
        intent="refund request",
        customer_message="I need help with a refund for order 104 and my email is alice@example.com.",
        user_id="user-104",
    )

    activity = generate_customer_support_activity(scenario)

    assert activity["provider"] == "anthropic"
    assert activity["model"] == "claude-3.5-sonnet"
    assert "alice@example.com" not in activity["prompt_text"]
    assert activity["tool_calls"][0]["tool_name"] == "faq_lookup"
    assert activity["data_sources_accessed"] == ["faq_db", "orders_db"]
    assert activity["agent_execution"]["status"] == "completed"
    assert activity["token_usage"]["input_tokens"] > 0
