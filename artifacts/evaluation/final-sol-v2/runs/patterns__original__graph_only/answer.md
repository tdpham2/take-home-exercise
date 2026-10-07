# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** Long-running narrative-generation jobs were repeatedly killed after exceeding a 10-hour processing SLA; the record attributes this to large network data volumes.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **high** — The source directly reports the failure and its attributed mechanism.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C2.** Another narrative-side report combines missing SQS notifications, tasks left RUNNING, and comment-narrative algorithm errors; it does not establish that the algorithm errors caused the missing notifications.
  Sources: KEP-3912. Route: `graph`.
  Confidence: **high** — Both observations are directly stated, while their causal relationship is not.
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
- **C3.** Collection likewise has lost completion or failure signals: Weibo processing is reported with missing service callbacks, and failed Video-Summary tasks are reported not to trigger callbacks.
  Sources: KEP-2175, KEP-6650. Route: `graph`.
  Confidence: **medium** — Two source reports support a recurring signal-loss pattern, but concern distinct workflows.
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
  - `ev_90b8b0d6052b3676` [0:100]: Callbacks missing for failure cases Callbacks are not being triggered when Video-Summary tasks fail.
- **C4.** A collection-specific failure occurred before BrightData jobs could be created: calls to its batching service sometimes received connection-refused errors, with no retry mechanism reported for those network failures.
  Sources: KEP-5076. Route: `graph`.
  Confidence: **high** — The source directly identifies the connection error and reported retry gap; possible service-unavailability causes remain qualified.
  - `ev_3d5d2f47d4a972e3` [0:398]: While creating BrightData batching jobs, the system occasionally fails with a connection error when calling the BrightData batching service: HTTPConnectionPool(host='brightdata-batching-service.kepler.svc.cluster.local', port=12000): Max retries exceeded with url: /brightdata-batching/jobs/create (Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
  - `ev_91a620eacb16c78c` [0:264]: BrightData batching service may be temporarily unavailable (pod restart, rollout, scaling). No retry mechanism exists for connection refused / network-level failures . Causes: Unnecessary task failures Missed BrightData job creation Inconsistent ingestion behavior
- **C5.** Another collection-specific mechanism was upstream access failure: YouTube YTDLP downloads reportedly hit high rates of 403 errors when SmartProxy blocked requests, degrading collection.
  Sources: KEP-6971. Route: `graph`.
  Confidence: **high** — The source reports the failure and attributed access mechanism; it does not verify recovery after migration.
  - `ev_c7511760bf9c6367` [0:392]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests. This degraded YouTube data collection over approximately the same window as the broader FB/IG/TikTok outage (from ~Apr 21), and was confirmed separately by Austin Noronha on April 28. The fix was to migrate YouTube downloads from SmartProxy to Brightdata
- **C6.** BrightData collection also had a batch-lifecycle risk distinct from narrative compute timeout: the proposed safeguards call for reconciling batches stuck in sent status and making callback or retry updates idempotent.
  Sources: KEP-2175, KEP-5668. Route: `graph`.
  Confidence: **medium** — The null batch ID is reported, but the lifecycle controls are prescribed rather than verified as implemented.
  - `ev_5735a7f1cf387d96` [0:74]: Inconsistent batch_id presence In some failure scenarios, batch_id is null
  - `ev_6be1916061f01606` [0:340]: Correct Batch Lifecycle Handling Ensure robust status transitions from sent → completed (and any other relevant states), including: Handling of retries / callbacks from Bright Data. Idempotent updates to avoid inconsistent states. Stale Batch Detection & Recovery Add logic to detect batches stuck in sent beyond a configurable time window.
- **C7.** Thus the recurring pattern is interrupted or unacknowledged asynchronous processing, but the documented mechanisms differ: narrative work can exceed an application SLA or fail algorithmically, whereas collection can fail at external access, service connection, callback, or batch-state boundaries.
  Sources: KEP-3912, KEP-5076, KEP-6650, KEP-6969, KEP-6971. Route: `graph`.
  Confidence: **medium** — This is a cross-record comparison, not a claim that all systems share one root cause.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
  - `ev_d9db300b6974ef3b` [0:183]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state (i.e. RUNNING) Investigate the failure of the comment narratives (Algorithm Error)
  - `ev_c7511760bf9c6367` [0:137]: YouTube video download jobs using the YTDLP library were failing with high rates of 403 errors due to SmartProxy (SPA) blocking requests.
  - `ev_3d5d2f47d4a972e3` [0:140]: While creating BrightData batching jobs, the system occasionally fails with a connection error when calling the BrightData batching service:
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks

## Unanswered

- Whether the proposed batch-lifecycle controls were deployed and effective.
- Whether the reported collection and narrative failures produced measured customer impact or share any single root cause.

## Limitations

- The cited records cover distinct systems and workflows; recurrence means analogous failure modes in this selected evidence, not measured prevalence.
- Reported fixes and prescriptions do not by themselves verify recovery or deployment.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
