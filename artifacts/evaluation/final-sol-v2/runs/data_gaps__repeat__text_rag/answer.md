# What explanations do the records support for DocDB/Elasticsearch data gaps, and what remains unresolved?

Status: partial

- **C1.** A record reports major data gaps and inconsistencies between DocDB and Elasticsearch.
  Sources: Community_141. Route: `text`.
  Confidence: **high** — The record states the problem directly.
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C2.** Other records separately report that data is not being ingested into DocDB/ES and that data stored in DocDB is uneven or incomplete.
  Sources: KEP-6611, gdrive:1mXMcKxPJDNpoazNcmy5zt3j_2Sg9S258XJt_xwrq5xg. Route: `text`.
  Confidence: **high** — Both are direct reports.
  - `ev_08a24f67b8645adb` [0:40]: data is not being ingested into docDb/ES
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C3.** An initial analysis attributed recurring “post not available in ES” errors to get-api returning posts outside the requested date range; it reported that those posts were absent from the corresponding Elasticsearch indices.
  Sources: KEP-5582. Route: `text`.
  Confidence: **high** — The record explicitly gives this explanation for the errors.
  - `ev_4b4877ee9d6ab0e5` [0:258]: Problem Statement We are continuously getting the error "post not available in ES" for data coming from multiple get-api sources. In the first iteration of analysis, we found that: get-api is returning posts that are outside the relevant requested date range
  - `ev_cd82949318d4632d` [0:124]: Because these posts do not exist in the corresponding Elasticsearch indices for that date range, downstream processing fails
- **C4.** The proposed response to those out-of-range posts was to enforce date-range filtering at the get-api layer.
  Sources: KEP-5582. Route: `text`.
  Confidence: **high** — The passage explicitly states the proposed fix.
  - `ev_b9081dcdc406a856` [0:123]: Fix or enforce date-range filtering logic at the get-api layer so that only posts within the requested window are returned.
- **C5.** A separate issue attributes wrong Elasticsearch media data to deduplication logic that does not check downloaded-media fields against existing records.
  Sources: KEP-5358. Route: `text`.
  Confidence: **high** — The issue states both the defect and its reported effect.
  - `ev_50e6ee2c28410911` [0:282]: Issue: Incorrect media deduplication causing wrong data in ES. The current media deduplication logic only skips the download when the following conditions are met... However, there is no actual deduplication of: downloaded_media_s3_path is_media_downloaded against existing records.
- **C6.** A record reports Elasticsearch requests exceeding the configured read window under load, causing failures in ES-dependent code paths.
  Sources: KEP-6815. Route: `text`.
  Confidence: **high** — The record directly reports the timeout mechanism and failures.
  - `ev_93bb7a65168ad9a7` [0:178]: We're currently querying ~1,000 posts per request over a 6‑month lookback. The expectation is a <30s response, but under current Elasticsearch load we're exceeding that threshold
  - `ev_c1c1bf0abb13b4f9` [0:129]: Requests to Elasticsearch do not complete within the configured read window, causing failures in any code path that depends on ES
- **C7.** Investigators observed more than 25 Elasticsearch search tasks running for multiple days.
  Sources: KEP-6844. Route: `text`.
  Confidence: **high** — The observation is explicit.
  - `ev_152fb586fbeffd19` [0:97]: Observed 25+ search tasks ( indices:data/read/search ) running in Elasticsearch for multiple days

## Unanswered

- What is the scope and root cause of the reported DocDB/Elasticsearch inconsistencies, and are the separate ingestion and incomplete-DocDB reports part of the same incident?
- Were the proposed date-filter fix, media-deduplication changes, or DocDB upgrades deployed, and did any verified reconciliation or recovery follow?
- Did Elasticsearch timeouts or long-running searches cause missing records, or only retrieval and processing failures?

## Limitations

- The supplied passages contain reports, an initial analysis, and proposed work, but no record-level comparison or verified end-to-end outcome.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
