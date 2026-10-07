# Why did the government tenant stop receiving narrative updates in April 2026, and what did the timeout change actually address?

Status: partial

- **C1.** At least one network in the government customer’s Argonaut tenant stopped receiving narrative updates around April 19, 2026.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The incident passage directly identifies the tenant, network, and approximate onset.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C2.** The incident record attributes the stoppage to narrative jobs exceeding the then-10-hour processing threshold and being killed before completion.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The incident record explicitly states this cause.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C3.** The killed job re-queued and was killed again, producing a silent retry loop without output or an alert.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The retry behavior is stated directly.
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C4.** The reported change raised the narrative processing timeout from 10 to 12 hours, addressing the cutoff that killed long-running jobs—not demonstrating that jobs became faster or that updates resumed.
  Sources: KEP-6969. Route: `text`.
  Confidence: **medium** — The change and prior cutoff are explicit; its scope and lack of a verified outcome are inferred from what the supplied passages establish.
  - `ev_ad26bffaa983949e` [0:62]: the processing timeout was increased from 10 hours to 12 hours
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing

## Unanswered

- Did the affected network resume narrative updates after the timeout increase?
- Why were its narrative jobs taking more than 10 hours, and could they also exceed 12 hours?

## Limitations

- The separate April 21–29 data-collection incident in KEP-6970 is not established as the cause of this Argonaut narrative stoppage.
- The incident text also says later alarms caught the issue without action; the supplied passages do not establish a precise alert timeline.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
