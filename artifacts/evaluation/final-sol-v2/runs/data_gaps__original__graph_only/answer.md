# What explanations do the records support for DocDB/Elasticsearch data gaps, and what remains unresolved?

Status: partial

- **C1.** In the Weibo records, Tikhub returned HTTP 200 responses with valid video-post data, while data was reported not ingested into DocDB or Elasticsearch. The failing stage is not identified.
  Sources: KEP-6610, gdrive:1mXMcKxPJDNpoazNcmy5zt3j_2Sg9S258XJt_xwrq5xg. Route: `graph`.
  Confidence: **medium** — The extracted reports support the contrast, but not a specific cause.
  - `ev_afaa76709f32a0cf` [0:81]: Tikhub for Weibo data are returning HTTP 200 responses with valid video post data
  - `ev_08a24f67b8645adb` [0:40]: data is not being ingested into docDb/ES
- **C2.** A separate ticket reports uneven or incomplete data stored in DocDB.
  Sources: KEP-6611. Route: `graph`.
  Confidence: **high** — Direct extracted ticket wording; it does not establish a mechanism.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C3.** Another ticket attributes DocDB/Elasticsearch drift to partial de-duplication updates.
  Sources: KEP-6664. Route: `graph`.
  Confidence: **high** — Direct extracted ticket wording, limited to the drift described there.
  - `ev_98651123bedd9e11` [0:50]: DocDB/ES drift from partial de-duplication updates

## Unanswered

- Where valid Weibo API responses were lost in the ingestion pipeline, and whether that explains all reported gaps.
- Whether cursor handling caused the incomplete DocDB storage; the available original excerpt does not establish that mechanism.
- Whether de-duplication drift and the Weibo ingestion gap were the same incident or explain the broader inconsistencies.
- The extent of missing data and whether any remediation was deployed and independently verified.

## Limitations

- Inferred graph links and administrative closure do not establish causality or recovery.
- The available excerpts lack pipeline traces, measurements, and post-fix validation.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
