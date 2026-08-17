from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CustomerSupportScenario:
    customer_id: str
    ticket_id: str
    intent: str
    customer_message: str
    user_id: str
    asset: str = "customer-support"


@dataclass
class MockToolCall:
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


def _redact_email(value: str) -> str:
    return "[REDACTED_EMAIL]"


def generate_customer_support_activity(scenario: CustomerSupportScenario) -> dict[str, Any]:
    prompt = (
        f"Customer {scenario.customer_id} says: '{scenario.intent}' for ticket {scenario.ticket_id}. "
        "Provide support guidance and confirm whether applicable policy allows a refund."
    )

    faq_tool = MockToolCall(
        tool_name="faq_lookup",
        arguments={"query": scenario.intent},
        result={"matches": ["refund policy", "return window"], "source": "faq_db"},
    )
    orders_tool = MockToolCall(
        tool_name="orders_lookup",
        arguments={"ticket_id": scenario.ticket_id, "customer_id": scenario.customer_id},
        result={"order_status": "shipped", "refund_eligible": True, "source": "orders_db"},
    )

    prompt_text = prompt.replace(scenario.customer_id, "[customer-id]")
    prompt_text = prompt_text.replace(scenario.ticket_id, "[ticket-id]")
    prompt_text = prompt_text.replace("alice@example.com", _redact_email("alice@example.com"))

    return {
        "provider": "anthropic",
        "model": "claude-3.5-sonnet",
        "asset": scenario.asset,
        "user_id": scenario.user_id,
        "prompt_text": prompt_text,
        "tool_calls": [
            {
                "tool_name": faq_tool.tool_name,
                "arguments": faq_tool.arguments,
                "result": faq_tool.result,
            },
            {
                "tool_name": orders_tool.tool_name,
                "arguments": orders_tool.arguments,
                "result": orders_tool.result,
            },
        ],
        "data_sources_accessed": ["faq_db", "orders_db"],
        "agent_execution": {
            "agent_id": "customer-support",
            "declared_sources": ["faq_db"],
            "observed_sources": ["faq_db", "orders_db"],
            "status": "completed",
            "governance_alert": True,
        },
        "token_usage": {
            "input_tokens": 128,
            "output_tokens": 72,
            "total_tokens": 200,
        },
        "request_metadata": {
            "latency_ms": 1420,
            "status_code": 200,
        },
    }
