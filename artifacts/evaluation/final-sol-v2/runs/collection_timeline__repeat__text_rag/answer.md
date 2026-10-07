# How did the April collection incident progress from reported failures through remediation and backfill, and what recovery is verified?

Status: partial

- **C1.** KEP-6970 reports severely degraded or failing Facebook, Instagram, and TikTok collection from approximately April 21–29, 2026.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The record states the affected sources and approximate window directly.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The incident record says no automated alarm fired during the period.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Direct statement in the incident record.
  - `ev_06eee086b8cf9d93` [0:43]: No automated alarm fired during this period
- **C3.** KEP-6970 attributes a queue backup that prevented new jobs from starting to video-vision jobs not closing their final steps properly.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The record explicitly reports this causal diagnosis.
  - `ev_66f837dba0b6f0bf` [0:167]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting
- **C4.** KEP-6970 reports a host-PID setting fix applied before the 19.2.0 deployment.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The fix and its order relative to deployment are stated directly.
  - `ev_48b827cfe137a976` [0:205]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting. Fix: host PID setting change applied
  - `ev_1faf97ee0458fc4b` [0:47]: Host PID fix applied prior to 19.2.0 deployment
- **C5.** A separate YouTube report attributes high rates of YTDLP download 403 errors to SmartProxy blocking and reports degraded YouTube collection over approximately April 21–29.
  Sources: KEP-6971. Route: `text`.
  Confidence: **high** — KEP-6971 directly describes the YouTube failure and window.
  - `ev_5a437fcbb1decfd2` [0:137]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests.
  - `ev_966dbf6e0186fd0b` [0:56]: YouTube data collection degraded for ~8 days (Apr 21–29)
- **C6.** KEP-6971 reports migrating YouTube downloads from SmartProxy to Brightdata as the YouTube remediation.
  Sources: KEP-6971. Route: `text`.
  Confidence: **high** — The migration is stated directly.
  - `ev_1a105ce0683db415` [0:61]: Migrated YouTube download proxy from SmartProxy to Brightdata
- **C7.** An April 28 standup note said the cron job sending failure callbacks needed to be stopped before backfill could be triggered.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The passage directly states the prerequisite and coordination.
  - `ev_4700e329357c7762` [0:196]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered (per Apr 28 standup: Magna coordinating with Abhik Roy to stop cron before triggering backfill)
- **C8.** Following the reported April 29 deployment of Kepler 19.2.0, Kiran Sabbani ordered backfill from April 21 for TikTok, Instagram, YouTube, and Facebook.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — The deployment, order, start date, and listed sources are directly reported.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C9.** On April 30, a TikTok merge-request bypass was requested, and 19.2.1 Brightdata-batching-service and Facebook-source hotfix merge requests were deploying to staging.
  Sources: KEP-6970. Route: `text`.
  Confidence: **high** — Both April 30 actions are explicitly reported.
  - `ev_2aaa51b05f284118` [0:100]: Apr 30, 7:00 AM EDT — TikTok MR bypass requested in #kepler-dev-all-pods (data-source-tiktok MR 501)
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document
- **C10.** The supplied passages verify remediation reports and a backfill order, but do not verify completed backfill, restored collection, or full data integrity.
  Sources: KEP-6970. Route: `text`.
  Confidence: **medium** — The cited passages describe actions and a requirement, not completed recovery; the conclusion is limited to the supplied record.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity
  - `ev_14acd247410dce00` [0:150]: Apr 30, 7:25 AM EDT — 19.2.1 hotfix MRs deploying to staging: brightdata-batching-service and data-source-facebook tags, with a linked change document

## Unanswered

- Was the failure-callback cron actually disabled, and when?
- Was the April 21 backfill run and completed for each listed source, and what validation showed restored data integrity?
- When, if ever, did collection rates recover, and were the April 30 staging hotfixes deployed to production?

## Limitations

- The retrieved passages include repeated summaries of KEP-6970; these are not independent incident confirmations.
- The source reports degraded collection but supplies no measured customer-impact assessment or post-remediation recovery metrics.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
