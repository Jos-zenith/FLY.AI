# Synthetic customer-support testbed

This directory defines realistic customer-support scenarios and drives them through the **real** running monitor — `POST /chat` and `POST /agent/run` — rather than pre-computing what the pipeline should output. `backend/scripts/seed_demo_data.py` imports `SCENARIOS` from here and calls `drive_scenarios(...)` as part of the standard seeding flow, so running the seed script exercises this module every time; it isn't a separate, disconnected demo path.

It intentionally models:
- a customer-support agent handling a refund, an order-status check, and a billing question
- real PII in the raw customer message (email, phone, card number) — redaction happens inside the real `/chat` endpoint, not here, so what ends up on the dashboard is genuinely what the pipeline detected
- one scenario that mentions an order, which makes the agent reach into Orders DB — a source it never declares — to show a real scope-violation verdict from `app/services/agent_tracker.py`, not a scripted one
- token/latency metadata that comes back from the real endpoint response, not a hand-authored fixture

See `customer_support_demo.py`'s module docstring for why it's built this way: an earlier version generated a scenario dict with its own hand-rolled redaction and a pre-computed governance verdict that nothing ever fed into the actual monitor — realistic-looking, but disconnected from the system it was meant to test. `backend/tests/test_testbed_demo.py` asserts against the real pipeline's output (via FastAPI's `TestClient`) to keep it that way.
