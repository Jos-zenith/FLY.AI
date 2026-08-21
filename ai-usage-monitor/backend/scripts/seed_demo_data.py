"""Seed the running AI Usage Monitor with a realistic demo dataset.

This does NOT insert fake rows directly into the database. It drives the
real HTTP endpoints (/chat and /agent/run) so every row on the dashboard
was produced by the actual monitoring pipeline -- PII detection, prompt
sanitization, and the declared-vs-observed agent tracker all run for
real. That matters for a live demo: what you show an evaluator is the
system actually working, not a fixture.

Usage (with the backend already running, e.g. `uvicorn app.main:app`):

    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --base-url http://127.0.0.1:8000

What it creates:
  - A handful of /chat prompts across different AI assets, some carrying
    realistic PII (email, phone, credit card) so the PII governance
    donut and the Prompts tab have real detections to show.
  - One CLEAN agent run: declared "FAQ DB", and it only touches FAQ DB.
    Shows up in Agent Runs as "Within scope".
  - One SCOPE-BREACH agent run: declared "FAQ DB", but the customer
    message mentions an order, so the agent also queries Orders DB --
    a data source it never declared. Shows up in Agent Runs flagged as
    a scope violation, which is the exact failure mode described in the
    Samsung ChatGPT case study this project is modeled on.
"""

import argparse
import sys
from pathlib import Path

import httpx

# testbed/ lives at the repo root, one level up from backend/ -- add it to
# sys.path so this script can be run directly (`python scripts/seed_demo_data.py`
# from backend/) without needing the repo installed as a package.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testbed.customer_support_demo import SCENARIOS, drive_scenarios  # noqa: E402

CHAT_PROMPTS = [
    {
        "ai_asset": "customer-support",
        "model": "gpt-4",
        "message": "Please reset the account for alice@example.com, she can't log in.",
    },
    {
        "ai_asset": "customer-support",
        "model": "gpt-4",
        "message": "Customer callback requested at 9840123456 regarding ticket TKT-104.",
    },
    {
        "ai_asset": "billing-agent",
        "model": "claude-3",
        "message": "Refund request -- card on file is 4111 1111 1111 1111, please confirm before processing.",
    },
    {
        "ai_asset": "chat",
        "model": "gpt-4",
        "message": "Summarize this quarter's support ticket volume by category.",
    },
    {
        "ai_asset": "customer-support",
        "model": "gpt-4",
        "message": "Following up with bob.customer@example.com about the refund status.",
    },
]

CLEAN_AGENT_RUN = {
    "agent_id": "support-agent-clean",
    "message": "What's in the FAQ about return windows?",
    "query_orders": False,
}

SCOPE_BREACH_AGENT_RUN = {
    "agent_id": "support-agent-breach",
    "message": "Customer is asking about their recent order status, can you check?",
    "ticket_id": "TKT-104",
    "customer_mentions_orders": True,
}


def seed(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        print(f"Seeding demo data against {base_url} ...\n")

        print("-- Sending sample chat prompts --")
        for prompt in CHAT_PROMPTS:
            resp = client.post("/chat", json=prompt)
            resp.raise_for_status()
            data = resp.json()
            pii = data.get("pii_metadata") or {}
            pii_summary = ", ".join(f"{k}:{v}" for k, v in pii.items()) or "none"
            print(f"  [{prompt['ai_asset']}] \"{data['message'][:60]}\" -- PII: {pii_summary}")

        print("\n-- Running a CLEAN agent (declared FAQ DB, touches only FAQ DB) --")
        resp = client.post("/agent/run", json=CLEAN_AGENT_RUN)
        resp.raise_for_status()
        clean = resp.json()
        print(f"  run_id={clean['run_id']} declared={clean['declared']} observed={clean['observed']}")
        print(f"  governance_alert={clean['governance_alert']} (expected: False)")

        print("\n-- Running a SCOPE-BREACH agent (declared FAQ DB, also touches Orders DB) --")
        resp = client.post("/agent/run", json=SCOPE_BREACH_AGENT_RUN)
        resp.raise_for_status()
        breach = resp.json()
        print(f"  run_id={breach['run_id']} declared={breach['declared']} observed={breach['observed']}")
        print(f"  unexpected={breach['unexpected']}")
        print(f"  governance_alert={breach['governance_alert']} (expected: True)")

        # testbed/customer_support_demo.py defines a second, independent
        # set of realistic scenarios (see its module docstring for why
        # this exists as a separate module rather than more inline
        # literals here). Driving them through the same real /chat and
        # /agent/run endpoints exercises that module for real instead of
        # leaving it as an unused scenario generator.
        print(f"\n-- Driving {len(SCENARIOS)} testbed scenarios (testbed/customer_support_demo.py) --")
        testbed_results = drive_scenarios(client, SCENARIOS)
        for scenario, result in zip(SCENARIOS, testbed_results):
            pii = result["chat"].get("pii_metadata") or {}
            pii_summary = ", ".join(f"{k}:{v}" for k, v in pii.items()) or "none"
            agent = result["agent_run"]
            scope = "scope violation" if agent["unexpected"] else "within scope"
            print(f"  [{scenario.asset}] ticket {scenario.ticket_id}: PII={pii_summary}, agent={scope}")

        print("\nDone. Open the dashboard's Agent Runs tab to see both runs, and Overview/Prompts for PII data.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running backend (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    try:
        seed(args.base_url)
    except httpx.ConnectError:
        print(
            f"Could not reach {args.base_url} -- is the backend running?\n"
            "  cd ai-usage-monitor/backend && uvicorn app.main:app --reload --port 8000",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
