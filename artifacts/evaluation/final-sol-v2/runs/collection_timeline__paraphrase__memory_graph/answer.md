# Trace the reported April collection failures, subsequent technical changes and backfill actions; what evidence confirms recovery?

Status: partial

- **C1.** KEP-6970 reports severely degraded or failing Facebook, Instagram and TikTok collection from approximately April 21 through April 29, 2026.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source excerpt states the approximate window and affected platforms directly.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The incident record reports that video-vision jobs failed to close their final steps, backing up the queue and preventing new jobs from starting; it says a host-PID setting change was applied.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — This is the record's explicit causal account and fix report, not independent validation of effectiveness.
  - `ev_9488fa8cc6db3d39` [0:348]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied. Apr 29, 6:42 AM EDT — Kiran Sabbani in #kepler-dev-all-pods: "Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April."
- **C3.** The record says no automated alarm detected the collection issue during the reported eight-day window.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source directly reports the monitoring gap.
  - `ev_75b67275157f9120` [0:324]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing. Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21, confirming the outage window. No automated alarm detected the issue during the 8-day window.
- **C4.** KEP-6970 reports Kepler 19.2.0 deployment on April 29 and an order to backfill from April 21 across TikTok, Instagram, YouTube and Facebook; the wording is an order, not proof of completed backfill.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The deployment and backfill order are explicit; completion is not stated.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C5.** Disabling the cron job that sent failure callbacks was identified as a prerequisite before triggering backfill; the passage does not confirm that it was disabled.
  Sources: KEP-6970. Route: `memory`.
  Confidence: **high** — The source explicitly frames this as a needed preparatory action.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C6.** On the following reported April 30, a TikTok merge-request bypass was requested, while 19.2.1 hotfix merge requests for the Brightdata batching service and Facebook data source were deploying to staging; neither passage establishes production deployment or collection recovery.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The actions and staging environment are explicit, but their ultimate results are unstated.
  - `ev_2aaa51b05f284118` [0:100]: Apr 30, 7:00 AM EDT — TikTok MR bypass requested in #kepler-dev-all-pods (data-source-tiktok MR 501)
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C7.** A separate KEP-6971 report attributes contemporaneous YouTube download failures to SmartProxy blocking YTDLP requests with 403 errors and identifies migration to Brightdata as the fix; it should not be conflated with the Facebook/Instagram/TikTok queue failure.
  Sources: KEP-6971. Route: `graph`.
  Confidence: **high** — The separate record directly identifies a different failure mechanism and proposed fix.
  - `ev_c7511760bf9c6367` [0:392]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests. This degraded YouTube data collection over approximately the same window as the broader FB/IG/TikTok outage (from ~Apr 21), and was confirmed separately by Austin Noronha on April 28. The fix was to migrate YouTube downloads from SmartProxy to Brightdata
- **C8.** The available incident evidence says backfill was required to restore full data integrity, but does not confirm that it ran or that collection and data completeness recovered.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — These passages establish a recovery requirement and plan, not a measured outcome.
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April

## Unanswered

- Was the callback cron job actually disabled and was the backfill executed successfully for each platform?
- Did the 19.2.1 changes reach production, and when?
- What post-fix job, collection-rate or data-integrity checks confirm recovery? None were found in the inspected evidence.

## Limitations

- The repeated KEP-6970 excerpts are one incident record, not independent corroboration.
- April dates without an explicit year were not treated as independently verified timestamps.
- Reported fixes and staging activity do not by themselves establish production recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
