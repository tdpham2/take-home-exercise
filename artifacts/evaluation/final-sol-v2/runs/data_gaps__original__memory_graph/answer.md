# What explanations do the records support for DocDB/Elasticsearch data gaps, and what remains unresolved?

Status: partial

- **C1.** A record reports major gaps and inconsistencies between DocDB and Elasticsearch, without identifying their cause.
  Sources: Community_141. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — Direct extracted wording reports the condition, not a mechanism.
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C2.** A separate record attributes DocDB/Elasticsearch drift to partial de-duplication updates, but does not describe the failure mechanism.
  Sources: KEP-6664. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The attribution is explicit but appears only in a brief extracted description.
  - `ev_98651123bedd9e11` [0:50]: DocDB/ES drift from partial de-duplication updates
- **C3.** Another record reports uneven or incomplete DocDB data; completeness within DocDB and agreement between DocDB and Elasticsearch are distinct questions.
  Sources: Community_141, KEP-6611. Route: `memory`.
  Confidence: **medium** — The excerpts describe different checks, without establishing whether the same data was affected.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
  - `ev_6c9707c22f4b3e34` [0:67]: Major data gaps and inconsistencies between DocDB and Elasticsearch
- **C4.** Incorrect cursor handling is a possible explanation for inconsistent DocDB storage, but the causal connection appears in an inferred graph rationale, not a directly extracted source passage.
  Sources: KEP-6611. Route: `memory`.
  Confidence: **low** — Only the inferred rationale supplies the cursor-related causal claim.
  - `ev_1c518266822509e0` [0:386]: Resolving data ingestion failure (decision_80b5b8e1) depends on fixing inconsistent DocDB storage due to incorrect cursor handling (decision_02d55676). The cursor handling issue directly impacts data ingestion; the ingestion failure cannot be properly diagnosed without first resolving the cursor inconsistency. Both decisions share DocDB as a target resource and the same participants.
  - `ev_d12f9a9f4427477b` [0:41]: Data stored in DocDB is uneven/incomplete
- **C5.** For Weibo data, valid Tikhub HTTP 200 responses were reported alongside missing ingestion into DocDB/Elasticsearch. This places the observed gap after retrieval but does not identify the failing step.
  Sources: KEP-6610, gdrive:1mXMcKxPJDNpoazNcmy5zt3j_2Sg9S258XJt_xwrq5xg. Route: `memory`.
  Confidence: **medium** — The observations bracket the gap but do not isolate a technical cause.
  - `ev_afaa76709f32a0cf` [0:81]: Tikhub for Weibo data are returning HTTP 200 responses with valid video post data
  - `ev_08a24f67b8645adb` [0:40]: data is not being ingested into docDb/ES
  - `ev_855ed0b570fdb824` [0:27]: Tikhub → processing → DB/ES

## Unanswered

- Which processing or persistence step failed in the Weibo ingestion path?
- What cursor-handling error occurred, and did it contribute to the reported gaps?
- Were de-duplication drift, incomplete DocDB storage, and Weibo non-ingestion one incident or separate issues?
- Were fixes deployed and validated through source-to-store completeness and DocDB-to-Elasticsearch reconciliation checks?

## Limitations

- Inferred graph dependencies and supersession claims are not direct source reports of causality or chronology.
- The available extracted passages do not quantify the gaps, describe repairs, or establish post-fix recovery. An administrative Done status is not substantive validation.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
