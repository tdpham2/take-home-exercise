# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** A reported narrative-generation failure repeatedly killed jobs after a 10-hour timeout and re-queued them without output or an alert.
  Sources: KEP-6969. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The incident passages directly report the timeout and retry loop.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C2.** A collection outage was attributed instead to video-vision jobs failing to close final steps, backing up the queue and preventing new jobs from starting.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — This is the source-reported cause, not independently verified recovery.
  - `ev_9488fa8cc6db3d39` [0:168]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting.
- **C3.** A separate narrative report described micro- and macro-narrative UI data appearing hours late; it reported success with 4–7 staging networks but failure with roughly 200 or more production networks.
  Sources: KEP-6189. Route: `memory`.
  Confidence: **medium** — The reports establish lateness and an environment contrast, but not that scale caused the delay.
  - `ev_78b67c045ef5dda3` [0:59]: UI data for micro‑ and macro‑narratives appears hours late.
  - `ev_0aa92eb7859f3f5e` [0:91]: The pipeline works fine in staging (4‑7 networks) but fails in production (~200+ networks).
- **C4.** Collection can fail at initiation: a Weibo report says network creation succeeded without date validation, but collection was not triggered for any source in that network.
  Sources: KEP-6777. Route: `graph`.
  Confidence: **high** — The passage directly reports setup success and absent collection triggering.
  - `ev_ab3e2ef2efebc39d` [0:131]: Network gets created successfully without date validation for Weibo. No data collection is triggered for any sources in the network
- **C5.** A report describes severely degraded or failing Facebook, Instagram, and TikTok collection over an approximate interval, with no automated alarm firing during that period.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The passages support degraded collection and missed detection, but not a platform-specific cause or completed recovery.
  - `ev_75b67275157f9120` [0:137]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing.
  - `ev_06eee086b8cf9d93` [0:43]: No automated alarm fired during this period
- **C6.** Missing downstream narrative data had another reported mechanism: Network Trigrams held macro_ids absent from the Macro Narratives collection.
  Sources: KEP-4243. Route: `graph`.
  Confidence: **high** — The passage directly states the cross-collection mismatch, without explaining why it arose.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection

## Unanswered

- The narrative-statistics claim was omitted because its proposed source citation was not shown and could not be validated from the available evidence.
- The selected reports do not establish how prevalent these modes are or whether they share a root cause.
- The cited collection passage does not verify completed backfill or end-to-end recovery.

## Limitations

- These are selected source reports; repeated passages from one incident are not independent incidents.
- Reported causes and fixes are not independently verified outcomes. Staging and production behavior remain distinct.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
