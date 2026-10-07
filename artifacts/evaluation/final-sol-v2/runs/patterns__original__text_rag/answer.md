# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** Across the records, processing can fail before output is produced, but the cited mechanisms span execution, coordination, data integrity, and collection dependencies rather than one common cause.
  Sources: KEP-3912, KEP-4243, KEP-6923, KEP-6969. Route: `text`.
  Confidence: **medium** — This is a comparison of distinct records, not evidence of a shared root cause.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_8377265b8fad614c` [0:100]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.
- **C2.** For one Argonaut-tenant government customer network, narrative-generation jobs reportedly exceeded a 10-hour processing threshold and were killed before completion.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The record directly names the network and reports the timeout mechanism.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
- **C3.** That job reportedly re-queued after termination, creating a silent retry loop with no output or alert.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The passage directly describes the loop.
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C4.** A separate investigation describes missing SQS notifications leaving tasks in a hanging RUNNING state; it also calls for investigation of comment-narrative Algorithm Errors.
  Sources: KEP-3912. Route: `text`.
  Confidence: **medium** — The investigation text names both symptoms but does not establish that they share a cause.
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
- **C5.** In staging, topic-clustering jobs were reported to fail with an algorithmic error despite completed data collection for active networks.
  Sources: KEP-2189. Route: `text`.
  Confidence: **high** — Both observations are directly reported for the staging work.
  - `ev_ae8831731edc8c8f` [0:64]: Data collection is completed for all active networks in staging.
  - `ev_dcd6b5f9b30344e7` [0:85]: There a re failures in the topic clustering with algorithmic error for 18 jobs out of
- **C6.** Narrative Graph API processing reportedly raised a KeyError when Network Trigrams contained macro_ids absent from Macro Narratives.
  Sources: KEP-4243. Route: `text`.
  Confidence: **high** — The record directly describes the mismatch and exception.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
- **C7.** A report-generation issue produced failures or refusal responses, particularly with Azure models or sensitive-topic prompts; content filtering was suggested, not confirmed, as the mechanism.
  Sources: KEP-6760. Route: `text`.
  Confidence: **medium** — The output behavior is reported directly, while the proposed mechanism is qualified as apparent.
  - `ev_78270a30fb9ad835` [0:176]: report generation fails or returns 'I'm sorry I cannot assist with that request' responses, particularly when using Azure models or specific prompts related to sensitive topics
  - `ev_4722c9e12ee05946` [0:100]: This appears to be related to OpenAI/Azure content filtering and handling of large-scale generation.
- **C8.** For collection, the dependency-risk list names funding or quota exhaustion, rate limits, and vendor or service outages as distinct ways data flow can be interrupted.
  Sources: KEP-6923. Route: `text`.
  Confidence: **high** — These modes are explicitly listed.
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.
  - `ev_a968798c28c0d7d6` [0:16]: Rate‑limit hits.
  - `ev_1dba2fdf457f30b3` [0:45]: Vendor / service outage not detected quickly.
- **C9.** A BrightData batching proposal targets rate limiting by grouping requests; its retry cap and throughput target are requirements, not demonstrated collection outcomes.
  Sources: KEP-7025. Route: `text`.
  Confidence: **medium** — The passages express a goal and requirements, not measured results.
  - `ev_e5585e8d13c80e28` [0:113]: The goal is to reduce rate limiting issues and improve data collection efficiency by grouping requests in batches
  - `ev_9337c1379bb2a44f` [0:64]: Backoff logic should not exceed 3 retries within a 24-hour cycle
  - `ev_a7c43f25cd6ac0ad` [0:61]: Should maintain processing speed of at least 5,000 users/hour
- **C10.** The pipeline-risk list also distinguishes upstream model crashes, partial network-level failures, release-related narrative-accumulation regressions, and report-generation failures.
  Sources: KEP-6923. Route: `text`.
  Confidence: **high** — The source explicitly lists these as different pipeline failure modes.
  - `ev_db0c75ab2fb11e09` [0:54]: Pipeline model crashes → everything downstream breaks.
  - `ev_3d078a483bf0ab14` [0:57]: Partial network‑level failures (NE, NH, Influence, etc.).
  - `ev_82fb7c9fc0071447` [0:65]: Release‑related regressions (e.g., narrative‑accumulation issue).
  - `ev_1ac3a7fb42bdf536` [0:47]: Report‑generation failures (no regular QA run).
- **C11.** Missing service callbacks are separately flagged as a Weibo processing failure, resembling the missing-notification symptom but not establishing the same underlying mechanism.
  Sources: KEP-3912, KEP-6650. Route: `text`.
  Confidence: **medium** — Both passages concern missing completion signals, but the Weibo evidence is only a title.
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
  - `ev_8377265b8fad614c` [0:100]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state

## Unanswered

- Whether the proposed missing-macro_id handling, BrightData batching, or notification and callback fixes were deployed and effective.
- How frequently each failure mode occurred across tenants or environments beyond the cited cases and risk list.
- The root cause of the staging algorithmic errors and whether the Weibo callback issue involved SQS.

## Limitations

- The passages mix incident reports, investigation requests, a risk catalogue, and implementation requirements; they are not a uniform incident sample.
- The staging topic-clustering count is truncated, and no failure rate can be inferred.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
