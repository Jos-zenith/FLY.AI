# Capability Matrix

| Capability | Status | Notes |
| --- | --- | --- |
| AI chat endpoint | Planned | Accepts user requests and sanitizes input |
| PII detection | Implemented | Pattern-based detection for emails, phones, SSNs |
| Agent run tracking | Implemented | Compares declared tool use with observed execution |
| Dashboard summary | Planned | Aggregates counts by app, site, and agent |
| Postgres persistence | Planned | SQLAlchemy models ready for relational storage |
| OTel observability | Implemented | External FastAPI/HTTPX instrumentation produced HTTP spans, request metadata, timing, and upstream client spans, but not raw prompt text or internal agent decisions |
| Fake support app | Implemented | Simulated customer support scenarios |

## Research findings

| Layer | What was visible | What stayed hidden |
| --- | --- | --- |
| Auto-instrumented app (no app code changes) | Incoming HTTP server spans, outgoing HTTP client spans, request route/method/status, timing, host/url metadata | Raw prompt content, prompt redaction details, internal tool logic, DB access, governance decisions |
| Reverse-proxy / gateway | Full upstream request body, full upstream response body, model, latency, token counts, sanitized prompt, PII counts | Internal agent reasoning, independent DB queries the agent makes outside the gateway, downstream business decisions unless explicitly logged |
| Explicit code instrumentation | Tool call names, tool arguments, declared vs observed sources, DB access events, run start/end/status, governance alert on mismatches | Anything executed inside unwrapped libraries or external calls that bypass the logging wrappers |

## Planned extensions

- Add role-based access control
- Add per-user consent and masking preferences
- Add anomaly detection for tool sprawl or over-usage
