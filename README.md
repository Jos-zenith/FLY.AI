AI Usage Monitor — VICT.AI Submission

This repository is a build a proof of concept that safely observes real AI activity, sanitizes sensitive information before it is ever stored, and reconciles what an AI agent was declared to do against what it actually did — the same gap that let Samsung employees paste confidential source code into ChatGPT in 2023 with nothing in between to notice.

The primary, evaluated application is ai-usage-monitor/. 
Its own README has the full write-up — architecture and data flow, the PII detection approach and its limits, the no-code/gateway/code-instrumentation capability matrix, assumptions, and known limitations.

The reasoning behind what got built and in what order — grounded in the 2023 Samsung–ChatGPT case,
Three user personas (an engineer who never opens the dashboard, a governance lead who needs evidence not a shrug and a backend engineer who needs an honest capability matrix),
their journey maps, and the Priority–Impact matrix that separated the quick wins from the major projects — is written up separately: https://docs.google.com/document/d/1lkFk6jss1cMlSCq3leTT5JE7hZrrnF6PA4jojcZJqcc/edit?usp=sharing

<img width="1180" height="800" alt="preview" src="https://github.com/user-attachments/assets/027208f1-c67a-46d7-ac91-539fa7a03420" />

The app is PostgreSQL-first by default — ai-usage-monitor/docker-compose.yml starts a local Postgres instance.
If PostgreSQL isn't available, it falls back to local SQLite automatically, so the whole thing still runs with zero external services configured.
