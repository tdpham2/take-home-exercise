# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** Both areas show work that fails to reach completion, but the documented narrative-generation mechanism is application termination after a 10-hour processing threshold.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **medium** — The cited record directly reports the narrative cause; the cross-area framing is a synthesis.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C2.** Collection-side work can remain incomplete even after external processing finishes: Bright Data batch statuses were reported not to transition reliably from sent to completed.
  Sources: KEP-5668. Route: `graph`.
  Confidence: **high** — The record states the observed status-transition failure and its timing.
  - `ev_2387deb7a51273b0` [0:120]: Due to a bug, batch statuses are not reliably transitioning from sent → completed after Bright Data finishes processing.
- **C3.** Another completion-signaling failure was a callback_status type mismatch: a string was sent instead of an integer, leaving a background task group incomplete.
  Sources: KEP-5641. Route: `graph`.
  Confidence: **high** — The source explicitly reports this mechanism and outcome.
  - `ev_cccf85ea01d19cfa` [0:187]: Key: Root cause: callback_status is sent as a string instead of an integer, so the background service does not mark tasks as complete, leaving the task group stuck in an incomplete state.
- **C4.** A narrative-related investigation also reports missing SQS notifications that left tasks in RUNNING state; it separately calls out comment-narrative algorithm errors. Neither is the same mechanism as the 10-hour application kill.
  Sources: KEP-3912, KEP-6969. Route: `graph`.
  Confidence: **medium** — The records distinguish missing notifications, algorithm errors, and timeout termination, but do not establish a shared incident.
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C5.** Incomplete downstream data is another recurring symptom: narrative records had macro_ids in Network Trigrams but not Macro Narratives, while a collection record described DocDB data as uneven or incomplete.
  Sources: KEP-4243, KEP-6611. Route: `graph`.
  Confidence: **medium** — Both records support an incompleteness comparison, not a common cause.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C6.** Collection can also fail before processing begins: a Weibo network was reported created without date validation, with no source collection triggered. This differs from narrative jobs that started but were killed before completion.
  Sources: KEP-6777, KEP-6969. Route: `graph`.
  Confidence: **medium** — The comparison follows the reported trigger and termination states without asserting a shared system.
  - `ev_ab3e2ef2efebc39d` [0:131]: Network gets created successfully without date validation for Weibo. No data collection is triggered for any sources in the network
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing

## Unanswered

- Whether the cited failures shared an underlying cause or occurred in the same environment is not established.
- These records do not establish prevalence, measured customer impact, or verified recovery.

## Limitations

- The cited records are a selected sample; similar symptoms should not be counted as one incident.
- Reported causes and investigative descriptions are not independent verification of fixes or outcomes.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
