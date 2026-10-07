# Which pruning behaviors and follow-up actions are reported, and what evidence supports their temporal order?

Status: partial

- **C1.** In KEP-6419, a newly pruned narrative moved to the hidden tab and initially showed its pruning rule on hover; the reporter said that on returning the next day, the hover showed the narrative title instead.
  Sources: KEP-6419. Route: `graph`.
  Confidence: **high** — The first-person report explicitly orders the immediate display before the next-day display.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C2.** A separate KEP-6431 record calls for a retest of the next-day pruning-rule hover text problem; it does not report a retest result.
  Sources: KEP-6431. Route: `graph`.
  Confidence: **high** — The title directly identifies a retest, but supplies no outcome.
  - `ev_82dffd65d16997af` [0:66]: RETEST - Pruning Rule Hover Text Shows the Wrong Text The Next Day
- **C3.** In KEP-5342, the reporter said a pruned narrative immediately entered Hidden Narratives but did not return to the main tab after its corresponding rule was deleted.
  Sources: Community_1210. Route: `graph`.
  Confidence: **high** — The report explicitly gives the order: prune, then delete the rule, then observe the failure to restore.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
- **C4.** KEP-4019 reports that a feature reflecting pruning-rule deletion in topic narratives was implemented and its merge request merged in staging; this is not proof that the restoration defect was resolved.
  Sources: KEP-4019. Route: `graph`.
  Confidence: **high** — The source directly reports implementation and a staging merge, but no verified behavioral outcome.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C5.** KEP-4050 identifies restoration to the main Narrative tab after rule deletion as a retest, not as a verified result.
  Sources: KEP-4050. Route: `graph`.
  Confidence: **high** — The record is expressly labeled a retest and uses prescriptive wording.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
- **C6.** KEP-5389 reports that deleting a pruning rule did not automatically refresh the UI, and KEP-5480 subsequently frames that issue as a retest; the records shown do not establish a passing result.
  Sources: KEP-5389, KEP-5480. Route: `graph`.
  Confidence: **medium** — The original defect and retest title support a reported follow-up sequence, not completion or success.
  - `ev_7e4519c3675b92f7` [0:69]: When a pruning rule is deleted, the UI does not refresh automatically
  - `ev_0038d1e815d621c1` [0:60]: Retest: Deleted Pruning Rule Does Not Sync Immediately on UI
- **C7.** KEP-6460 reports that hiding another narrative correctly moved that narrative to Hidden, but also made several narratives that were not hidden appear there.
  Sources: KEP-6460. Route: `graph`.
  Confidence: **high** — The report directly describes the prior hidden item, subsequent hide action, and unexpected additional entries.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
- **C8.** KEP-5759 reports that the system blocked pruning without an active token and states that pruning should instead depend on user permissions.
  Sources: KEP-5759. Route: `graph`.
  Confidence: **high** — The reported failure and desired rule are directly stated in the same record; the desired rule is not an observed fix.
  - `ev_1ad128968e343ee3` [0:126]: System blocks pruning when no active token is available. User cannot proceed with Hide / Flag action due to token restriction.
  - `ev_9decf1cbcbcc7d25` [0:123]: pruning capability should be restricted only based on user permissions (Viewer vs Editor) — not based on token availability
- **C9.** KEP-6413 reports a different token-related sequence: a user without tokens could create a prune rule and prune, but received a no-token error when attempting to delete that rule.
  Sources: KEP-6413. Route: `graph`.
  Confidence: **high** — The source explicitly orders creation and pruning before the failed deletion attempt; it should not be collapsed into KEP-5759's reported behavior.
  - `ev_ace0d087762ec7f6` [0:351]: Currently, when a user does not have available tokens , the user is still able to create a Narrative Prune Rule and prune narratives successfully . However, when the same user attempts to delete the created prune rule from the Agent Detail Page → Narrative Pruning section , the system shows an error message stating that the user does not have tokens
- **C10.** The KEP-6413 follow-up says token-check logic remained in the update and delete pruning-rule APIs and was removed; no post-removal test result is shown.
  Sources: KEP-6413. Route: `graph`.
  Confidence: **high** — The record reports a code change, not a verified user-facing recovery.
  - `ev_d42ebd7f985b5490` [0:94]: The Token check Logic was kept in updfation and delete pruning rules API's. We have removed it

## Unanswered

- What were the exact dated chronology and deployment status of the pruning fixes and retests? The cited original snippets lack verified timestamps and passing results.
- Did deletion restore previously hidden narratives, and did hover text remain correct after the next day following the retests?
- Why do KEP-5759 and KEP-6413 describe different no-token behavior? The excerpts do not establish whether their environments, versions, or paths differed.
- Was the KEP-6460 hidden-tab duplication fixed and verified?

## Limitations

- Temporal order is strongest within first-person reports and in records expressly labeled retest; ticket numbers and graph edges do not independently prove chronology or causality.
- A staging merge or reported code change is not evidence of production deployment, successful QA, or customer impact.
- The cited reports describe selected cases, not the prevalence of pruning defects.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
