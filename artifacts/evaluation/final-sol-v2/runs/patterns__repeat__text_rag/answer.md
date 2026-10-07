# Which processing failure modes recur across narrative generation and collection, and where do the mechanisms differ?

Status: partial

- **C1.** Both narrative generation and data collection can stop producing new output, but the cited records describe different mechanisms.
  Sources: KEP-6923, KEP-6969. Route: `text`.
  Confidence: **medium** — The passages support a shared no-output symptom, not a shared cause.
  - `ev_1c1739cdda90321d` [0:174]: A government customer network in the Argonaut tenant (network_id: ca95298f-cb34-5119-b8f9-e447607dfab7) stopped generating narrative updates from approximately April 19, 2026
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.
- **C2.** For the Argonaut tenant network, the reported cause of missing narrative updates was generation jobs exceeding a 10-hour processing threshold and being killed before completion.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The incident passage explicitly reports the mechanism.
  - `ev_5f2b2e2ded8842f5` [0:196]: Root cause: narrative generation jobs for this network were repeatedly running beyond the processing time SLA threshold (10 hours at the time) and being killed by the application before completing
- **C3.** Those killed jobs reportedly re-queued into a silent retry loop without output or an alert.
  Sources: KEP-6969. Route: `text`.
  Confidence: **high** — The passage directly describes the retry behavior.
  - `ev_1b68761b66cc3cc3` [0:110]: The same job would then re-queue and be killed again, creating a silent retry loop with no output and no alert
- **C4.** Other tickets flag missing completion signals: one asks investigators to examine absent SQS notifications associated with tasks stuck RUNNING, while another names missing Weibo service callbacks.
  Sources: KEP-3912, KEP-6650. Route: `text`.
  Confidence: **medium** — Both passages identify missing signals, but the Weibo evidence is only a title and the SQS item is investigative.
  - `ev_8377265b8fad614c` [0:100]: Investigate the tasks where we did not receive SQS Notifications making the tasks stay in hang state
  - `ev_adb482ae008cdf13` [0:61]: Critical Weibo Processing Failures: Missing Service Callbacks
- **C5.** Staging topic-clustering jobs were reported to fail with an algorithmic error; a separate ticket calls for investigation of comment-narrative algorithm errors.
  Sources: KEP-2189, KEP-3912. Route: `text`.
  Confidence: **medium** — The staging failure is reported directly; the comment-narrative item is an investigation request.
  - `ev_dcd6b5f9b30344e7` [0:85]: There a re failures in the topic clustering with algorithmic error for 18 jobs out of
  - `ev_996046a98ac70ec7` [0:67]: Investigate the failure of the comment narratives (Algorithm Error)
- **C6.** A Narrative Graph processing record reports that macro IDs present in Network Trigrams but absent from Macro Narratives produce a KeyError.
  Sources: KEP-4243. Route: `text`.
  Confidence: **high** — The record directly states the mismatch and resulting exception.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
- **C7.** The proposed handling for missing macro IDs was to ignore them during Narrative Graph backend API processing.
  Sources: KEP-4243. Route: `text`.
  Confidence: **high** — The passage explicitly prescribes the behavior.
  - `ev_03b6897ac3e47a32` [0:155]: The backend should handle this scenario. If a macro_id is missing from Macro Narratives, it should be ignored during Narrative Graph backend API processing
- **C8.** The pipeline failure-mode list includes funding or quota exhaustion, rate-limit hits, and vendor or service outages as collection-side risks.
  Sources: KEP-6923. Route: `text`.
  Confidence: **high** — These modes are explicitly listed.
  - `ev_0c852a6941b0f4d8` [0:49]: Funding / quota exhaustion stops data collection.
  - `ev_a968798c28c0d7d6` [0:16]: Rate‑limit hits.
  - `ev_1dba2fdf457f30b3` [0:45]: Vendor / service outage not detected quickly.
- **C9.** A proposed BrightData batch service aimed to reduce rate limiting by grouping collection requests; the passage does not show that it was deployed or effective.
  Sources: KEP-7025. Route: `text`.
  Confidence: **high** — The passages state an aim and goal, not an outcome.
  - `ev_59b44c9c5c22ea16` [0:94]: This Epic aims to introduce a centralized batch processing service for BrightData API requests
  - `ev_e5585e8d13c80e28` [0:113]: The goal is to reduce rate limiting issues and improve data collection efficiency by grouping requests in batches
- **C10.** The pipeline list describes another propagation mechanism: model crashes can break downstream stages, and partial network-level failures may affect NE, NH, or Influence.
  Sources: KEP-6923. Route: `text`.
  Confidence: **high** — Both failure modes are explicitly listed.
  - `ev_db0c75ab2fb11e09` [0:54]: Pipeline model crashes → everything downstream breaks.
  - `ev_3d078a483bf0ab14` [0:57]: Partial network‑level failures (NE, NH, Influence, etc.).
- **C11.** Report generation can fail or return refusal text; the record only tentatively links this to OpenAI/Azure content filtering and large-scale generation.
  Sources: KEP-6760. Route: `text`.
  Confidence: **medium** — The failure is reported directly, but the proposed mechanism is qualified as apparent.
  - `ev_78270a30fb9ad835` [0:176]: report generation fails or returns 'I'm sorry I cannot assist with that request' responses, particularly when using Azure models or specific prompts related to sensitive topics
  - `ev_4722c9e12ee05946` [0:100]: This appears to be related to OpenAI/Azure content filtering and handling of large-scale generation.
- **C12.** Output-integrity problems also appear: one ticket reports inconsistent statistics across endpoints, and another reports micro-narratives returned with empty source arrays.
  Sources: KEP-4182, KEP-5643. Route: `text`.
  Confidence: **medium** — Both passages describe inconsistent or incomplete outputs, without establishing a shared cause.
  - `ev_5646d4217047176d` [0:34]: Inconsistent data across endpoints
  - `ev_0a44e4a243fc5a62` [0:102]: Key: The POST /summary/micro-narratives/list API endpoint returns narratives with empty source arrays.

## Unanswered

- Whether the proposed fixes were deployed or prevented recurrence.
- Whether the listed collection and pipeline risks correspond to specific incidents, and how often any mode occurred.
- Whether the SQS, Weibo callback, and algorithm-error tickets share underlying causes.

## Limitations

- The records mix incident reports, investigation requests, risk lists, and proposed work; they do not support prevalence estimates.
- The staging algorithm-error passage is truncated, so its job-failure proportion cannot be determined.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
