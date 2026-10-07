# Which pruning behaviors and follow-up actions are reported, and what evidence supports their temporal order?

Status: partial

- **C1.** In a staging QA report, pruning a narrative immediately moved it to Hidden; deleting its pruning rule afterward did not return it to the main tab.
  Sources: Community_1210, KEP-5342. Route: `memory`.
  Confidence: **high** — The report states both actions and their order directly.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
  - `ev_8c6ddb56926d9ecb` [0:84]: 🪲QA: Staging : Deleted Pruning Rule Does Not Restore Narrative to Main Narrative Tab
- **C2.** The stated desired behavior was to unhide affected narratives or return them to the main tab when their pruning rule was deleted.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — The wording explicitly states a requirement, not an observed result.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
- **C3.** A related ticket reported an implemented pruning-rule-deletion feature and a merge into staging, but this does not itself verify that previously hidden narratives were restored.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **medium** — The implementation and staging merge are directly reported; functional success is not shown.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C4.** In another report, a newly pruned narrative initially moved to Hidden and showed the pruning rule on hover; on a next-day revisit, the hover showed the narrative title instead.
  Sources: KEP-6419. Route: `memory`.
  Confidence: **high** — The report explicitly contrasts immediate behavior with a next-day revisit.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C5.** A retest ticket was recorded for the next-day hover-text issue; the available title does not establish its result.
  Sources: KEP-6431. Route: `memory`.
  Confidence: **medium** — The ticket title establishes a retest work item, not execution or outcome.
  - `ev_82dffd65d16997af` [0:66]: RETEST - Pruning Rule Hover Text Shows the Wrong Text The Next Day
- **C6.** A separate hidden-tab report says an existing rule-hidden narrative was present before another narrative was hidden; the new one moved correctly, but several narratives not hidden by the user also appeared in Hidden.
  Sources: KEP-6460. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The conditional report directly states the pre-existing state, subsequent hide action, and observed result.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
- **C7.** That hidden-tab issue was later marked resolved and Done in a ticket comment, though the cited text alone does not verify the corrected behavior.
  Sources: KEP-6460. Route: `memory`.
  Confidence: **medium** — The comment reports resolution and a status change, but no test result is included in the cited text.
  - `ev_556016c4f8f9dfec` [0:88]: This issue is resolved, moving the status to done. Please check the video attached below

## Unanswered

- The supplied source excerpts do not establish a reliable calendar order among the separate deletion, hover-text, and hidden-tab reports.
- The excerpts do not verify that the staging merge restored hidden narratives, that the hover retest passed, or that the hidden-tab fix worked in production.

## Limitations

- Within-report sequences are explicit; cross-ticket causal and date ordering is not established by the inferred graph links.
- The two hidden-tab evidence entries repeat the same passage and are not independent incidents.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
