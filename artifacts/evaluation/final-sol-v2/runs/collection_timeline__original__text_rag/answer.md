# How did the April collection incident progress from reported failures through remediation and backfill, and what recovery is verified?

Status: partial

- **C1.** KEP-6970 reports severely degraded or failing Facebook, Instagram, and TikTok collection from approximately April 21–29, 2026.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The record states the platforms, condition, and approximate window directly.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** KEP-6970 says no automated alarm fired during the period.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Direct statement in the incident record.
  - `ev_06eee086b8cf9d93` [0:43]: No automated alarm fired during this period
- **C3.** KEP-6970 attributes a queue backup that prevented new jobs from starting to video-vision jobs not closing their final steps properly.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The causal account is explicit in the record.
  - `ev_66f837dba0b6f0bf` [0:167]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting
- **C4.** The reported host-PID fix was applied before the Kepler 19.2.0 deployment.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The passage directly states the fix and its relative timing.
  - `ev_1faf97ee0458fc4b` [0:47]: Host PID fix applied prior to 19.2.0 deployment
- **C5.** A separate YouTube account reports YTDLP download failures with high rates of SmartProxy 403 errors and a migration of YouTube downloads to Brightdata.
  Sources: KEP-6971. Route: `text`.
  Confidence: **high** — KEP-6971 directly reports the failures and migration.
  - `ev_5a437fcbb1decfd2` [0:137]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests.
  - `ev_1a105ce0683db415` [0:61]: Migrated YouTube download proxy from SmartProxy to Brightdata
- **C6.** The April 28 standup account says the cron job sending failure callbacks needed to be disabled before backfill could be triggered.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The dependency and standup context are explicit.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C7.** KEP-6970 reports Kepler 19.2.0 deployment on April 29, when Kiran Sabbani ordered backfill from April 21.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The deployment and order are stated directly.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
- **C8.** The requested backfill covered TikTok, Instagram, YouTube, and Facebook from April 21.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The requested platforms and start date are explicit.
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C9.** On April 30, a TikTok merge-request bypass was requested and 19.2.1 hotfix merge requests for brightdata-batching-service and data-source-facebook were deploying to staging.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Both April 30 actions are directly reported.
  - `ev_2aaa51b05f284118` [0:100]: Apr 30, 7:00 AM EDT — TikTok MR bypass requested in #kepler-dev-all-pods (data-source-tiktok MR 501)
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C10.** The supplied passages verify reported fix application, a 19.2.0 deployment, a backfill order, and staging hotfix activity, but not completed backfill or restored collection.
  Sources: KEP-6970. Route: `text`.
  Confidence: **medium** — The positive milestones are explicit; the recovery boundary reflects what these supplied passages do not document.
  - `ev_1faf97ee0458fc4b` [0:47]: Host PID fix applied prior to 19.2.0 deployment
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document

## Unanswered

- Was the failure-callback cron actually disabled, and when?
- Did the four-platform backfill run and complete successfully?
- When, if at all, did collection return to normal, and what measurements verified it?
- Did the April 30 staging hotfixes reach production?

## Limitations

- The passages do not independently verify the reported root cause or quantify customer impact.
- The YouTube SmartProxy failure is documented separately from the Facebook, Instagram, and TikTok queue-backup account.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
