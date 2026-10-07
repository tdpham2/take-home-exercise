# What explanations do the records support for DocDB/Elasticsearch data gaps, and what remains unresolved?

Status: partial

- **C1.** A record reports major data gaps and inconsistencies between DocDB and Elasticsearch.
  Sources: Community_141. Route: `graph`.
  Confidence: **high** — The extracted source text states the condition directly.
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C2.** A Weibo ingestion record reports valid video-post data in HTTP 200 responses from Tikhub; successful upstream responses alone do not establish that the posts reached DocDB or Elasticsearch.
  Sources: KEP-6610. Route: `graph`.
  Confidence: **medium** — The response observation is direct, but the extracted excerpt does not itself document the downstream failure.
  - `ev_afaa76709f32a0cf` [0:81]: Tikhub for Weibo data are returning HTTP 200 responses with valid video post data
- **C3.** A separate record reports uneven or incomplete data stored in DocDB.
  Sources: KEP-6611. Route: `graph`.
  Confidence: **high** — The extracted source text states the storage condition directly.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C4.** Another record identifies partial de-duplication updates as a source of DocDB/Elasticsearch drift.
  Sources: KEP-6664. Route: `graph`.
  Confidence: **high** — The extracted source label explicitly associates the drift with partial de-duplication updates; it does not establish how often this occurred.
  - `ev_98651123bedd9e11` [0:50]: DocDB/ES drift from partial de-duplication updates

## Unanswered

- What step between Tikhub responses and persistence failed, and whether that failure caused the reported cross-store gaps.
- Whether incorrect cursor handling caused the incomplete DocDB data; that causal link appears here only in inferred graph text, not an original excerpt.
- Whether the ingestion, incomplete-storage, and de-duplication reports describe one incident or distinct failures, and how much data each affected.
- Whether proposed fixes were deployed and whether reconciliation or recovery was verified.

## Limitations

- Inferred graph dependency and supersession links are not independent evidence of causation, chronology, or resolution.
- The available extracted excerpts are brief and do not provide a verified recovery outcome.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
