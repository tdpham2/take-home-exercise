# How did the April collection incident progress from reported failures through remediation and backfill, and what recovery is verified?

Status: partial

- **C1.** KEP-6970 reports that Facebook, Instagram, and TikTok collection was severely degraded or failing approximately April 21–29, 2026.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — Direct retrospective ticket report; the window is approximate.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The ticket says no automated alarm detected the issue during that window.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — Reported in the incident ticket, without independent alarm records.
  - `ev_75b67275157f9120` [0:324]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing. Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21, confirming the outage window. No automated alarm detected the issue during the 8-day window.
- **C3.** A separate YouTube report attributed failed video downloads and high 403 rates to SmartProxy blocking YTDLP requests; it proposed moving downloads to Brightdata.
  Sources: KEP-6971. Route: `graph`.
  Confidence: **medium** — Ticket report identifies a distinct YouTube failure; the cited wording does not verify that migration was completed.
  - `ev_c7511760bf9c6367` [0:392]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests. This degraded YouTube data collection over approximately the same window as the broader FB/IG/TikTok outage (from ~Apr 21), and was confirmed separately by Austin Noronha on April 28. The fix was to migrate YouTube downloads from SmartProxy to Brightdata
- **C4.** KEP-6970 identified video-vision jobs failing to close final steps, backing up the queue and preventing new jobs; it reports that a host-PID setting fix was applied.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The cause and applied fix are the ticket's report, not independent proof of sustained recovery.
  - `ev_48b827cfe137a976` [0:205]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied
- **C5.** Following the reported Kepler 19.2.0 deployment on April 29, Kiran Sabbani ordered a backfill beginning April 21.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — Direct ticket wording supports deployment and the order, but not backfill execution.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
- **C6.** The stated backfill scope was TikTok, Instagram, YouTube, and Facebook from April 21.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **high** — The wording directly specifies intended scope, not completion.
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C7.** Before triggering backfill, the team said the cron job sending failure callbacks needed to be disabled; an April 28 standup described coordination to stop it.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **high** — Direct prerequisite and coordination report; it does not establish the cron was stopped.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C8.** By the reported April 30 update, 19.2.1 hotfix merge requests for brightdata-batching-service and data-source-facebook were deploying to staging, not verified in production.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **high** — The passage explicitly limits this activity to staging.
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C9.** The cited recovery evidence establishes an applied host-PID fix and a reported 19.2.0 deployment, but not completed backfill or restored full data integrity; the ticket calls backfill necessary for that restoration.
  Sources: KEP-6970. Route: `graph`.
  Confidence: **medium** — The sources report remediation and a requirement, while none cited verifies backfill completion or end-to-end recovery.
  - `ev_48b827cfe137a976` [0:205]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity

## Unanswered

- Was the failure-callback cron actually disabled and the backfill triggered or completed?
- Did post-fix collection resume reliably, and was data completeness verified across all four platforms?
- Was the YouTube Brightdata migration completed, and did it resolve the 403 failures?

## Limitations

- The incident and remediation passages are retrospective ticket reports, not independent operational measurements.
- April 28–30 mentions without an explicit year are not independently dated here; the approximate 2026 window comes from KEP-6970.
- No measured customer impact or confirmed recovery date is established by the cited evidence.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
