"""Synthetic customer-support scenarios, wired into the real monitor.

This module used to generate a plain scenario dict -- provider, model,
tool_calls, a hand-rolled `_redact_email` helper -- and nothing ever fed
it anywhere. That was dead code: it duplicated what
`app/services/pii.py` and `app/services/agent_tracker.py` already do for
real, and no script or test drove it through the actual monitoring
pipeline. `backend/scripts/seed_demo_data.py` was doing the real
demo-data work with its own separate, hand-written prompt list.

This version does one job: define realistic customer-support scenarios
as data, and turn each into the exact request bodies `/chat` and
`/agent/run` expect. It intentionally does NOT pre-redact PII or
pre-compute a governance verdict -- that would just be re-implementing
`app/services/pii.py` and `app/services/agent_tracker.py` badly. Posting
these payloads to the real endpoints (via `drive_scenarios`, or from
`backend/scripts/seed_demo_data.py`, which now imports SCENARIOS from
here) means the PII detected and the scope-violation verdict shown on
the dashboard were actually computed by the real pipeline, not scripted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CustomerSupportScenario:
    customer_id: str
    ticket_id: str
    intent: str
    customer_message: str
    user_id: str
    asset: str = "customer-support"
    model: str = "gpt-4"
    # Whether this scenario's agent run should reach into Orders DB, a
    # source it never declares -- the scope-violation case. False means
    # the agent stays within its declared FAQ DB scope.
    mentions_orders: bool = False


SCENARIOS: list[CustomerSupportScenario] = [
    CustomerSupportScenario(
        customer_id="CUST-104",
        ticket_id="TKT-104",
        intent="refund request",
        customer_message="I need help with a refund for my order, my email is alice@example.com.",
        user_id="user-104",
        mentions_orders=False,
    ),
    CustomerSupportScenario(
        customer_id="CUST-118",
        ticket_id="TKT-118",
        intent="order status",
        customer_message="Can you check the status of my order? Call me back at 9840123456 if you need anything.",
        user_id="user-118",
        mentions_orders=True,
    ),
    CustomerSupportScenario(
        customer_id="CUST-131",
        ticket_id="TKT-131",
        intent="billing question",
        customer_message="Why was my card 4111 1111 1111 1111 charged twice this month?",
        user_id="user-131",
        asset="billing-agent",
        model="claude-3",
        mentions_orders=False,
    ),
]


def to_chat_payload(scenario: CustomerSupportScenario) -> dict[str, Any]:
    """Build the exact body `POST /chat` expects for this scenario.

    The raw message (with real PII in it) is sent as-is -- redaction
    happens inside the real endpoint, not here. Pre-redacting this dict
    would mean the demo shows sanitizer output that was never actually
    produced by the sanitizer.
    """
    return {
        "message": scenario.customer_message,
        "ai_asset": scenario.asset,
        "model": scenario.model,
        "user_id": scenario.user_id,
        "session_id": scenario.ticket_id,
    }


def to_agent_payload(scenario: CustomerSupportScenario) -> dict[str, Any]:
    """Build the exact body `POST /agent/run` expects for this scenario."""
    return {
        "agent_id": f"{scenario.asset}-agent",
        "message": scenario.customer_message,
        "ticket_id": scenario.ticket_id,
        "query_orders": scenario.mentions_orders,
    }


def drive_scenarios(client, scenarios: list[CustomerSupportScenario] | None = None) -> list[dict[str, Any]]:
    """Post every scenario through the real /chat and /agent/run endpoints.

    `client` is any object with a `.post(path, json=...)` method that
    returns a response with `.raise_for_status()` and `.json()` -- an
    `httpx.Client` in real use (see seed_demo_data.py), or FastAPI's
    `TestClient` in tests. Returns one result dict per scenario with both
    responses, so a caller (or a test) can assert on what the real
    pipeline actually did with each one.
    """
    results = []
    for scenario in scenarios or SCENARIOS:
        chat_resp = client.post("/chat", json=to_chat_payload(scenario))
        chat_resp.raise_for_status()

        agent_resp = client.post("/agent/run", json=to_agent_payload(scenario))
        agent_resp.raise_for_status()

        results.append(
            {
                "scenario": scenario,
                "chat": chat_resp.json(),
                "agent_run": agent_resp.json(),
            }
        )
    return results
