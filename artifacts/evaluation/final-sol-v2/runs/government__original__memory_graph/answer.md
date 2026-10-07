# Why did the government tenant stop receiving narrative updates in April 2026, and what did the timeout change actually address?

Status: partial

- **C1.** The affected Argonaut government-customer network stopped generating narrative updates from approximately April 19, 2026.
  Sources: KEP-6969. Route: `memory`.
  Confidence: **high** — The incident text states the affected network and approximate start date directly.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The reported cause was that narrative-generation jobs exceeded the then-10-hour processing timeout and were killed before completion; the same jobs re-queued and were killed again, yielding no output.
  Sources: KEP-6969. Route: `memory`.
  Confidence: **high** — Both the reported cause and retry behavior are explicit in the original incident excerpts.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C3.** Detection and response compounded the lapse: the customer found it before internal alarms did, and later alarms reportedly prompted no action.
  Sources: KEP-6969. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The incident excerpt directly describes customer discovery and subsequent inaction.
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.
- **C4.** The timeout change increased the processing limit from 10 to 12 hours, addressing premature termination of long-running narrative jobs rather than the separate alerting-and-response failure.
  Sources: KEP-6969. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The threshold increase and job-termination mechanism are direct; the contrast with alerting is a bounded synthesis, not a verified remediation outcome.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.

## Unanswered

- The available excerpts do not establish that the 12-hour limit restored updates, improved job runtime, or fixed alert ownership and response.

## Limitations

- The incident's reported root cause is source testimony, not independent performance analysis; an approximate April 19 start is not a confirmed recovery timestamp.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
