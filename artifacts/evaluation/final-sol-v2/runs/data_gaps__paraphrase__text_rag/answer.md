# What can we infer from the DocDB and Elasticsearch gap reports about their explanations, and which explanations remain uncertain?

Status: partial

- **C1.** A report describes major data gaps and inconsistencies between DocDB and Elasticsearch.
  Sources: Community_141. Route: `text`.
  Confidence: **high** — The passage states the discrepancy directly.
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C2.** A separate report says data stored in DocDB is uneven or incomplete.
  Sources: KEP-6611. Route: `text`.
  Confidence: **high** — The passage states the condition directly.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C3.** One report attributes DocDB/Elasticsearch drift to partial de-duplication updates.
  Sources: KEP-6664. Route: `text`.
  Confidence: **high** — The attribution is explicit in the passage.
  - `ev_98651123bedd9e11` [0:50]: DocDB/ES drift from partial de-duplication updates
- **C4.** Elasticsearch read timeouts are another reported failure mode: requests do not finish within the configured window, causing failures in code paths that depend on Elasticsearch.
  Sources: KEP-6815. Route: `text`.
  Confidence: **high** — The passage explicitly describes the timeout and resulting failures.
  - `ev_c1c1bf0abb13b4f9` [0:129]: Requests to Elasticsearch do not complete within the configured read window, causing failures in any code path that depends on ES
- **C5.** The supplied passages do not establish that the incorrectly marked “Created” task status caused the reported data gaps.
  Sources: Community_141. Route: `text`.
  Confidence: **medium** — Both issues appear in the supplied record, but neither excerpt states a causal link.
  - `ev_327810f5b874fd50` [0:43]: Task status incorrectly marked as "Created"
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch

## Unanswered

- Which records, systems, and time periods were affected by each reported gap, and are the reports describing the same incident?
- What evidence verifies that partial de-duplication updates caused the reported drift, and how much of the discrepancy do they explain?
- Did Elasticsearch timeouts, long-running searches, task-status errors, DocDB version differences, or incomplete DocDB writes contribute to any specific gap?
- Were the gaps repaired, and was consistency subsequently verified?

## Limitations

- The retrieved passages are short excerpts; they do not provide a reconciliation analysis or independently verified root cause.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
