AI Usage Monitor — VICT.AI Submission

Organizations approve which AI tools and agents are allowed to run, but that approval says nothing about what actually happens after: whether an employee pastes a customer's phone number into a prompt, whether an agent quietly reaches a database nobody declared for it, or whether "the AI system" is even doing what it was registered to do. That blind spot is exactly what let Samsung engineers paste confidential source code into ChatGPT in 2023 — not malice, just an organization with no visibility layer between "employee has a task" and "employee pastes data into a prompt box."

This repository is a proof of concept for that problem: safely observe real AI activity, sanitize sensitive information before it is ever stored, and reconcile what an AI agent was declared to do against what it actually did.

The primary, evaluated application is ai-usage-monitor/. Its own README has the full write-up — architecture and data flow, the PII detection approach and its limits, the no-code / gateway / code-instrumentation capability matrix, assumptions, and known limitations.

The reasoning behind what got built and in what order — grounded in the 2023 Samsung–ChatGPT case, three user personas (an engineer who never opens the dashboard, a governance lead who needs evidence rather than a shrug, and a backend engineer who needs an honest capability matrix instead of a marketing claim), their journey maps, and the Priority–Impact matrix that separated the quick wins from the major projects — is written up separately:
https://docs.google.com/document/d/1lkFk6jss1cMlSCq3leTT5JE7hZrrnF6PA4jojcZJqcc/edit?usp=sharing

<img width="1180" height="800" alt="preview" src="https://github.com/user-attachments/assets/027208f1-c67a-46d7-ac91-539fa7a03420" />

What this system actually does

Everything in ai-usage-monitor/ supports four flows. The first two are the two pillars the brief asks for directly; the other two are what make the first two trustworthy rather than just claimed.

1. Safe prompt capture — sanitize before it's ever stored. A prompt comes in through POST /chat (or the /gateway/v1/messages path, which represents traffic already flowing through an existing AI application). A regex + Luhn-checked + NER-assisted detector finds PII spans — email, phone, card numbers, SSNs, IDs, names — before anything touches disk. The database only ever receives the redacted text plus structured counts ({"EMAIL": 1, "PHONE": 1}); the raw prompt is never persisted. The raw, unredacted text still reaches the underlying model client, exactly as it would reach a real LLM provider — that gap between "hidden from your own records" and "hidden from the AI provider" is deliberate, and is the specific risk this project exists to make visible rather than paper over.

2. Agent governance — declared vs. observed, not declared vs. assumed. An agent run declares its data sources up front (e.g. "FAQ Database only"). During execution, every tool call and data-source access is recorded independently of that declaration. When the run finishes, the two lists are diffed: sources touched but never declared are flagged as a scope violation, right down to which run and which source. A governance lead reviewing this doesn't have to trust a config file — they get a record of what actually happened.

3. AI asset registry & per-asset monitoring toggle. Every AI tool the system has ever seen — chat, customer-support, billing-agent, or anything new — is tracked as a registered asset with a declared purpose, declared data sources, and a monitoring on/off flag that can be flipped at runtime, no redeploy required. This exists in two places for two different people: a governance-lead-facing registry table in the dashboard, and a lightweight "Monitored / Not monitored" switch right on the chat screen itself — because the employee actually sending prompts never opens the dashboard, so the control that matters to them has to live where they are.

4. Honest observability research — what can actually be seen, and how. Rather than assert "full visibility," the project instruments real OpenTelemetry spans (FastAPI + HTTPX auto-instrumentation, plus custom gateway spans) and documents, capability by capability, what a no-code approach can see, what a gateway adds, and what only in-code instrumentation can capture — including where each approach fails. See ai-usage-monitor/docs/capability-matrix.md for the full comparison and ai-usage-monitor/docs/architecture.excalidraw for the data-flow diagram behind all four flows above.
