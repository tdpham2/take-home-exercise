# Across narrative and collection processing, what reported failure mechanisms recur, and which differences prevent treating them as one cause?

Status: partial

- **C1.** A recurring failure pattern is missing completion signaling: one report says absent SQS notifications left tasks RUNNING, while a separate Weibo report names missing service callbacks.
  Sources: KEP-3912, KEP-6650. Route: `graph`.
  Confidence: **medium** — Both reports identify missing signals, but they concern distinct tasks and do not establish a shared cause.
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
- **C2.** The comment-narrative report separately labels an Algorithm Error; it does not show that the missing SQS notifications caused that error.
  Sources: KEP-3912. Route: `graph`.
  Confidence: **high** — The source lists two investigations without asserting their causal relationship.
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
- **C3.** In a collection/data-processing report, duplicate post IDs were said to cause callback issues; the report attributes duplicates to one post appearing under a username, hashtag, and cashtag. That is a different mechanism from an absent notification.
  Sources: KEP-4403. Route: `graph`.
  Confidence: **high** — The source explicitly reports both the duplicate-ID origin and the callback symptom.
  - `ev_4ae869bc7e9ee1a1` [0:226]: duplicate post IDs being sent to them. This is causing callback issues on success and failure for the same post ID. Currently, duplicate IDs are being sent because the same post can appear for a username, hashtag, and cashtag.
- **C4.** Another collection-side report describes transient BrightData batching-service connection failures with no retry, leading to task failures and missed job creation. This is an availability/retry gap, not evidence of the duplicate-ID mechanism.
  Sources: KEP-5076. Route: `graph`.
  Confidence: **medium** — The source states the risk and expected consequences; the temporary unavailability is framed as possible.
  - `ev_91a620eacb16c78c` [0:264]: BrightData batching service may be temporarily unavailable (pod restart, rollout, scaling). No retry mechanism exists for connection refused / network-level failures . Causes: Unnecessary task failures Missed BrightData job creation Inconsistent ingestion behavior
- **C5.** Narrative generation also had a time-budget failure: long-running, large-volume network jobs were reported terminated after exceeding a 10-hour processing SLA timeout.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The report directly names the workload, termination, and timeout.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
- **C6.** A cross-collection mismatch was reported: Network Trigrams records had macro_ids missing from Macro Narratives. The proposed handling was to ignore such IDs in Narrative Graph API processing; the prescription does not prove deployment or recovery.
  Sources: KEP-4243. Route: `graph`.
  Confidence: **medium** — The mismatch and proposed handling are direct; their implementation and outcome are not shown.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_5a57e73b353bac90` [0:114]: If a macro_id is missing from Macro Narratives, it should be ignored during Narrative Graph backend API processing
- **C7.** A separate report says network narratives were created but their statistics were missing, distinguishing downstream statistics generation from narrative creation failure.
  Sources: KEP-6948. Route: `graph`.
  Confidence: **high** — The source explicitly contrasts created narratives with missing statistics.
  - `ev_ed201d4f746ee339` [0:160]: Narratives are being created successfully for networks, including: Common Narratives Post Narratives Themes However, associated narrative statistics are missing
- **C8.** A backlog investigation listed duplicate processing, excessive retries, queueing bugs, trigger conditions, and backfill as alternatives to increased incoming volume, so backlog alone cannot identify a single collection-processing cause.
  Sources: KEP-7018. Route: `graph`.
  Confidence: **medium** — The report presents competing possibilities rather than a confirmed diagnosis.
  - `ev_4989871d48de03d1` [0:353]: The increase in processing and MLE-side queue backlog aligns with an actual increase in incoming social media data volume from the application side OR whether there is an unintended issue such as: Duplicate processing Excessive retries Queueing bug Incorrect trigger conditions Backfill replay side effects Misconfigured ingestion or summarization logic

## Unanswered

- Whether the missing SQS notifications, Weibo callbacks, duplicate-ID callbacks, and comment-narrative Algorithm Error share any underlying component or incident.
- Whether the proposed handling, retry changes, or timeout increase were deployed and verified to resolve their respective failures.

## Limitations

- These are selected source reports, not evidence of failure prevalence or a unified root cause.
- A title or proposed fix does not establish measured customer impact or verified recovery.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
