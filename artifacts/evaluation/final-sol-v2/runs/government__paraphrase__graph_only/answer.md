# For the April 2026 government-network narrative outage, what failed and how much of the problem did increasing the timeout resolve?

Status: partial

- **C1.** A government customer network in the Argonaut tenant stopped receiving narrative updates from approximately April 19, 2026.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The incident record states the affected tenant, failure, and approximate start date directly.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The reported failure was that narrative-generation jobs exceeded the 10-hour processing threshold and the application killed them before completion; retries then produced no output.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The incident record explicitly describes the job termination and retry loop.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C3.** The processing timeout was increased from 10 to 12 hours.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The source explicitly reports the timeout change, but not its measured outcome.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours

## Unanswered

- How much the timeout increase resolved the outage is not established by the retrieved original passages; they provide no measured recovery, completion rate, or confirmation that narrative updates resumed.

## Limitations

- Do not treat the timeout change itself as proof of recovery or infer a percentage of the problem resolved.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
