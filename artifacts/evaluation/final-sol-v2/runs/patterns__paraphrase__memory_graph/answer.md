# Across narrative and collection processing, what reported failure mechanisms recur, and which differences prevent treating them as one cause?

Status: partial

- **C1.** Narrative Graph processing reportedly encountered Network Trigrams macro_ids absent from Macro Narratives; the source attributes a processing KeyError to that mismatch.
  Sources: KEP-4243. Route: `graph`.
  Confidence: **high** — The source explicitly reports the mismatch and its attributed exception.
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
- **C2.** An Instagram issue reports an exception because a post was unavailable in ES/docDB; this is record unavailability, not the same cross-collection macro_id mismatch.
  Sources: KEP-4243, KEP-5394. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The reported missing objects differ, while no common underlying cause is shown.
  - `ev_efe60f324c3ee2ac` [0:58]: Bug| Instagram | Exception: Post Not available in ES/docDB
  - `ev_857bba204521b877` [0:116]: Records with macro_ids exist in the Network Trigrams collection but are missing from the Macro Narratives collection
- **C3.** A comments export report instead identifies malformed fields: a null media_id and an id that does not follow the stated post_id-plus-profile_id schema.
  Sources: Community_647. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source states the field-level defects directly.
  - `ev_460c9517f1228627` [0:147]: Key: data issue from export comments docDB filter: this json contains "media_id" : null also "id" filed is not as per schema (post_id + profile_id)
- **C4.** A separate Instagram report says an .mp4 was present while ES showed post type 2, indicating a reported media-type mismatch rather than missing data.
  Sources: KEP-5577. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The discrepancy is explicit, but the intended meaning of type 2 is not supplied.
  - `ev_1735aa477b27776b` [0:78]: This post contains .mp4 file at index 2 location but showing post type 2 in es
- **C5.** Collection-side duplicate post IDs were reported to arise when one post matched a username, hashtag and cashtag, producing conflicting success/failure callbacks for the same ID.
  Sources: KEP-4403. Route: `graph`.
  Confidence: **high** — The source explicitly states both the duplication route and callback issue.
  - `ev_4ae869bc7e9ee1a1` [0:226]: duplicate post IDs being sent to them. This is causing callback issues on success and failure for the same post ID. Currently, duplicate IDs are being sent because the same post can appear for a username, hashtag, and cashtag.
- **C6.** Large-volume narrative generation jobs were reported terminated after exceeding a 10-hour processing SLA timeout, a runtime-limit mechanism distinct from data-integrity faults.
  Sources: KEP-6969. Route: `graph`.
  Confidence: **medium** — Termination and timeout are direct reports; the cross-incident distinction is synthesis.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
- **C7.** Another narrative report says objects were created but associated statistics were missing, showing that apparent creation success did not establish complete output.
  Sources: KEP-6948. Route: `graph`.
  Confidence: **medium** — The source directly contrasts creation with missing statistics; the completeness framing is synthesis.
  - `ev_d42e52c6eefc4edd` [0:219]: Narratives are being created successfully for networks, including: Common Narratives Post Narratives Themes However, associated narrative statistics are missing: Total Views Attention Average Score Total Number of Posts
- **C8.** The proposed response to missing macro_ids was to ignore them during Narrative Graph backend processing; it is a prescription, not evidence that the inconsistency was repaired or recovery verified.
  Sources: KEP-4243. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The conditional 'should' unambiguously expresses desired handling, not observed execution.
  - `ev_5a57e73b353bac90` [0:114]: If a macro_id is missing from Macro Narratives, it should be ignored during Narrative Graph backend API processing
- **C9.** Across these selected reports, failures recur broadly at processing boundaries—missing references or records, invalid or inconsistent fields, duplicate identifiers, time limits, and incomplete outputs—but the evidence does not establish one shared root cause.
  Sources: Community_647, KEP-4243, KEP-4403, KEP-6948, KEP-6969. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The comparison is supported by distinct reported symptoms and mechanisms, but selected records cannot establish prevalence or a universal explanation.
  - `ev_fe9edd081c5bc41d` [0:100]: This mismatch causes an inconsistent data state, resulting in a KeyError exception during processing
  - `ev_460c9517f1228627` [0:147]: Key: data issue from export comments docDB filter: this json contains "media_id" : null also "id" filed is not as per schema (post_id + profile_id)
  - `ev_4ae869bc7e9ee1a1` [0:226]: duplicate post IDs being sent to them. This is causing callback issues on success and failure for the same post ID. Currently, duplicate IDs are being sent because the same post can appear for a username, hashtag, and cashtag.
  - `ev_f3dba2eba43e2de5` [0:180]: Narrative generation jobs for networks with large data volumes (long-running networks) were being terminated by the application upon exceeding the processing SLA timeout (10 hours)
  - `ev_d42e52c6eefc4edd` [0:219]: Narratives are being created successfully for networks, including: Common Narratives Post Narratives Themes However, associated narrative statistics are missing: Total Views Attention Average Score Total Number of Posts

## Unanswered

- What caused the missing narrative statistics and the Instagram record or field discrepancies is not established here.
- The cited reports do not verify deployment, durable repair, or end-to-end recovery.

## Limitations

- These are selected reports, not a prevalence estimate; overlapping passages from one ticket are not independent incidents.
- Source-reported causes are distinguished from the cross-record comparison, which is synthesis.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
