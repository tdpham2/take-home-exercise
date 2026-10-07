# For the April 2026 government-network narrative outage, what failed and how much of the problem did increasing the timeout resolve?

Status: partial

- **C1.** The Argonaut tenant’s government customer network stopped generating narrative updates around April 19, 2026.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — Directly reported for the identified network.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The incident report attributes the failure to narrative jobs exceeding the then-10-hour processing threshold and being killed before completion; the same jobs re-queued into a silent retry loop.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The record explicitly reports both the termination mechanism and retry behavior.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C3.** The processing timeout was increased from 10 to 12 hours, a two-hour increase.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The before-and-after settings are explicit.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours

## Unanswered

- The supplied passages do not quantify how much of the narrative outage the timeout increase resolved or verify that narrative generation recovered.

## Limitations

- A timeout change alone is not evidence of a successful outcome.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
