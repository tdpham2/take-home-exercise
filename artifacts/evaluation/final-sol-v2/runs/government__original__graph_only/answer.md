# Why did the government tenant stop receiving narrative updates in April 2026, and what did the timeout change actually address?

Status: partial

- **C1.** The incident record says one Argonaut government-tenant network stopped generating narrative updates around April 19, 2026; it does not establish a tenant-wide outage.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The record directly identifies one affected network and an approximate start date.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The reported cause was that narrative-generation jobs exceeded the 10-hour processing limit and were killed before completion; re-queued jobs were killed again, producing no output.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The incident record explicitly reports the timeout and retry mechanism.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C3.** The timeout change raised the processing limit from 10 to 12 hours to give long-running narrative jobs more time before application termination; it does not itself demonstrate that updates resumed.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **medium** — The change and targeted failure mechanism are directly reported, but recovery is not verified by these passages.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)

## Unanswered

- Whether and when narrative updates resumed after the timeout increase.
- Why the jobs ran longer than 10 hours.
- Whether alerting or response procedures were changed.

## Limitations

- KEP-6969 is an incident report, not independent verification of deployment or recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
