# Which monitoring and QA activities are documented routines, and what evidence shows they were performed or effective?

Status: partial

- **C1.** Production release monitoring is documented as part of a release checklist, alongside deployment and rollback plans.
  Sources: KEP-3037. Route: `text`.
  Confidence: **high** — The checklist is explicit.
  - `ev_84a32112342d490b` [0:117]: Production Release & Monitoring Includes Deployment plan Rollback plan Release notes Configuration changes documented
- **C2.** Data-validation monitoring is prescribed twice daily using the Network Summary V1 and ES Data Collection Stats V1 dashboards.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — The cadence and dashboards are stated directly.
  - `ev_9f543bc4c976ff23` [0:134]: This activity should be performed twice a day to ensure continuous monitoring of data consistency, completeness, and anomaly detection
  - `ev_12a71d32dc0dce15` [0:67]: using Network Summary V1 and ES Data Collection Stats V1 dashboards
- **C3.** The data-validation instructions flag platforms with more than a 5% day-over-day decline for at least two consecutive days.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — The threshold is explicit.
  - `ev_a5524b6316553c2f` [0:103]: Condition to Monitor: ⚠️ Risky - Platforms with 2+ consecutive days of decline (day-over-day drop > 5%)
- **C4.** The data-validation instructions call for a high-priority Slack alert when any monitored value is zero.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — The alert condition and destination are explicit.
  - `ev_12bedb14a8af7e0c` [0:78]: If any value = 0 , alert in #kepler-data-validation (Slack) with High Priority
- **C5.** A ticket reports that a monitoring cron was set on the production environment to run daily.
  Sources: KEP-2287. Route: `text`.
  Confidence: **high** — This is a direct configuration report.
  - `ev_07b02b3b9de41f0f` [0:35]: cron set on prod env on daily basis
- **C6.** Monitoring for long-running or stuck batches is proposed, rather than shown operating.
  Sources: KEP-6766. Route: `text`.
  Confidence: **high** — “Introduce” expresses a proposed action.
  - `ev_b4227410a8c3aa8e` [0:107]: Introduce a monitoring mechanism to detect and handle long-running or stuck batches to ensure SLA adherence
- **C7.** Staging QA for report generation is documented as a task, but its Done status does not demonstrate a test result.
  Sources: KEP-2840. Route: `text`.
  Confidence: **medium** — The task and administrative status are explicit; no result accompanies them.
  - `ev_45ac9b2dcf5e0d1f` [0:52]: QA Staging: Validate Report Generation Functionality
  - `ev_7eff0be2512c5620` [0:31]: resolution: Done | status: Done
- **C8.** A staging-and-production QA retest reported that a Narrative Hierarchy tooltip showed a Views value much larger than the API response for the hovered date.
  Sources: KEP-5622. Route: `text`.
  Confidence: **high** — The retest scope and observed comparison are stated directly.
  - `ev_31c2704adc3ea88a` [0:93]: Retest: 🐞QA: Staging & Prod: Narrative Hierarchy chart tooltip shows incorrect Views on hover
  - `ev_f851edaad47dde88` [0:94]: Tooltip shows a different (much larger) Views value than the API response for the hovered date
- **C9.** QA reported a pruning-rule hover that initially displayed the correct rule but displayed the narrative title when revisited the next day.
  Sources: KEP-6419. Route: `text`.
  Confidence: **high** — The passage describes the observed before-and-after behavior.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C10.** A report-generation check identified a potential discrepancy: the UI showed 50 posts for a stated range while the generated report said it analyzed 38.
  Sources: KEP-2929. Route: `text`.
  Confidence: **high** — The compared counts are stated directly as a potential issue.
  - `ev_96ce76253fd0f8e8` [0:250]: Potential Issue Identified: For the time range 22JAN–26FEB, the product UI shows 50 total posts. However, the generated report for a prompt that requests analysis of all posts and gives the same timeframe says: 'This report analyzes 38 unique posts…'
- **C11.** A product-contract review is reported as completed, with observations documented and recommendations shared on reliability, observability, alerting, and technical debt.
  Sources: KEP-6424. Route: `text`.
  Confidence: **high** — The passage directly reports review deliverables.
  - `ev_e307074eb986d857` [0:164]: Product contract reviewed end-to-end Observations documented in the attached document Recommendations shared for reliability, observability, alerting, and tech debt

## Unanswered

- Were the prescribed twice-daily dashboard checks actually performed, and on which dates?
- Did the production cron run successfully or generate actionable alerts?
- Were the detected QA discrepancies fixed and verified by passing retests?
- Did monitoring or QA measurably improve reliability or prevent customer impact?

## Limitations

- The passages contain instructions, task statuses, and selected observations, but no monitoring logs, alert history, test-run results, or outcome metrics.
- The selected QA defects demonstrate detection of particular issues, not the prevalence of defects or overall QA effectiveness.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
