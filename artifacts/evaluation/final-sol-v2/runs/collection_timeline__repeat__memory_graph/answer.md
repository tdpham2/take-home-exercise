# How did the April collection incident progress from reported failures through remediation and backfill, and what recovery is verified?

Status: partial

- **C1.** KEP-6970 reports that Facebook, Instagram, and TikTok collection was severely degraded or failing for approximately April 21–29, 2026.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — Direct incident-record wording, with an approximate window.
  - `ev_477c9de5cda34331` [0:136]: From approximately April 21 through April 29, 2026, data collection for Facebook, Instagram, and TikTok was severely degraded or failing
- **C2.** The incident record says no automated alarm detected the degradation during that window.
  Sources: KEP-6970. Route: `memory`.
  Confidence: **high** — Direct record statement.
  - `ev_06eee086b8cf9d93` [0:43]: No automated alarm fired during this period
- **C3.** KEP-6970 attributes the queue backup to video-vision jobs not closing their final steps, which prevented new jobs from starting.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source explicitly reports this as the cause; it is not independently established.
  - `ev_66f837dba0b6f0bf` [0:167]: Root cause identified and fixed: video vision processing jobs were not closing their final steps properly, causing a queue backup that prevented new jobs from starting
- **C4.** The record reports a host-PID setting fix applied before the Kepler 19.2.0 deployment.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — Direct source statement about fix timing, not proof of sustained recovery.
  - `ev_1faf97ee0458fc4b` [0:47]: Host PID fix applied prior to 19.2.0 deployment
- **C5.** On deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered backfill starting April 21.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — Direct record wording; the order is not evidence of completion.
  - `ev_97a309f4cce85c3a` [0:92]: Upon deployment of Kepler 19.2.0 on April 29, Kiran Sabbani ordered a backfill from April 21
- **C6.** The planned backfill covered TikTok, Instagram, YouTube, and Facebook from April 21; this does not itself establish that YouTube collection had failed.
  Sources: KEP-6970. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The quoted plan names four platforms, whereas the failure report names three.
  - `ev_840978102672098c` [0:77]: Backfill to be done for TikTok, Instagram, YouTube and Facebook from 21 April
- **C7.** Disabling the cron job that sent failure callbacks was described as a prerequisite before triggering backfill.
  Sources: KEP-6970. Route: `memory`.
  Confidence: **high** — Direct prerequisite wording, without confirmation it was executed.
  - `ev_798015aecf48cc37` [0:100]: The cron job sending failure callbacks also needed to be disabled before backfill could be triggered
- **C8.** The record says backfill from April 21 was required to restore full data integrity, rather than saying full integrity had already been restored.
  Sources: KEP-6970. Route: `memory`.
  Confidence: **high** — The wording expresses a requirement, not a verified outcome.
  - `ev_cdf54cd1ff4aa620` [0:60]: Backfill from Apr 21 required to restore full data integrity

## Unanswered

- No cited evidence verifies that the cron was disabled, that backfill ran or completed, or that missing data was reconciled.
- No cited post-fix collection metrics or checks verify sustained recovery or the exact recovery time.

## Limitations

- The incident sequence is chiefly supported by repeated excerpts from one record, KEP-6970, not independent incident reports.
- A reported fix and a deployment-linked backfill order do not establish end-to-end recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
