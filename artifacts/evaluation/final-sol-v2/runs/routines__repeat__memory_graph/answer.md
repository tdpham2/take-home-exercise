# Which monitoring and QA activities are documented routines, and what evidence shows they were performed or effective?

Status: partial

- **C1.** Vendor usage and billing monitoring is prescribed for Mondays and Thursdays: gather statistics, review traffic patterns and top domains, check anomalies, alert stakeholders, and document observations.
  Sources: KEP-4256. Route: `memory`.
  Confidence: **high** — The source explicitly states the checklist and cadence.
  - `ev_03e71e671753e994` [0:548]: Checklist: [ ] Gather usage and billing statistics from both platforms. [ ] Review any changes in download patterns or target domain lists. [ ] Track top 10 domains or endpoints contributing to traffic/spend. [ ] Check for any abnormal spikes or cost anomalies. [ ] Raise an alert or tag stakeholders in case of any deviation from expected usage. [ ] Document observations in the vendor monitoring sheet or dashboard. This task should be completed every Monday and Thursday for proactive tracking and early detection of unexpected billing patterns.
- **C2.** Manual API QA is prescribed as a twice-daily Postman collection run, with failures logged in a shared sheet and consistent failures escalated in Slack.
  Sources: KT-292, KT-334. Route: `memory`.
  Confidence: **high** — The instructions directly specify cadence, logging, and escalation.
  - `ev_72bcaf2a50c998b3` [0:209]: This is a manual QA activity to execute the Postman collection twice daily (morning and evening) throughout the month. The purpose is to monitor API health, validate responses, and identify any failures early.
  - `ev_916c116ecced7dd4` [0:68]: Log any failures, delays, or anomalies in the shared tracking sheet.
  - `ev_eaf6ee6af9edf403` [0:78]: Notify the QA group or developer in Slack if consistent failures are observed.
- **C3.** A recorded morning vendor API run reported 56 of 57 BrightData tests passed and identified an Instagram Snapshot API monitor failure; this shows at least one test result was recorded, not that twice-daily runs were sustained or effective overall.
  Sources: KEP-6734. Route: `memory`.
  Confidence: **high** — The source directly reports a run result and a failed check.
  - `ev_bc2c6112db23bb6e` [0:57]: Vendor API runs (Morning) - BrightData API - 56/57 Passed
  - `ev_bc7d01297224ca42` [0:55]: Insta - Discover by url - Snapshot API monitor - Failed
- **C4.** Dashboard-based data validation is prescribed twice daily using Network Summary V1 and ES Data Collection Stats V1, with attention to two-plus days of greater-than-5% daily decline and high-priority Slack alerts for zero values.
  Sources: KEP-6559. Route: `memory`.
  Confidence: **high** — The source directly specifies the dashboards, cadence, and alert conditions.
  - `ev_12a71d32dc0dce15` [0:67]: using Network Summary V1 and ES Data Collection Stats V1 dashboards
  - `ev_9f543bc4c976ff23` [0:134]: This activity should be performed twice a day to ensure continuous monitoring of data consistency, completeness, and anomaly detection
  - `ev_a5524b6316553c2f` [0:103]: Condition to Monitor: ⚠️ Risky - Platforms with 2+ consecutive days of decline (day-over-day drop > 5%)
  - `ev_12bedb14a8af7e0c` [0:78]: If any value = 0 , alert in #kepler-data-validation (Slack) with High Priority
- **C5.** A production-monitoring record reports that post-deployment statistics were checked continuously for a background service, but supplies no metrics demonstrating performance improvement.
  Sources: KEP-3901. Route: `memory`.
  Confidence: **medium** — The source reports monitoring but gives no underlying measurements or check history.
  - `ev_42dddc41da53aded` [0:141]: Production has been monitored post deployment. Stats have been checked continuously for monitoring the performance of the background service.

## Unanswered

- No reviewed evidence establishes completion of every scheduled vendor review, every twice-daily API or dashboard check, or delivery of prescribed alerts.
- No reviewed measurements establish that these routines reduced incidents, improved service performance, or achieved a particular detection latency.

## Limitations

- Repeated checklist wording is not independent evidence of repeated execution.
- Administrative Done status does not verify execution, recovery, or effectiveness.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
