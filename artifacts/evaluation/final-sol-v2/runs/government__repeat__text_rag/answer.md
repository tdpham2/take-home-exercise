# Why did the government tenant stop receiving narrative updates in April 2026, and what did the timeout change actually address?

Status: partial

- **C1.** The Argonaut government tenant’s cited network stopped generating narrative updates around April 19, 2026.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The incident report directly identifies the tenant, network, and approximate onset.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The reported cause was that this network’s narrative-generation jobs repeatedly exceeded the then-10-hour processing threshold and were killed before completion.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The incident report explicitly states this mechanism as its root cause.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C3.** The report says killed jobs re-queued and were killed again, producing a silent loop without output or an alert.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The cited passage directly describes the retry behavior.
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C4.** The reported timeout change raised the processing limit from 10 to 12 hours, addressing termination at the 10-hour threshold rather than establishing that jobs became faster or that narrative updates resumed.
  Sources: KEP-6969. Route: `text`.
  Confidence: **medium** — The change and prior failure threshold are explicit; its limited scope follows from comparing them.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing

## Unanswered

- Why did this network’s narrative-generation jobs take longer than 10 hours?
- Did the 12-hour threshold allow jobs to finish and narrative updates to resume, and when?

## Limitations

- The separate April data-collection incident in KEP-6970 is not evidence that it caused this Argonaut network’s narrative-generation failure.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
