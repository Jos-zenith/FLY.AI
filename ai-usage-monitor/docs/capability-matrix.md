# Capability Matrix

| Capability | Status | Notes |
| --- | --- | --- |
| AI chat endpoint | Planned | Accepts user requests and sanitizes input |
| PII detection | Implemented | Pattern-based detection for emails, phones, SSNs |
| Agent run tracking | Implemented | Compares declared tool use with observed execution |
| Dashboard summary | Planned | Aggregates counts by app, site, and agent |
| Postgres persistence | Planned | SQLAlchemy models ready for relational storage |
| OTel observability | Planned | Hook points included in observability package |
| Fake support app | Implemented | Simulated customer support scenarios |

## Planned extensions

- Add role-based access control
- Add trace propagation with OpenTelemetry
- Add per-user consent and masking preferences
- Add anomaly detection for tool sprawl or over-usage
