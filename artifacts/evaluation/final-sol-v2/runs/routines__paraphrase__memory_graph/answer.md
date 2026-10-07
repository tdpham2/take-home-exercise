# What does the history say teams should routinely do for monitoring and QA, and what establishes actual execution or effectiveness?

Status: partial

- **C1.** For API health, the documented manual QA routine is to run the Postman collection twice daily, log failures or anomalies, and notify QA or a developer in Slack when failures persist.
  Sources: KT-292, KT-334. Route: `memory`.
  Confidence: **high** — Direct imperative and purpose wording in the original extracts.
  - `ev_72bcaf2a50c998b3` [0:209]: This is a manual QA activity to execute the Postman collection twice daily (morning and evening) throughout the month. The purpose is to monitor API health, validate responses, and identify any failures early.
  - `ev_916c116ecced7dd4` [0:68]: Log any failures, delays, or anomalies in the shared tracking sheet.
  - `ev_eaf6ee6af9edf403` [0:78]: Notify the QA group or developer in Slack if consistent failures are observed.
- **C2.** A data-validation routine calls for twice-daily checks of consistency, completeness, and anomalies, with a high-priority Slack alert if any monitored value is zero.
  Sources: KEP-6559. Route: `graph`.
  Confidence: **high** — The source directly states the cadence and alert rule.
  - `ev_9f543bc4c976ff23` [0:134]: This activity should be performed twice a day to ensure continuous monitoring of data consistency, completeness, and anomaly detection
  - `ev_12bedb14a8af7e0c` [0:78]: If any value = 0 , alert in #kepler-data-validation (Slack) with High Priority
- **C3.** Vendor usage and billing reviews are prescribed for Mondays and Thursdays: inspect usage, download patterns, traffic and spend contributors, and anomalies; then record observations and alert stakeholders about deviations.
  Sources: KEP-4256. Route: `memory`.
  Confidence: **high** — The checklist explicitly lists tasks and cadence.
  - `ev_03e71e671753e994` [0:548]: Checklist: [ ] Gather usage and billing statistics from both platforms. [ ] Review any changes in download patterns or target domain lists. [ ] Track top 10 domains or endpoints contributing to traffic/spend. [ ] Check for any abnormal spikes or cost anomalies. [ ] Raise an alert or tag stakeholders in case of any deviation from expected usage. [ ] Document observations in the vendor monitoring sheet or dashboard. This task should be completed every Monday and Thursday for proactive tracking and early detection of unexpected billing patterns.
- **C4.** The history includes bounded reports of actual QA execution: production validation for specified deployed items and validation of the Video Vision upload-and-analysis workflow.
  Sources: KEP-4271, KEP-7057. Route: `graph`.
  Confidence: **medium** — The extracts report completion but omit test artifacts, pass criteria, and the full item list.
  - `ev_2ce500dcaecf699e` [0:74]: QA has completed validation on Production for the following deployed items
  - `ev_bd5cb26d7310be88` [0:73]: QA completed validation for the Video Vision upload and analysis workflow
- **C5.** One production record reports a daily cron was set up; that establishes reported configuration, not successful daily execution or detection performance.
  Sources: KEP-2287. Route: `memory_confirmed_by_graph`.
  Confidence: **medium** — The extract directly reports configuration but supplies no run history or results.
  - `ev_07b02b3b9de41f0f` [0:35]: cron set on prod env on daily basis
- **C6.** A separate report-generation record explicitly notes failures alongside the absence of a regular QA run.
  Sources: KEP-6923. Route: `graph`.
  Confidence: **high** — The source directly states the gap in that workflow.
  - `ev_1ac3a7fb42bdf536` [0:47]: Report‑generation failures (no regular QA run).
- **C7.** To establish that a prescribed routine actually ran and worked, the available prescriptions and completion labels would need run logs or check results, alert-delivery and response records, and scoped validation outcomes against explicit criteria; the cited material does not supply those for the routine cadences.
  Sources: KEP-2287, KEP-4256, KT-292. Route: `memory`.
  Confidence: **medium** — This is an evidentiary distinction drawn from prescriptions, an unchecked checklist, and a configuration report, not a claim that no such artifacts exist anywhere.
  - `ev_72bcaf2a50c998b3` [0:209]: This is a manual QA activity to execute the Postman collection twice daily (morning and evening) throughout the month. The purpose is to monitor API health, validate responses, and identify any failures early.
  - `ev_03e71e671753e994` [0:548]: Checklist: [ ] Gather usage and billing statistics from both platforms. [ ] Review any changes in download patterns or target domain lists. [ ] Track top 10 domains or endpoints contributing to traffic/spend. [ ] Check for any abnormal spikes or cost anomalies. [ ] Raise an alert or tag stakeholders in case of any deviation from expected usage. [ ] Document observations in the vendor monitoring sheet or dashboard. This task should be completed every Monday and Thursday for proactive tracking and early detection of unexpected billing patterns.
  - `ev_07b02b3b9de41f0f` [0:35]: cron set on prod env on daily basis

## Unanswered

- Whether the twice-daily API and data checks or Monday/Thursday billing reviews occurred consistently.
- Whether alerts were delivered, acknowledged, and acted on, and whether monitoring reduced detection time or harm.
- The test cases, pass criteria, and results behind the bounded QA-completion reports.

## Limitations

- Repeated billing checklist text across records is not independent evidence of repeated execution.
- Configured scheduling and reported QA completion do not by themselves establish sustained operation or effectiveness.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
