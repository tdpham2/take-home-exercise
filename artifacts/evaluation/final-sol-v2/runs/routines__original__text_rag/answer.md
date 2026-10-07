# Which monitoring and QA activities are documented routines, and what evidence shows they were performed or effective?

Status: partial

- **C1.** Data-consistency monitoring is documented as a twice-daily activity, not shown here as twice-daily execution.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — The passage directly specifies the intended frequency.
  - `ev_9f543bc4c976ff23` [0:134]: This activity should be performed twice a day to ensure continuous monitoring of data consistency, completeness, and anomaly detection
- **C2.** The documented check uses the Network Summary V1 and ES Data Collection Stats V1 dashboards and flags platforms with at least two consecutive days of declines exceeding 5% day over day.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — Both the dashboards and condition are explicitly named.
  - `ev_12a71d32dc0dce15` [0:67]: using Network Summary V1 and ES Data Collection Stats V1 dashboards
  - `ev_a5524b6316553c2f` [0:103]: Condition to Monitor: ⚠️ Risky - Platforms with 2+ consecutive days of decline (day-over-day drop > 5%)
- **C3.** The monitoring instructions call for a high-priority Slack alert when any checked value is zero.
  Sources: KEP-6559. Route: `text`.
  Confidence: **high** — The alert condition and channel are explicit.
  - `ev_12bedb14a8af7e0c` [0:78]: If any value = 0 , alert in #kepler-data-validation (Slack) with High Priority
- **C4.** A separate record reports that a daily cron was set in production.
  Sources: KEP-2287. Route: `text`.
  Confidence: **high** — This is a direct report of setup.
  - `ev_07b02b3b9de41f0f` [0:35]: cron set on prod env on daily basis
- **C5.** Production release documentation lists a deployment plan, rollback plan, release notes, and configuration changes under release and monitoring.
  Sources: KEP-3037. Route: `text`.
  Confidence: **high** — The listed items appear directly in the passage.
  - `ev_84a32112342d490b` [0:117]: Production Release & Monitoring Includes Deployment plan Rollback plan Release notes Configuration changes documented
- **C6.** Monitoring for long-running or stuck batches is proposed, rather than evidenced as operating.
  Sources: KEP-6766. Route: `text`.
  Confidence: **high** — The imperative wording describes an intended mechanism.
  - `ev_017e38b2a29f5b29` [0:83]: Introduce a monitoring mechanism to detect and handle long-running or stuck batches
- **C7.** Staging QA for report generation is documented as a task marked Done, but the supplied passages contain no test result.
  Sources: KEP-2840. Route: `text`.
  Confidence: **medium** — The task and administrative status are explicit, but neither is a test log.
  - `ev_45ac9b2dcf5e0d1f` [0:52]: QA Staging: Validate Report Generation Functionality
  - `ev_7eff0be2512c5620` [0:31]: resolution: Done | status: Done
- **C8.** A staging-and-production QA retest reported that a Narrative Hierarchy tooltip's Views value was much larger than the API response for the hovered date.
  Sources: KEP-5622. Route: `text`.
  Confidence: **high** — The retest and observed discrepancy are directly reported.
  - `ev_31c2704adc3ea88a` [0:93]: Retest: 🐞QA: Staging & Prod: Narrative Hierarchy chart tooltip shows incorrect Views on hover
  - `ev_f851edaad47dde88` [0:94]: Tooltip shows a different (much larger) Views value than the API response for the hovered date
- **C9.** A pruning-rule hover check reported that the correct rule appeared immediately but was replaced by the narrative title on returning the next day.
  Sources: KEP-6419. Route: `text`.
  Confidence: **high** — The passage directly describes the immediate and later observations.
  - `ev_df451649650f6041` [0:443]: Current behavior: When I add a new pruning rule, the narrative that gets pruned goes to the hidden tab and immediately shows a hover indicating which rule was used. In other words, if I hover over the speech bubble with the three dots of a pruned narrative, it correctly displays the rule that pruned the narrative. However, if I return the next day, the hover no longer shows the pruning rule. Instead, it displays the title of the narrative.
- **C10.** A report-generation comparison identified 50 posts in the UI but 38 unique posts in the generated report for the stated timeframe.
  Sources: KEP-2929. Route: `text`.
  Confidence: **high** — The comparison and counts are directly reported.
  - `ev_96ce76253fd0f8e8` [0:250]: Potential Issue Identified: For the time range 22JAN–26FEB, the product UI shows 50 total posts. However, the generated report for a prompt that requests analysis of all posts and gives the same timeframe says: 'This report analyzes 38 unique posts…'

## Unanswered

- Were the twice-daily dashboard checks actually performed, and are there dated check records or sent alerts?
- Did the production cron run successfully, and what did it detect?
- What were the staging report-generation test results beyond the Done status?
- Were the reported QA defects fixed and verified by passing retests?

## Limitations

- The supplied passages establish documented routines, one reported cron setup, and specific defect observations; they do not establish overall monitoring or QA effectiveness.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
