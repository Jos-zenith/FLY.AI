AI Usage Monitor — VICT.AI Submission

My approach started from problem understanding rather than architecture: before writing any FastAPI or React code, I grounded the brief in the 2023 Samsung–ChatGPT incident and built out three personas — an employee who never opens a dashboard, a governance lead who needs evidence rather than a shrug, and a backend engineer who's been burned by "zero code change" claims before. 

Running that through a Priority–Impact matrix made the trade-off explicit and defensible: the highest-leverage 20% wasn't breadth of AI providers supported, it was two things — safe prompt capture that sanitizes before storage, and declared-vs-observed reconciliation for agents — because those two capabilities most directly prevent a Samsung-style leak, and everything else got built or deliberately deferred around that decision.

On engineering and system design, the build follows that priority order end to end. PII detection layers regex with a Luhn checksum for card numbers and an NER fallback for names, and redaction happens before anything is written to disk — the sanitized text is all the database ever sees, while the raw prompt still reaches the model client, which I treat as an honest architectural limitation to document rather than a gap to hide, since that's genuinely how any proxy-based monitoring layer behaves.

Agent runs declare their data sources up front and get diffed against what was actually touched at runtime, so a governance reviewer gets a real record instead of a trust-the-config-file assumption. For accuracy, both flows are covered by an automated test suite that asserts the actual effect (a suppressed capture really doesn't appear in the prompt log; a scope violation really gets flagged), not just that an endpoint returns 200.

The reasoning behind what got built and in what order — grounded in the 2023 Samsung–ChatGPT case, three user personas
An engineer who never opens the dashboard
A governance lead who needs evidence rather than a shrug
A backend engineer 
who needs an honest capability matrix instead of a marketing claim), their journey maps and the Priority–Impact matrix that separated the quick wins from the major projects — is written up separately:
https://docs.google.com/document/d/1lkFk6jss1cMlSCq3leTT5JE7hZrrnF6PA4jojcZJqcc/edit?usp=sharing

<img width="1180" height="800" alt="preview" src="https://github.com/user-attachments/assets/027208f1-c67a-46d7-ac91-539fa7a03420" />

On privacy, security, and edge cases specifically: raw text is never persisted under any code path, including the one endpoint where I found and fixed a bug where sanitized text was being sent to the model instead of raw — which would have quietly broken both the capture guarantee and the privacy narrative if it had shipped; a bare 9-digit run is deliberately not flagged as an SSN to avoid drowning real detections in false positives; and prompt monitoring can be toggled off per AI asset at runtime without a redeploy, which matters because consent and transparency are part of the brief, not just data protection.

Finally, rather than assert full visibility the way most vendors in this space do, I researched and documented an honest capability matrix — what's observable with zero code change, what a gateway adds, and what only in-code instrumentation can see — because the ability to say what a system can't see is, per Alan's persona, the part every vendor pitch leaves out.
