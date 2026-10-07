# Which monitoring and QA activities are documented routines, and what evidence shows they were performed or effective?

Status: partial

- **C1.** A manual API-health QA routine calls for running a Postman collection morning and evening, logging anomalies, and escalating persistent failures; the stated cadence is a prescription, not proof of every scheduled run.
  Sources: KEP-6734, KT-292. Route: `graph`.
  Confidence: **high** — The source directly states the routine and its instructions.
  - `ev_72bcaf2a50c998b3` [0:209]: This is a manual QA activity to execute the Postman collection twice daily (morning and evening) throughout the month. The purpose is to monitor API health, validate responses, and identify any failures early.
  - `ev_ee0180a483ae2552` [0:68]: Log any failures, delays, or anomalies in the shared tracking sheet.
  - `ev_f4a9d67680ff4f6d` [0:78]: Notify the QA group or developer in Slack if consistent failures are observed.
- **C2.** One recorded morning vendor-API run reported 56 of 57 tests passed and a failed Instagram Snapshot API monitor check, showing at least one execution and detection, not sustained effectiveness.
  Sources: KEP-6734. Route: `graph`.
  Confidence: **high** — The source reports a concrete run result and named failure.
  - `ev_bc2c6112db23bb6e` [0:57]: Vendor API runs (Morning) - BrightData API - 56/57 Passed
  - `ev_bc7d01297224ca42` [0:55]: Insta - Discover by url - Snapshot API monitor - Failed
- **C3.** A separate production API-suite execution summary reports 215 tests, 208 passed and 7 failed; this documents a test run, not a fully passing production system.
  Sources: KEP-7078. Route: `graph`.
  Confidence: **high** — The summary directly supplies environment and counts.
  - `ev_4a2fbd0945ff738e` [0:136]: Prod API Suite Execution Result: QA-API-Suite — Production Execution Summary (2026-05-13) Total Tests: 215 | ✅ Passed: 208 | ❌ Failed: 7
- **C4.** A monitoring instruction calls for twice-daily checks of data consistency, completeness and anomalies; it does not itself show that those checks were carried out.
  Sources: KEP-6559. Route: `graph`.
  Confidence: **high** — The modal 'should' makes this an explicit instruction.
  - `ev_9f543bc4c976ff23` [0:134]: This activity should be performed twice a day to ensure continuous monitoring of data consistency, completeness, and anomaly detection
- **C5.** Network-health monitoring documentation describes regular trend analysis, including a below-minus-five-percent daily decline threshold and a two-consecutive-day decline condition.
  Sources: KEP-5056, KEP-6559. Route: `graph`.
  Confidence: **medium** — The source describes a practice and thresholds, but gives no run log here.
  - `ev_0fb05ff1366c34b2` [0:104]: Trend analysis is performed on a regular basis to monitor network health and identify critical declines.
  - `ev_02dbb530e1bbd728` [0:44]: Daily decline threshold: < -5.0% → Declining
  - `ev_a5524b6316553c2f` [0:103]: Condition to Monitor: ⚠️ Risky - Platforms with 2+ consecutive days of decline (day-over-day drop > 5%)
- **C6.** A vendor-usage and billing checklist prescribes gathering statistics, reviewing traffic and spend changes, alerting on anomalies, and documenting observations every Monday and Thursday; its unchecked boxes do not establish completion.
  Sources: KEP-4256. Route: `graph`.
  Confidence: **high** — The checklist and cadence are directly stated.
  - `ev_03e71e671753e994` [0:548]: Checklist: [ ] Gather usage and billing statistics from both platforms. [ ] Review any changes in download patterns or target domain lists. [ ] Track top 10 domains or endpoints contributing to traffic/spend. [ ] Check for any abnormal spikes or cost anomalies. [ ] Raise an alert or tag stakeholders in case of any deviation from expected usage. [ ] Document observations in the vendor monitoring sheet or dashboard. This task should be completed every Monday and Thursday for proactive tracking and early detection of unexpected billing patterns.
- **C7.** A production background-service record says production was monitored after deployment and its performance statistics checked continuously; it reports performance observation but no quantitative effectiveness result.
  Sources: KEP-3901. Route: `graph`.
  Confidence: **medium** — Direct source report of monitoring, without metrics or independent verification.
  - `ev_42dddc41da53aded` [0:141]: Production has been monitored post deployment. Stats have been checked continuously for monitoring the performance of the background service.
- **C8.** Staging Big Agent sanity-test results document actual QA runs with failures: one summary reports 20 queries, 15 passed and 5 failed; another reports 33 queries, 24 passed and 9 failed.
  Sources: KEP-2735, KEP-2809. Route: `graph`.
  Confidence: **high** — Both excerpts directly report staging test counts and failures.
  - `ev_202f2a527a68fc12` [0:195]: Sanity Test Results – Big Agent Kepler Staging Environment | 08.01.26 Queries Run: 20 Queries Passed: 15 Queries Failed: 5 Majority failures observed in comment stance queries Pass Percentage:75%
  - `ev_84c5dad01abf5e69` [0:146]: Sanity Test Results – Big Agent Kepler Staging Environment | 13.01.26 Queries Run: 33 Queries Passed: 24 Queries Failed: 9 Pass Percentage: 72.73%
- **C9.** The reliability-SOP source identifies report-generation failures as a concern and explicitly notes 'no regular QA run,' countering any inference that routine report QA was established merely because QA tasks exist.
  Sources: KEP-6923. Route: `memory_confirmed_by_graph`.
  Confidence: **high** — The source explicitly states the gap.
  - `ev_1ac3a7fb42bdf536` [0:47]: Report‑generation failures (no regular QA run).

## Unanswered

- No complete run logs, compliance rates, detection-to-resolution times, or before/after reliability measures were shown for the twice-daily and Monday/Thursday routines.
- The cited report-QA gap is not accompanied by evidence establishing when, or whether, a regular report-generation QA run was later implemented.

## Limitations

- Repeated checklist passages in different records may be reused wording rather than independent executions.
- Administrative Done status and stated monitoring purposes were not treated as proof of effectiveness.
- Staging sanity tests, production API tests, vendor API monitoring, and background-service monitoring concern distinct scopes; their results should not be pooled into one success rate.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
