# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** Pruning was reported to move a narrative immediately to Hidden, but deleting its rule left it hidden rather than restoring it to the main tab in a staging QA report.
  Sources: Community_1210, KEP-5342. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source explicitly reports both steps and identifies the QA environment.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
  - `ev_8c6ddb56926d9ecb` [0:84]: 🪲QA: Staging : Deleted Pruning Rule Does Not Restore Narrative to Main Narrative Tab
- **C2.** The documented desired behavior was to unhide affected narratives or return them to the main tab when a pruning rule is deleted.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — The quoted wording is an explicit requirement, not a result.
  - `ev_72945596997f9008` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
- **C3.** A later implementation statement says the rule-deletion feature was implemented and its merge request merged in staging; a restoration retest was identified, but the retrieved retest text does not report a passing result.
  Sources: KEP-4019, KEP-4050. Route: `graph`.
  Confidence: **medium** — Implementation and staging merge are directly reported, while the retest wording names a check rather than its outcome.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
- **C4.** A separate report says deleting a pruning rule did not automatically refresh the UI; subsequent records are labeled retests of that sync issue.
  Sources: KEP-5389, KEP-5480. Route: `graph`.
  Confidence: **medium** — The behavior is explicit, but the retrieved retest title does not establish whether it was fixed.
  - `ev_7e4519c3675b92f7` [0:69]: When a pruning rule is deleted, the UI does not refresh automatically
  - `ev_0038d1e815d621c1` [0:60]: Retest: Deleted Pruning Rule Does Not Sync Immediately on UI
- **C5.** Another report describes correct immediate hiding and rule attribution, followed on a next-day visit by hover text showing the narrative title instead of the pruning rule.
  Sources: KEP-6419. Route: `graph`.
  Confidence: **high** — The source directly specifies the before-and-after observation within one workflow.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C6.** A Hidden-tab report says hiding another narrative correctly moved that item, but also displayed several narratives that had not been hidden; the stated target was a Hidden tab containing only actually hidden items, without duplicates.
  Sources: KEP-6460. Route: `memory`.
  Confidence: **high** — Both observed and expected behavior are explicit in the same issue record.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
  - `ev_4808624dac3da9b4` [0:270]: Expected behavior: The Hidden tab should only contain narratives that are actually hidden. This includes narratives hidden automatically by rules and any narratives newly hidden by the user. No additional narratives should appear there, and nothing should be duplicated.
- **C7.** The Hidden-tab issue was reported as resolved and moved to Done, with a fix version listed, but these records alone do not verify deployment or durable correctness.
  Sources: Community_1397, KEP-6460. Route: `memory`.
  Confidence: **medium** — Closure and fix-version statements are direct, but neither establishes verified production behavior.
  - `ev_556016c4f8f9dfec` [0:88]: This issue is resolved, moving the status to done. Please check the video attached below
  - `ev_df57738ef0ee6fe8` [0:50]: resolution: Done | fix_versions: ["Kepler 18.0.1"]
- **C8.** Ordering is strongest within the reported workflows—immediate hiding before rule deletion, and correct initial hover before the next-day hover change. The retrieved excerpts do not establish a reliable calendar order among the restoration, UI-sync, hover, and duplication issues or prove that one remediation caused another.
  Sources: Community_1210, KEP-6419. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The local sequences are explicit; cross-issue chronology remains unverified.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.

## Unanswered

- Whether the restoration retest passed and whether restoration reached production.
- Whether the UI-sync and hover issues were fixed and remained fixed.
- Reliable calendar ordering across the separate issues and any causal relationship among them.

## Limitations

- The date-bearing claim linking the restoration bug to implementation appears only in an inferred graph rationale, so its dates and causation were not adopted.
- Administrative Done, a fix version, and a staging merge do not establish production deployment or sustained success.
- Repeated excerpts and overlapping tickets were not counted as independent incidents.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
