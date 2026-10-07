# Trace the reported April collection failures, subsequent technical changes and backfill actions; what evidence confirms recovery?

Status: partial

- **C1.** KEP-6970 reports that Facebook, Instagram, and TikTok collection was severely degraded or failing approximately April 21–29, 2026; it also says no automated alarm detected the issue during that eight-day window.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — Directly reported in KEP-6970, but the passage is an extracted account rather than an independent monitoring record.
  - `ev_75b67275157f9120` [0:324]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing. Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21, confirming the outage window. No automated alarm detected the issue during the 8-day window.
- **C2.** KEP-6970 identifies video-vision jobs failing to close their final steps as the cause of a queue backup that prevented new jobs from starting, and reports that a host-PID setting change was applied.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The record reports the diagnosis and applied change; it does not independently verify restored collection.
  - `ev_48b827cfe137a976` [0:205]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied
- **C3.** KEP-6970 reports deployment of Kepler 19.2.0 on April 29 and says Kiran Sabbani then ordered a backfill beginning April 21.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The source reports deployment and an order, not backfill completion.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
- **C4.** The proposed backfill covered TikTok, Instagram, YouTube, and Facebook; YouTube appears in the backfill scope, not in the cited three-platform failure report.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The two passages distinguish planned backfill scope from reported failure scope.
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C5.** Before triggering backfill, the team said the cron job sending failure callbacks needed to be disabled; the cited passage describes coordination, not confirmation that the job was stopped.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — This is a reported prerequisite and coordination step, not an execution record.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C6.** On April 30, 19.2.1 hotfix merge requests for brightdata-batching-service and data-source-facebook were reported as deploying to staging.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The passage establishes staging deployment activity, not production deployment or a successful outcome.
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C7.** The cited backfill language establishes a requirement to restore full data integrity, not that integrity was restored.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **high** — The source explicitly says ‘required’; it provides no completion or validation result.
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity

## Unanswered

- Was the failure-callback cron job actually disabled and the four-platform backfill run to completion?
- Were the 19.2.1 hotfixes deployed to production?
- What post-fix collection metrics or post-backfill validation confirms recovery and full data integrity?

## Limitations

- The supplied passages contain reports, orders, prerequisites, and staging activity, but no direct recovery or backfill-completion evidence.
- The cited passages are largely from one KEP-6970 account; repeated extracts are not independent confirmations.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
