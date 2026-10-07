# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** Backend CRUD operations for narrative-pruning rules were specified, and API integration was reported complete; neither statement alone verifies end-to-end behavior.
  Sources: KEP-4238, KEP-4366. Route: `graph`.
  Confidence: **high** — Both statements appear directly in source extracts; their operational effect is unverified.
  - `ev_f19d74f6ba596733` [0:107]: Build Crud Operations for narrative pruning in application backend Collection Name: narrative_pruning_rules
  - `ev_d071431bf98c79f3` [0:56]: API integration for Narrative Pruning has been completed
- **C2.** The stated scope was Narratives, formerly Micro Narratives, rather than Comment Conversations; a staging QA retest reported that Comment Narratives were nevertheless allowed for pruning.
  Sources: Community_114, KEP-5757. Route: `graph`.
  Confidence: **high** — The prescription and contrary staging report are explicit; the retest title does not verify subsequent correction.
  - `ev_9972d78a7ed96453` [0:75]: pruning should only be applicable to Narratives (formerly Micro Narratives)
  - `ev_87879ee4d1969114` [0:74]: Pruning should only be applicable to Narratives, not Comment Conversations
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives
- **C3.** The intended rule-deletion behavior was to unhide affected narratives or return them to the Main tab; a record reported implementing deletion handling and merging it into staging.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — The first passage is an expectation; the second directly reports implementation and a staging merge, not successful operation.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C4.** A separate staging QA report said deleting the corresponding pruning rule did not return the pruned Narrative to the main tab.
  Sources: Community_1210, KEP-5342. Route: `graph`.
  Confidence: **high** — The staging label and observed behavior are directly reported; no verified recovery is shown.
  - `ev_8c6ddb56926d9ecb` [0:84]: 🪲QA: Staging : Deleted Pruning Rule Does Not Restore Narrative to Main Narrative Tab
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
- **C5.** A retest item called for restoring narratives after rule deletion, while another retest item reported that deleting a pruning rule did not sync immediately in the UI; these do not establish a successful retest.
  Sources: KEP-4050, KEP-5480. Route: `graph`.
  Confidence: **high** — Both item titles are explicit, but neither supplies a passing test result.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
  - `ev_0038d1e815d621c1` [0:60]: Retest: Deleted Pruning Rule Does Not Sync Immediately on UI
- **C6.** Another report said that hiding a Narrative when the Hidden tab already contained one also caused narratives not actually hidden to appear there; the documented expected behavior was no extra or duplicated entries.
  Sources: KEP-6460. Route: `graph`.
  Confidence: **high** — The observation and expected behavior are directly stated in the same defect record; no fix verification is present.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
  - `ev_4808624dac3da9b4` [0:270]: Expected behavior: The Hidden tab should only contain narratives that are actually hidden. This includes narratives hidden automatically by rules and any narratives newly hidden by the user. No additional narratives should appear there, and nothing should be duplicated.
- **C7.** A further report described pruning-rule hover text changing by the next day from the rule that hid the narrative to the narrative title.
  Sources: KEP-6419. Route: `graph`.
  Confidence: **high** — The behavior is explicit in a source report, but it is not proof of prevalence or root cause.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C8.** Only a partial order is supportable: requirements or intended behavior, implementation and staging work, and QA defect or retest records are identifiable, but the supplied passages do not establish a reliable date-by-date sequence or verified remediation across these defects.
  Sources: KEP-4019, KEP-4050, KEP-5342. Route: `graph`.
  Confidence: **medium** — The workflow stages are documented, but these excerpts have no confirmed timestamps or passing outcomes; item numbers and graph edges cannot supply chronology.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
  - `ev_8c6ddb56926d9ecb` [0:84]: 🪲QA: Staging : Deleted Pruning Rule Does Not Restore Narrative to Main Narrative Tab
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab

## Unanswered

- Which code changes, if any, corrected the Comment Narrative scope, deletion restoration or UI sync, Hidden-tab duplication, and hover-text defects?
- When did each staging report, fix, and retest occur, and did any retest pass?
- Were any defects deployed beyond staging or observed by customers?

## Limitations

- Requirements and expected behavior are not evidence of execution; a reported staging merge is not proof of successful behavior.
- The selected records provide no confirmed dates establishing a total chronology; ticket numbers and inferred graph links are not chronological evidence.
- Related quotations from the same record are not independent incidents.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
