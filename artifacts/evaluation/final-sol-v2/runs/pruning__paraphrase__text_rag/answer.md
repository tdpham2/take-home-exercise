# Which pruning behaviors and follow-up actions are reported, and what evidence supports their temporal order?

Status: partial

- **C1.** The pruning design was reported complete.
  Sources: Community_114. Route: `text`.
  Confidence: **high** — The passage directly reports completion.
  - `ev_04fcaa0002d7d7b3` [0:31]: Narrative Pruning TRD completed
- **C2.** Pruning was specified to apply to Narratives, not Comment Conversations.
  Sources: Community_114. Route: `text`.
  Confidence: **high** — The passage states the intended scope.
  - `ev_87879ee4d1969114` [0:74]: Pruning should only be applicable to Narratives, not Comment Conversations
- **C3.** A staging QA retest reported that Comment Narratives were allowed for pruning despite the specified restriction.
  Sources: KEP-5757. Route: `text`.
  Confidence: **high** — The passage directly labels the observation as a staging retest.
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives
- **C4.** The stated expected behavior was for pruned narratives to appear in Hidden Narratives in real time.
  Sources: Community_114. Route: `text`.
  Confidence: **high** — The passage explicitly states a requirement.
  - `ev_c16cd8a81b99410d` [0:71]: Pruned narratives must appear in Hidden Narratives section in real-time
- **C5.** The planned data handoff was for MLE to send pruning_flag: true and a pruning_id, with topic_narratives updated to carry those details.
  Sources: KEP-4255. Route: `text`.
  Confidence: **high** — Future-tense wording directly describes the planned handoff and update.
  - `ev_5fe9ae2fbae6ba91` [0:136]: MLE team will be sending a pruning_flag : true with the pruning_id :'' , we need to update topic_narratives entity with the same details
- **C6.** The retrieved summary reports that pruning rules were sent from the backend service for narrative-generation runs.
  Sources: Community_114. Route: `text`.
  Confidence: **medium** — The wording reports the action, but it is a brief summary without run-level evidence.
  - `ev_0efca8b5653af727` [0:69]: Pruning rules sent from backend service for narrative generation runs
- **C7.** The retrieved summary reports completed code changes for pruning input-data creation and topic_narratives output-data updates, followed by a report of completed local testing.
  Sources: Community_114. Route: `text`.
  Confidence: **medium** — Each completion is reported, but the passages do not directly date or sequence them.
  - `ev_daf242ee923d0264` [0:64]: Code changes completed for narrative pruning input data creation
  - `ev_530274020d30e7a8` [0:62]: Code changes completed for topic_narratives output data update
  - `ev_bf1bbd5f170a12a9` [0:45]: Local testing completed for narrative pruning
- **C8.** Narrative Pruning API integration was reported complete and deployed to the Dev environment.
  Sources: KEP-4238. Route: `text`.
  Confidence: **high** — The passage directly reports both completion and a Dev deployment.
  - `ev_1891e24034dc3a2f` [0:111]: API integration for Narrative Pruning has been completed. The changes have been deployed to the Dev environment
- **C9.** Deleting a pruning rule was expected to unhide its related narratives or return them to the Main narrative tab.
  Sources: KEP-4019. Route: `text`.
  Confidence: **high** — The passage directly states the expected behavior.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
- **C10.** A follow-up report says a feature reflecting pruning-rule deletion in topic narratives was implemented and its merge request merged in the staging environment.
  Sources: KEP-4019. Route: `text`.
  Confidence: **high** — The passage directly reports implementation and a staging merge.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C11.** The passages establish a requirement-to-reported-implementation relationship for rule deletion, but provide no dated cross-ticket sequence for the TRD, code changes, local testing, Dev deployment, staging merge, and staging retest.
  Sources: KEP-4019, KEP-4238, KEP-5757. Route: `text`.
  Confidence: **medium** — The reports distinguish intended behavior, implementation, environments, and retest, but contain no dates tying those separate records together.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
  - `ev_1891e24034dc3a2f` [0:111]: API integration for Narrative Pruning has been completed. The changes have been deployed to the Dev environment
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives

## Unanswered

- What dates, if any, establish the order among TRD completion, code changes, local testing, Dev deployment, staging merge, and the staging QA retest?
- Was the Comment Narratives staging defect fixed and successfully retested?
- Did deleting a pruning rule actually unhide affected narratives, and was pruning deployed to or verified in production?

## Limitations

- The Community_114 passages are brief summaries, not independent run logs or deployment verification.
- No cited passage establishes customer impact or a complete end-to-end chronology.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
