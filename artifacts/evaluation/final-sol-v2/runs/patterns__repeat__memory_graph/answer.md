# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** Narrative output can stall after an upstream handoff: one incident reported an S3 upload whose downstream processing did not start.
  Sources: KEP-6688. Route: `memory`.
  Confidence: **high** — Direct incident wording.
  - `ev_e069cd9a1a360b09` [0:81]: Input file successfully uploaded to S3 , but downstream processing did not start.
- **C2.** Narrative statistics also lagged under production-scale load despite working in smaller staging deployments, leaving narrative UI data hours late.
  Sources: KEP-6189. Route: `memory`.
  Confidence: **medium** — The record reports both conditions, but these excerpts alone do not prove a complete causal chain.
  - `ev_0aa92eb7859f3f5e` [0:91]: The pipeline works fine in staging (4‑7 networks) but fails in production (~200+ networks).
  - `ev_78b67c045ef5dda3` [0:59]: UI data for micro‑ and macro‑narratives appears hours late.
- **C3.** A different narrative failure was a no-output retry loop: the same job was re-queued and killed repeatedly after exceeding a 10-hour processing timeout.
  Sources: KEP-6969. Route: `memory`.
  Confidence: **high** — The source explicitly describes the timeout and repeated termination.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C4.** Collection-side processing has analogous handoff failures, but at service boundaries: a BrightData batching record reports no retry for connection-refused or network failures and missed job creation.
  Sources: KEP-5076. Route: `graph`.
  Confidence: **medium** — The record describes the failure path, while temporary unavailability is framed as a possibility.
  - `ev_91a620eacb16c78c` [0:264]: BrightData batching service may be temporarily unavailable (pod restart, rollout, scaling). No retry mechanism exists for connection refused / network-level failures . Causes: Unnecessary task failures Missed BrightData job creation Inconsistent ingestion behavior
- **C5.** Collection processing can also fail through missing completion signals: records flag missing Weibo service callbacks and missing YouTube comment-seed callbacks.
  Sources: KEP-5829, KEP-6650. Route: `graph`.
  Confidence: **medium** — Two distinct source records name missing callbacks, but do not establish identical root causes.
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
  - `ev_c2120be5c598d246` [0:48]: Bug: Youtube missing Comment seed data callbacks
- **C6.** Collection-side resource pressure differs from the narrative timeout loop: one record says funding or quota exhaustion stops collection, while another identifies a hotkey that rate-limits one key while another is underused.
  Sources: KEP-6923, KEP-7004. Route: `graph`.
  Confidence: **medium** — Both mechanisms are source-described, but neither establishes their frequency or shared cause.
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.
  - `ev_b6d3a92e94cec12c` [0:121]: Hotkey issues — load concentrates on a single key, leading to rate-limiting on one key while the other is under-utilised.
- **C7.** The common symptom is delayed or absent downstream output, not one shared defect: narrative records identify orchestration, statistics lag, and timeout/requeue mechanisms; collection records identify missing callbacks, absent transient-failure retries, and quota or rate-limit constraints.
  Sources: KEP-5076, KEP-6189, KEP-6650, KEP-6688, KEP-6923, KEP-6969. Route: `memory`.
  Confidence: **medium** — This is a bounded comparison of selected records, not a prevalence estimate.
  - `ev_e069cd9a1a360b09` [0:81]: Input file successfully uploaded to S3 , but downstream processing did not start.
  - `ev_78b67c045ef5dda3` [0:59]: UI data for micro‑ and macro‑narratives appears hours late.
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
  - `ev_91a620eacb16c78c` [0:264]: BrightData batching service may be temporarily unavailable (pod restart, rollout, scaling). No retry mechanism exists for connection refused / network-level failures . Causes: Unnecessary task failures Missed BrightData job creation Inconsistent ingestion behavior
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.

## Unanswered

- The selected records do not establish prevalence, a single shared root cause, or verified recovery after proposed interventions.

## Limitations

- Incident descriptions and extracted graph passages are source reports, not independent operational verification.
- The staging and production examples refer to different conditions; they should not be merged into one environment.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
