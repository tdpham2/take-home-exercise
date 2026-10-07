# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** Narrative Pruning API integration was reported complete and deployed to Dev.
  Sources: KEP-4238. Route: `text`.
  Confidence: **high** — The passage directly reports completion and names the environment.
  - `ev_1891e24034dc3a2f` [0:111]: API integration for Narrative Pruning has been completed. The changes have been deployed to the Dev environment
- **C2.** The documented design called for backend-supplied pruning rules during narrative generation runs.
  Sources: Community_114. Route: `text`.
  Confidence: **medium** — The passage describes the data flow but provides no execution detail.
  - `ev_0efca8b5653af727` [0:69]: Pruning rules sent from backend service for narrative generation runs
- **C3.** The stated scope was Narratives rather than Comment Conversations, while a staging QA report said Comment Narratives were allowed for pruning.
  Sources: Community_114, KEP-5757. Route: `text`.
  Confidence: **medium** — The requirement and staging defect are explicit, but the passages do not establish when the mismatch began or ended.
  - `ev_87879ee4d1969114` [0:74]: Pruning should only be applicable to Narratives, not Comment Conversations
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives
- **C4.** A deletion-related change was reported implemented and merged in staging to reflect pruning-rule deletion in topic narratives.
  Sources: KEP-4019. Route: `text`.
  Confidence: **high** — The report directly identifies the change and staging merge.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C5.** A staging QA report said a narrative remained hidden after its corresponding pruning rule was deleted.
  Sources: KEP-5342. Route: `text`.
  Confidence: **high** — The observed failure is directly described.
  - `ev_6b1271f609ce438e` [0:176]: Even after deleting the pruning rule: The Narrative does not reappear in the main Narrative tab. The Narrative remains hidden. Suppression state appears to persist incorrectly.
- **C6.** A separate deletion-restoration retest was reported complete, without a stated pass result.
  Sources: KEP-4050. Route: `text`.
  Confidence: **high** — The passages identify the retest and report testing complete.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
  - `ev_1d3ba24c5a1d0d02` [0:26]: Testing fo this is complet
- **C7.** One reported behavior blocked Hide/Flag pruning without an active token, contrary to a stated requirement to gate it by user permission rather than token availability.
  Sources: KEP-5759. Route: `text`.
  Confidence: **medium** — The observed behavior and requirement are explicit, but no effective fix is demonstrated.
  - `ev_1ad128968e343ee3` [0:126]: System blocks pruning when no active token is available. User cannot proceed with Hide / Flag action due to token restriction.
  - `ev_521322613ce8c085` [0:143]: As per requirement, pruning capability should be restricted only based on user permissions (Viewer vs Editor) — not based on token availability
- **C8.** For pruning-rule update and delete APIs, a report says retained token-check logic was removed.
  Sources: KEP-6413. Route: `text`.
  Confidence: **high** — The remediation is directly reported.
  - `ev_d42ebd7f985b5490` [0:94]: The Token check Logic was kept in updfation and delete pruning rules API's. We have removed it
- **C9.** A hover reportedly showed the pruning rule immediately after pruning but showed the narrative title when the reporter returned the next day.
  Sources: KEP-6419. Route: `text`.
  Confidence: **high** — The within-report before/after behavior is explicit.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C10.** A report said hiding another narrative could cause additional, unhidden narratives to appear in the Hidden tab.
  Sources: KEP-6460. Route: `text`.
  Confidence: **high** — The reported sequence and erroneous display are direct.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
- **C11.** That Hidden-tab issue was later described within its record as resolved and moved to Done.
  Sources: KEP-6460. Route: `text`.
  Confidence: **high** — The record explicitly reports resolution.
  - `ev_556016c4f8f9dfec` [0:88]: This issue is resolved, moving the status to done. Please check the video attached below
- **C12.** The records support local sequences within individual reports, but not a confident overall order of the Dev integration, staging changes and defects, token remediation, hover defect, and Hidden-tab resolution.
  Sources: KEP-4019, KEP-4238, KEP-6419. Route: `text`.
  Confidence: **medium** — These passages establish environments or relative events, but supply no shared dates or explicit cross-record sequence.
  - `ev_1891e24034dc3a2f` [0:111]: API integration for Narrative Pruning has been completed. The changes have been deployed to the Dev environment
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.

## Unanswered

- What are the dated deployment and test results for each environment?
- Did deleting a pruning rule eventually restore affected narratives in staging or production?
- Was the Hide/Flag token restriction fixed, and was the update/delete API change deployed and verified?
- Was the hover defect fixed and independently retested?

## Limitations

- The supplied passages lack a reliable cross-record chronology and do not establish production outcomes.
- Requirements, retest completion, staging merges, and resolution statements are not interchangeable evidence of verified behavior.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
