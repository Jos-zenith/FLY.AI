# Capability Matrix

This project is best understood as a small observability testbed for AI usage monitoring rather than a complete application platform. The matrix below explains what can be seen from each observation point.

## What each layer can observe

| Observation layer | Provider / model | Prompt / message content | Token usage | Tool calls | Agent execution | Data-source access | What is not visible |
| --- | --- | --- | --- | --- | --- | --- | --- |
| No application changes | Usually only the transport layer: HTTP method, route, timing, upstream/downstream endpoints, and optional service metadata. No reliable proof of provider identity or model unless the app itself emits it. | Not visible in normal server traces. The actual user prompt is not present unless the app logs it explicitly. | Not reliably visible without application-level instrumentation or gateway metadata. | No. The app can appear as a black box. | No. A server trace cannot tell which sub-agent or tool executed. | No. DB access remains opaque unless the app emits events. | Internal reasoning, business logic, hidden tool execution, user-specific downstream actions |
| Gateway / reverse proxy | Yes, if the gateway has access to the upstream request and can inspect the request body; provider/model can often be inferred from fields like `model`, `provider`, and URL. | Partly visible: the gateway can see the full request payload and the upstream response, but should redact before storage. | Yes, when the upstream response includes usage metadata. | Only at the gateway boundary: outbound LLM call and maybe a route to a backend service. Not necessarily internal tool calls. | Not usually. A gateway sees the LLM request but not the internal agent workflow unless the app emits it. | Only if the gateway is also proxying DB or backend requests; otherwise no. | Internal tool graph, hidden DB queries, internal decision records, non-proxied sources |
| Application instrumentation | Yes, if the app sets metadata on spans or logs. | Yes, if the app intentionally captures sanitized prompts or redacted text. | Yes, when the app records upstream token counts or estimates. | Yes, if the code wraps tool calls and records names/arguments. | Yes, if the app records run start/end, declared sources, tool sequence, and status. | Yes, if the app logs wrapper calls around DB or service access. | Anything outside the instrumented wrappers, plus any raw payloads the app intentionally chooses not to record |
| Explicit agent tracking layer | Yes, this project records provider/model at gateway level and agent identity at run level. | Sanitized prompt text may be stored, but raw PII is not stored in the prompt log. | Yes, the app captures input/output tokens and latency. | Yes, tool names and arguments are recorded. | Yes, the project tracks declared vs observed sources and agent run lifecycle. | Yes, it records source access events from the explicit wrappers. | Non-wrapped third-party calls, unlogged calls outside the wrappers, hidden model internals beyond the chosen fields |

## Practical interpretation

### 1) No application changes
This produces the least insight. A standard HTTP trace can show only what the framework can see: request path, method, timing, payload size, and external HTTP calls. It cannot reliably prove which model was used, which tools were invoked, or whether a specific database was accessed.

### 2) Gateway visibility
A gateway helps substantially because it sits at the boundary between the application and the LLM provider. It can usually see:
- provider/model information from the request
- prompt payloads and upstream responses
- token usage from the LLM response
- latency and status

It still cannot see: 
- inner tool calls inside the application
- database accesses that happen outside the gateway
- application-level governance logic or agent reasoning

### 3) Application instrumentation
This is the first layer that can connect LLM traffic to business activity. By adding instrumentation around the agent lifecycle, tool wrappers, and database access, you can observe:
- tool names, arguments, and results
- declared vs observed sources
- status transitions and completion signals
- PII detection and redaction decisions

### 4) Why the project is intentionally limited
This repository is a small observability testbed, not a production customer-support system. The code intentionally records the exact things a realistic monitoring setup can observe without inventing full, opaque production internals.

The project does not claim to see:
- hidden internal reasoning traces from the model
- the model's private reasoning chain
- every unwrapped library or external service call
- full end-to-end business activity outside the explicit wrappers

### 5) Privacy and upstream exposure boundary
The app is designed to avoid storing raw prompt content locally, and it redacts prompt logs and tool arguments before persistence. However, the gateway still forwards the original user prompt to the configured upstream AI provider. That means the correct boundary is:
- local storage: redacted and limited
- upstream provider: still receives the original request content because the gateway is a proxy

This is an explicit monitoring limitation, not a privacy guarantee.

### 6) Demo access-control boundary
The default local/demo configuration does not enforce access control by default, which makes the sample easy to run and inspect in a development environment. A simple API-key or bearer-token guard can be enabled, but this is still only a demo safeguard and not a production authorization model. A real privacy-sensitive deployment would need authenticated users, RBAC, admin-only dashboards, and stronger secrets management.

### 7) Gateway safety boundary
The gateway is intentionally lightweight and is not production-safe. It forwards incoming request headers to the upstream provider unless explicitly filtered, and it does not implement rate limiting, abuse protection, request quotas, or robust validation of unexpected upstream responses. Database sessions are kept simple for the demo and should be explicitly closed in all production paths, rather than relying on the current lightweight pattern.

### 8) PII detection reliability statement
The project supports explicit, rule-based detection for common PII patterns such as emails and phone numbers. It does not guarantee dependable name detection across arbitrary real-world text. Known behavior includes false negatives for weakly contextual names such as “Ramesh” and false positives for capitalized words or organization names. The final documentation should be read as a best-effort detection layer, not a production identity-classification system.

## Current implementation status

| Capability | Status | Reality |
| --- | --- | --- |
| Gateway tracing | Implemented | Real FastAPI route + HTTPX request tracing with LLM metadata in the custom span |
| Prompt capture | Implemented | Sanitized prompt storage with PII counts and retention logic |
| PII detection and redaction | Implemented | Regex and optional model-based fallback; raw text is not persisted |
| Agent source tracking | Implemented | Declared vs observed sources and tool call recording |
| Dashboard views | Implemented | Summary and prompt list endpoints are present |
| Synthetic customer-support demo | Implemented | Lightweight, realistic scenario that exercises the monitor without a full external app |
| Full production-grade observability stack | Not claimed | This is intentionally a minimal demonstration environment |

## Planned extensions

- Add a stronger mock application flow with a realistic support ticket lifecycle
- Add richer tool and database wrappers for more complete agent tracing
- Add a user-level dashboard and policy rules for suppression/alerting
- Add more realistic multimodal and async agent activity samples
