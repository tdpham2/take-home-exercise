# Trace the reported April collection failures, subsequent technical changes and backfill actions; what evidence confirms recovery?

Status: partial

- **C1.** KEP-6970 reports severely degraded or failing Facebook, Instagram, and TikTok collection from approximately April 21–29, 2026.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Directly stated in the incident passage.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The incident record says no automated alarm fired during the period.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Direct statement.
  - `ev_06eee086b8cf9d93` [0:43]: No automated alarm fired during this period
- **C3.** KEP-6970 attributes a queue backup to video-vision jobs not closing their final steps, preventing new jobs from starting.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The causal account is explicit in the record.
  - `ev_66f837dba0b6f0bf` [0:167]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting
- **C4.** The record says a host-PID fix was applied before the Kepler 19.2.0 deployment.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Direct sequencing statement.
  - `ev_1faf97ee0458fc4b` [0:47]: Host PID fix applied prior to 19.2.0 deployment
- **C5.** A separate YouTube report attributes failed YTDLP downloads to SmartProxy 403 errors and says downloads were migrated to Brightdata.
  Sources: KEP-6971. Route: `text`.
  Confidence: **high** — Both the reported failure and change are explicit.
  - `ev_5a437fcbb1decfd2` [0:137]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests.
  - `ev_1a105ce0683db415` [0:61]: Migrated YouTube download proxy from SmartProxy to Brightdata
- **C6.** Upon the reported April 29 Kepler 19.2.0 deployment, Kiran Sabbani ordered a backfill from April 21.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Direct report of deployment and backfill order.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
- **C7.** The stated backfill scope was TikTok, Instagram, YouTube, and Facebook data from April 21.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The intended platforms and starting date are explicit.
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C8.** The incident record says the failure-callback cron job needed to be disabled before backfill could be triggered.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Directly stated prerequisite.
  - `ev_798015aecf48cc37` [0:100]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered
- **C9.** On April 30, a TikTok MR bypass was requested, while 19.2.1 hotfix MRs for the Brightdata batching service and Facebook data source were reported deploying to staging.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Both actions and their staging/request status are explicit.
  - `ev_2aaa51b05f284118` [0:100]: Apr 30, 7:00 AM EDT — TikTok MR bypass requested in #kepler-dev-all-pods (data-source-tiktok MR 501)
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document

## Unanswered

- No supplied passage confirms that the backfill was triggered, completed, or reconciled against missing data.
- No supplied post-fix collection metrics, queue-clearance result, platform checks, or production verification confirms recovery.

## Limitations

- The supplied passages support a reported failure, changes, and planned backfill—not verified restoration. The staging hotfix report and backfill order must not be treated as recovery evidence.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
