# What changes in narrative pruning behavior and remediation are documented, and how confidently can they be ordered?

Status: partial

- **C1.** A reported pruning action moved a narrative to Hidden, but deleting its rule did not restore it to the main Narrative tab.
  Sources: Community_1210. Route: `memory`.
  Confidence: **high** — The source directly reports both actions and results.
  - `ev_1db77eef58ddea9b` [0:217]: When I prune a Narrative, it immediately moves to the Hidden Narratives tab. However, when I delete the corresponding pruning rule from the Agent Details page, the Narrative does not reappear in the main Narrative tab
- **C2.** The stated requirement was to unhide affected narratives or return them to the main tab when their pruning rule was deleted.
  Sources: KEP-4019. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The required behavior is explicit.
  - `ev_2c6bc75694fac331` [0:125]: When deleting a pruning rule, related narratives which are in hidden must get un-hidden or appear in Main narrative tab again
- **C3.** A remediation report says a feature reflecting pruning-rule deletion was implemented and its merge request merged in staging.
  Sources: KEP-4019. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The implementation and staging-merge report is direct.
  - `ev_f2d83729fd1a8334` [0:118]: Implemented Feature to reflect narrative pruning rule deletion in topic narratives. MR , we have merged in staging ENV
- **C4.** A restoration retest was documented and testing was reported complete, but these excerpts do not state a pass result.
  Sources: KEP-4050. Route: `memory`.
  Confidence: **high** — The excerpts explicitly identify a retest and testing completion, but not its outcome.
  - `ev_4ed85e54eaab7297` [0:76]: Retest - Deleted Pruning Rule should Restore Narrative to Main Narrative Tab
  - `ev_1d3ba24c5a1d0d02` [0:26]: Testing fo this is complet
- **C5.** A distinct deletion report says the pruning-rules UI did not refresh automatically; the stated expectation was immediate removal from the All filter.
  Sources: KEP-5389. Route: `memory`.
  Confidence: **high** — The defect report and expectation are explicit.
  - `ev_7e4519c3675b92f7` [0:69]: When a pruning rule is deleted, the UI does not refresh automatically
  - `ev_fed8eeb168f5a736` [0:58]: Deleted rule should disappear immediately from: All filter
- **C6.** Another report says hiding a new narrative correctly moved it to Hidden while unrelated narratives also appeared there.
  Sources: KEP-6460. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The behavior is directly reported.
  - `ev_8f9034d5d62be1cd` [0:357]: If the UI section for "hidden narratives" already contains a hidden narrative (for example, if I created a pruning rule yesterday and the system hid a narrative automatically), and I hide another narrative, the new narrative correctly moves to the Hidden tab. However, several other narratives also appear in the Hidden tab even though they were not hidden.
- **C7.** The Hidden-tab issue was reported resolved and moved to Done, without independently verified resulting behavior in the cited excerpt.
  Sources: KEP-6460. Route: `memory`.
  Confidence: **high** — The closure statement is direct, but its referenced video was not inspected.
  - `ev_556016c4f8f9dfec` [0:88]: This issue is resolved, moving the status to done. Please check the video attached below

## Unanswered

- Exact dates and relative order of the restoration, UI-refresh, and Hidden-tab defects.
- Whether the staging implementation passed the restoration retest or reached production.
- Whether the UI-refresh defect was fixed and the Hidden-tab closure reflected verified behavior.

## Limitations

- The inferred CAUSES passage asserting dates and a direct trigger is not original source testimony and cannot establish chronology or causality.
- The source securely orders pruning before rule deletion within one reported workflow; it does not establish an overall cross-defect timeline.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
