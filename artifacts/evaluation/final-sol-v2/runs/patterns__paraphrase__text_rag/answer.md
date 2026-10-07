# Across narrative and collection processing, what reported failure mechanisms recur, and which differences prevent treating them as one cause?

Status: partial

- **C1.** Narrative Graph backend processing reportedly raised a KeyError when macro_ids existed in Network Trigrams but were missing from Macro Narratives.
  Sources: KEP-4243. Route: `text`.
  Confidence: **high** — The record directly describes the mismatch and exception.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
- **C2.** A separate narrative-level stance query reportedly returned zero comments despite 817 comments being indicated at the post level.
  Sources: KEP-6509. Route: `text`.
  Confidence: **high** — The conflicting counts are directly reported.
  - `ev_4d8d331637786fe8` [0:157]: the agent returns 0 comments across all stance categories (Support, Oppose, Neutral), despite the system indicating that 817 comments exist at the post level
- **C3.** Statistics API documentation flags inconsistent data across endpoints and proposes a single-source-of-truth refactor; it does not establish the same missing-record KeyError mechanism.
  Sources: KEP-4182. Route: `text`.
  Confidence: **medium** — The inconsistency and proposed refactor are explicit, but their relation to other failures is limited.
  - `ev_5646d4217047176d` [0:34]: Inconsistent data across endpoints
  - `ev_2c939eb047fbbdc5` [0:67]: Refactor statistics APIs to follow a single source of truth pattern
- **C4.** An enrichment task failure is attributed in its ticket text to a last-narrative-date issue.
  Sources: KEP-5586. Route: `text`.
  Confidence: **medium** — The attribution is explicit but appears in an investigation request without diagnostic detail.
  - `ev_d4b3ecd34ac362d9` [0:91]: Investigate and resolve the enrichment task failure caused by the last narrative date issue
- **C5.** Collection processing reportedly sent duplicate post IDs when one post appeared under a username, hashtag, and cashtag, causing success/failure callback issues for that ID.
  Sources: KEP-4403. Route: `text`.
  Confidence: **high** — The passage directly reports the duplication path and callback symptom.
  - `ev_4ae869bc7e9ee1a1` [0:226]: duplicate post IDs being sent to them. This is causing callback issues on success and failure for the same post ID. Currently, duplicate IDs are being sent because the same post can appear for a username, hashtag, and cashtag.
- **C6.** A Weibo processing ticket identifies missing service callbacks, but its supplied title alone does not show that duplicate IDs caused them.
  Sources: KEP-6650. Route: `text`.
  Confidence: **medium** — The title identifies the symptom, not its mechanism.
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
- **C7.** For an Argonaut-tenant government customer network, narrative generation jobs reportedly exceeded a 10-hour processing threshold, were killed, and re-queued into a silent loop without output or an alert.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The record directly states the reported timeout and retry mechanism.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C8.** A separate collection incident attributes a queue backup that prevented new jobs from starting to video-vision jobs failing to close their final steps.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The record directly gives this reported causal chain.
  - `ev_66f837dba0b6f0bf` [0:167]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting
- **C9.** Staging topic-clustering work reported algorithmic errors in some jobs after data collection was marked complete.
  Sources: KEP-2189. Route: `text`.
  Confidence: **medium** — The staging failure is reported, but the job-count passage is truncated.
  - `ev_ae8831731edc8c8f` [0:64]: Data collection is completed for all active networks in staging.
  - `ev_dcd6b5f9b30344e7` [0:85]: There a re failures in the topic clustering with algorithmic error for 18 jobs out of
- **C10.** BrightData batching was proposed to reduce rate-limiting issues, rather than documented here as a verified remedy for any cited outage.
  Sources: KEP-7025. Route: `text`.
  Confidence: **high** — Both passages explicitly frame batching as an aim or goal.
  - `ev_59b44c9c5c22ea16` [0:94]: This Epic aims to introduce a centralized batch processing service for BrightData API requests
  - `ev_e5585e8d13c80e28` [0:113]: The goal is to reduce rate limiting issues and improve data collection efficiency by grouping requests in batches
- **C11.** Detection gaps recur in the reports, but the Argonaut narrative-update failure and the multi-platform collection degradation are distinct incidents.
  Sources: KEP-6969, KEP-6970. Route: `text`.
  Confidence: **medium** — Both reports describe missed detection, while identifying different scopes and failure paths.
  - `ev_9b4317c218937e4f` [0:557]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026. The issue was not caught by any internal alarm — it was discovered by the government customer's own team, then, when the issue continued, our alarms caught it but no action was taken. Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing.
  - `ev_75b67275157f9120` [0:324]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing. Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21, confirming the outage window. No automated alarm detected the issue during the 8-day window.

## Unanswered

- Whether the proposed or reported fixes were deployed and verified to prevent recurrence.
- The diagnostic cause of the narrative-level stance aggregation discrepancy and of the last-narrative-date issue.
- Whether the Weibo missing callbacks share any mechanism with duplicate-post-ID callbacks.

## Limitations

- The supplied passages are selected records, so they do not establish prevalence.
- Some evidence is a ticket title, requirement, or truncated passage rather than an execution trace.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
