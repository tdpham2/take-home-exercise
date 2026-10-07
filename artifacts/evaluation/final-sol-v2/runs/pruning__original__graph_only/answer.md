# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** The documented intended scope was pruning Narratives only, excluding Comment Conversations; this is a requirement, not proof that the restriction was enforced.
  Sources: Community_114. Route: `graph`.
  Confidence: **high** — The source states the intended scope directly.
  - `ev_87879ee4d1969114` [0:74]: Pruning should only be applicable to Narratives, not Comment Conversations
- **C2.** A staging retest was titled as a case where Comment Narratives remained eligible for pruning despite that specification; the title does not establish the retest result.
  Sources: KEP-5757. Route: `graph`.
  Confidence: **medium** — The ticket title reports the issue but gives no test outcome or fix verification.
  - `ev_8032f99cb1184961` [0:101]: Retest:🪲QA: Staging : Comment Narratives Are Allowed for Pruning Though PRD Specifies Only Narratives
- **C3.** The specified behavior on deleting a pruning rule was to unhide its related narratives or return them to the Main narrative tab.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — The expected behavior is explicit.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
- **C4.** A staging QA report says a pruned Narrative moved immediately to Hidden but did not return to the main tab after its rule was deleted.
  Sources: Community_1210, KEP-5342. Route: `graph`.
  Confidence: **high** — The report directly describes the observed sequence and identifies staging.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
  - `ev_8c6ddb56926d9ecb` [0:84]: 🪲QA: Staging : Deleted Pruning Rule Does Not Restore Narrative to Main Narrative Tab
- **C5.** A separate implementation report says the rule-deletion behavior was implemented and merged into staging; it does not verify that narratives were restored in testing or production.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — Direct implementation and staging-merge report, with no outcome measurement.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C6.** A retest was requested for restoring a Narrative to the main tab after rule deletion, but no result is shown.
  Sources: KEP-4050. Route: `graph`.
  Confidence: **high** — The cited text is a retest title, not a pass result.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
- **C7.** Another report says that, after a rule hid a narrative, hiding an additional narrative could make several narratives appear in Hidden although they were not hidden; the prescribed correction was for Hidden to contain only actually hidden narratives, without duplicates.
  Sources: KEP-6460. Route: `graph`.
  Confidence: **high** — Observed behavior and expected correction are stated in the same ticket.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
  - `ev_4808624dac3da9b4` [0:270]: Expected behavior: The Hidden tab should only contain narratives that are actually hidden. This includes narratives hidden automatically by rules and any narratives newly hidden by the user. No additional narratives should appear there, and nothing should be duplicated.
- **C8.** A hover-display report says the pruning rule appeared immediately after pruning, but on returning the next day the hover showed the narrative title instead; the prescribed behavior was to keep showing the rule used.
  Sources: KEP-6419. Route: `graph`.
  Confidence: **high** — The report directly contrasts immediate and next-day behavior with the expectation.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
  - `ev_0a9ab2f340184cf3` [0:105]: Expected behavior: The hover should always display the pruning rule that was used to prune the narrative.
- **C9.** The evidence supports only local ordering within reports—pruning before deletion, and immediate hover before next-day hover—not a confident overall chronology among the scope issue, deletion remediation, duplication issue, and hover issue.
  Sources: Community_1210, KEP-6419. Route: `graph`.
  Confidence: **medium** — The within-report sequences are explicit; the shown original passages lack reliable cross-ticket event dates.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.

## Unanswered

- Whether the scope restriction, rule-deletion restoration, duplication correction, or hover correction was ultimately verified in staging or production.
- The dated cross-ticket order of the reported defects, implementation, and retests.

## Limitations

- Ticket numbers and graph relationship labels do not establish chronology or causality.
- The implementation and staging-merge statement is not proof of successful behavior; retest titles are not pass results.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
