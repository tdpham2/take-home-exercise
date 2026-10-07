# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** The stated scope was pruning Narratives, not Comment Conversations.
  Sources: Community_114. Route: `text`.
  Confidence: **high** — Direct requirement.
  - `ev_87879ee4d1969114` [0:74]: Pruning should only be applicable to Narratives, not Comment Conversations
- **C2.** The project reported completed pruning-related input and output code changes and local testing.
  Sources: Community_114. Route: `text`.
  Confidence: **high** — Each activity is explicitly reported.
  - `ev_daf242ee923d0264` [0:64]: Code changes completed for narrative pruning input data creation
  - `ev_530274020d30e7a8` [0:62]: Code changes completed for topic_narratives output data update
  - `ev_bf1bbd5f170a12a9` [0:45]: Local testing completed for narrative pruning
- **C3.** API integration for Narrative Pruning was reported deployed to the Dev environment.
  Sources: KEP-4238. Route: `text`.
  Confidence: **high** — Direct environment-specific report.
  - `ev_1891e24034dc3a2f` [0:111]: API integration for Narrative Pruning has been completed. The changes have been deployed to the Dev environment
- **C4.** A rule-deletion change was reported implemented and merged in staging so deletion would be reflected in topic narratives.
  Sources: KEP-4019. Route: `text`.
  Confidence: **high** — Direct implementation and staging-merge report.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C5.** Staging QA reported that deleting a pruning rule left its Narrative hidden rather than restoring it to the main tab.
  Sources: KEP-5342. Route: `text`.
  Confidence: **high** — Direct observed-behavior report.
  - `ev_6b1271f609ce438e` [0:176]: Even after deleting the pruning rule: The Narrative does not reappear in the main Narrative tab. The Narrative remains hidden. Suppression state appears to persist incorrectly.
- **C6.** A deletion-restoration retest was labeled as having completed testing.
  Sources: KEP-4050. Route: `text`.
  Confidence: **high** — The retest label and testing-completion statement are explicit.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
  - `ev_1d3ba24c5a1d0d02` [0:26]: Testing fo this is complet
- **C7.** Staging QA reported Comment Narratives being allowed for pruning despite the Narratives-only specification.
  Sources: KEP-5757. Route: `text`.
  Confidence: **high** — The environment, observed behavior, and specification conflict are stated directly.
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives
- **C8.** One report says users without an active token were blocked from hiding or flagging a Narrative, contrary to a permissions-only requirement.
  Sources: KEP-5759. Route: `text`.
  Confidence: **high** — Both the reported block and the contrasting requirement are explicit.
  - `ev_1ad128968e343ee3` [0:126]: System blocks pruning when no active token is available. User cannot proceed with Hide / Flag action due to token restriction.
  - `ev_521322613ce8c085` [0:143]: As per requirement, pruning capability should be restricted only based on user permissions (Viewer vs Editor) — not based on token availability
- **C9.** A separate report says a tokenless user could create a pruning rule but was blocked from deleting it.
  Sources: KEP-6413. Route: `text`.
  Confidence: **high** — Direct report of the create/delete contrast.
  - `ev_ace0d087762ec7f6` [0:351]: Currently, when a user does not have available tokens , the user is still able to create a Narrative Prune Rule and prune narratives successfully . However, when the same user attempts to delete the created prune rule from the Agent Detail Page → Narrative Pruning section , the system shows an error message stating that the user does not have tokens
- **C10.** For rule update and deletion APIs, a record reports removal of the token-check logic.
  Sources: KEP-6413. Route: `text`.
  Confidence: **high** — Direct remediation report.
  - `ev_d42ebd7f985b5490` [0:94]: The Token check Logic was kept in updfation and delete pruning rules API's. We have removed it
- **C11.** A Hidden-tab report says manually hiding another Narrative could also make non-hidden Narratives appear there; the issue was later reported resolved.
  Sources: KEP-6460. Route: `text`.
  Confidence: **medium** — The observation and resolution statement are direct, but the supplied passages do not include the video or independent verification.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
  - `ev_556016c4f8f9dfec` [0:88]: This issue is resolved, moving the status to done. Please check the video attached below
- **C12.** The hover reportedly showed the pruning rule immediately after pruning but showed the Narrative title on a return the next day.
  Sources: KEP-6419. Route: `text`.
  Confidence: **high** — Direct report with an explicit within-case sequence.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.

## Unanswered

- The passages provide no reliable dates to order the Dev deployment, staging merge, staging defects, retest, and token-check removal against one another. Ticket numbers and the 'Phase 2' label are not timestamps.
- Was rule-deletion restoration ever verified after the reported staging defect and completed retest?
- Were the token-check removal and Hidden-tab resolution deployed and verified in production?
- Was the next-day hover regression fixed?

## Limitations

- Only the within-report sequences—immediate pruning versus next-day hover behavior, and symptom versus reported resolution—can be ordered confidently. The broader remediation chronology remains unresolved.
- Requirements, completed testing, merges, and Done or resolved statements have different evidentiary strength and do not independently prove successful behavior.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
