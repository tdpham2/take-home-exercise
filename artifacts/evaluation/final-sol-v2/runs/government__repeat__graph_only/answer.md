# Why did the government tenant stop receiving narrative updates in April 2026, and what did the timeout change actually address?

Status: partial

- **C1.** The affected Argonaut government-tenant network stopped generating narrative updates from approximately April 19, 2026.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The incident record explicitly identifies the network and approximate onset.
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.
- **C2.** The incident record attributes the missing updates to narrative-generation jobs repeatedly exceeding the then-10-hour processing SLA and being killed by the application before completion.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — This is the record's explicit root-cause report, not an independently verified diagnosis.
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.
- **C3.** The record says the customer's team discovered the gap first; internal alarms initially missed it and later caught it without action being taken.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The incident record directly reports the detection and response sequence.
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.
- **C4.** The timeout change increased the narrative-processing limit from 10 to 12 hours, addressing application termination of long-running jobs, including those on large-data-volume networks; it is not evidence that job performance improved or that updates resumed.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **medium** — The cited text directly supports the limit change and termination mechanism; its operational scope is synthesis, and no verified recovery or performance result is supplied.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)

## Unanswered

- Whether the 12-hour limit was deployed for the affected network and whether narrative updates subsequently resumed.
- Why the narrative jobs took more than 10 hours, and whether underlying runtime or alert-response problems were fixed.

## Limitations

- The root cause and detection sequence are source reports, not independently verified telemetry.
- Changing the timeout may permit longer jobs to finish but does not itself establish faster processing or recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
