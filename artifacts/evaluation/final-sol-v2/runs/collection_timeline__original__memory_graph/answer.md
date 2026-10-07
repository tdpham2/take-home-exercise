# How did the April collection incident progress from reported failures through remediation and backfill, and what recovery is verified?

Status: partial

- **C1.** The incident record reports severely degraded or failing Facebook, Instagram, and TikTok collection from approximately April 21 through April 29, 2026.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The incident passage states the approximate window and affected platforms directly.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The incident record says no automated alarm detected the problem during that eight-day window.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The absence of an automated alarm is stated directly in the incident passage.
  - `ev_75b67275157f9120` [0:324]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing. Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21, confirming the outage window. No automated alarm detected the issue during the 8-day window.
- **C3.** The reported technical cause was video-vision jobs failing to close their final steps, backing up the queue and preventing new jobs from starting; the record says a host-PID setting change was applied as the fix.
  Sources: KEP-6970. Route: `memory`.
  Confidence: **high** — The passage directly reports the cause and applied change, though it does not independently demonstrate sustained recovery.
  - `ev_48b827cfe137a976` [0:205]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied
- **C4.** An April 28 standup note said the cron job sending failure callbacks needed to be stopped before backfill could be triggered; it described coordination to do so, not confirmed completion.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The prerequisite and coordination are explicit, but disabling the job is not confirmed by this wording.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C5.** After Kepler 19.2.0 was deployed on April 29, Kiran Sabbani ordered backfill from April 21 for TikTok, Instagram, YouTube, and Facebook.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The passages directly establish the order, target start date, and platforms; they do not establish completion.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C6.** By the April 30 update, 19.2.1 hotfix merge requests for brightdata-batching-service and data-source-facebook were deploying to staging; this does not establish production deployment.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **high** — The original passage specifies staging, not production.
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C7.** Full data integrity was described as requiring backfill from April 21; the cited evidence does not verify that backfill finished or that collection and historical data fully recovered.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The source states a requirement and a future-oriented plan, not a completed backfill or validated recovery.
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April

## Unanswered

- Whether the failure-callback cron was actually disabled and the backfill triggered or completed.
- Whether collection returned to normal across all affected platforms and customer networks, and whether historical data integrity was validated.
- Whether the 19.2.1 hotfix reached production or improved recovery.

## Limitations

- The April 21 start is approximate; do not treat it as an exact failure timestamp.
- The incident passages are source reports, not independent operational telemetry or proof of sustained recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
