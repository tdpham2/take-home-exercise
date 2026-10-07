# What explanations do the records support for DocDB/Elasticsearch data gaps, and what remains unresolved?

Status: partial

- **C1.** A record reports major gaps and inconsistencies between DocDB and Elasticsearch, without explaining their cause.
  Sources: Community_141. Route: `text`.
  Confidence: **high** — The report is explicit.
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C2.** Another record reports that data is not being ingested into DocDB or Elasticsearch.
  Sources: gdrive:1mXMcKxPJDNpoazNcmy5zt3j_2Sg9S258XJt_xwrq5xg. Route: `text`.
  Confidence: **high** — The ingestion failure is directly stated.
  - `ev_08a24f67b8645adb` [0:40]: data is not being ingested into docDb/ES
- **C3.** A separate record describes data stored in DocDB as uneven or incomplete.
  Sources: KEP-6611. Route: `text`.
  Confidence: **high** — The description is direct.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C4.** For one class of “post not available in ES” errors, an initial analysis reports that get-api returns posts outside the requested date range; those posts are absent from the corresponding Elasticsearch indices for that range, causing downstream failures.
  Sources: KEP-5582. Route: `text`.
  Confidence: **high** — The ticket explicitly gives this explanation for the stated errors.
  - `ev_4b4877ee9d6ab0e5` [0:258]: Problem Statement We are continuously getting the error "post not available in ES" for data coming from multiple get-api sources. In the first iteration of analysis, we found that: get-api is returning posts that are outside the relevant requested date range
  - `ev_cd82949318d4632d` [0:124]: Because these posts do not exist in the corresponding Elasticsearch indices for that date range, downstream processing fails
- **C5.** The proposed response to those out-of-range get-api results is to enforce requested-date-range filtering, but the passage does not show that the fix was implemented.
  Sources: KEP-5582. Route: `text`.
  Confidence: **high** — The proposed fix is explicit.
  - `ev_b9081dcdc406a856` [0:123]: Fix or enforce date-range filtering logic at the get-api layer so that only posts within the requested window are returned.
- **C6.** A media-deduplication ticket attributes wrong Elasticsearch data to logic that does not actually deduplicate the named downloaded-media fields against existing records.
  Sources: KEP-5358. Route: `text`.
  Confidence: **high** — The ticket directly states the defect and its reported effect.
  - `ev_50e6ee2c28410911` [0:282]: Issue: Incorrect media deduplication causing wrong data in ES. The current media deduplication logic only skips the download when the following conditions are met... However, there is no actual deduplication of: downloaded_media_s3_path is_media_downloaded against existing records.
- **C7.** An Elasticsearch ticket reports read-window timeouts under load that cause failures in ES-dependent code paths; this supports a possible access or processing failure, not proof that stored records are missing.
  Sources: KEP-6815. Route: `text`.
  Confidence: **medium** — The request failures are directly reported; their relevance to perceived gaps is a qualified synthesis.
  - `ev_93bb7a65168ad9a7` [0:178]: We're currently querying ~1,000 posts per request over a 6‑month lookback. The expectation is a <30s response, but under current Elasticsearch load we're exceeding that threshold
  - `ev_c1c1bf0abb13b4f9` [0:129]: Requests to Elasticsearch do not complete within the configured read window, causing failures in any code path that depends on ES

## Unanswered

- What caused the reported failure to ingest into DocDB and Elasticsearch?
- Which datasets, services, tenants, environments, and time periods are affected, and do the reports describe the same incident?
- Were the proposed filtering fix or any ingestion repairs deployed, and did record-level reconciliation verify recovery?
- How much of any apparent gap reflects absent stored data versus date-range mismatch, wrong media fields, query failures, or presentation?

## Limitations

- The supplied passages are short excerpts; they do not establish a single root cause, measured prevalence, customer impact, or verified recovery.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
