# Synthetic customer-support testbed

This directory provides a lightweight, realistic customer-support scenario that exercises the monitor without requiring a full external application.

It intentionally models:
- a customer support agent using a FAQ lookup and an orders lookup
- a redacted prompt that still demonstrates PII masking
- declared vs observed data sources to show governance alerting
- token, latency, and provider metadata close to real LLM activity

The generated scenario is designed to be realistic enough for demos and regression tests while remaining lightweight enough for a local repo.
