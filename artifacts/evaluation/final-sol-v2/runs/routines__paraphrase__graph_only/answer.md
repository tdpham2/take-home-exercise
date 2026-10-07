# What does the history say teams should routinely do for monitoring and QA, and what establishes actual execution or effectiveness?

Status: partial

- **C1.** For vendor monitoring, the checklist calls for twice-weekly review of usage, billing, traffic drivers and anomalies, with alerts and documented observations.
  Sources: KEP-4256. Route: `graph`.
  Confidence: **high** — The source explicitly states the checklist and cadence.
  - `ev_03e71e671753e994` [0:548]: Checklist: [ ] Gather usage and billing statistics from both platforms. [ ] Review any changes in download patterns or target domain lists. [ ] Track top 10 domains or endpoints contributing to traffic/spend. [ ] Check for any abnormal spikes or cost anomalies. [ ] Raise an alert or tag stakeholders in case of any deviation from expected usage. [ ] Document observations in the vendor monitoring sheet or dashboard. This task should be completed every Monday and Thursday for proactive tracking and early detection of unexpected billing patterns.
- **C2.** Another monitoring rule specifies a daily Active Network Stats validation check after the enrichment check.
  Sources: KEP-4172. Route: `graph`.
  Confidence: **medium** — The cadence is explicit; its subject comes from the associated rule label, which is unverified.
  - `ev_4d594d265b46ec88` [0:79]: Check Frequency: Once daily (after the enrichment check, ideally after 5pm IST)
- **C3.** A batch-lifecycle plan calls for status and age metrics, dashboards and alerts; this establishes an observability requirement, not implementation.
  Sources: KEP-5668. Route: `graph`.
  Confidence: **high** — The passage directly lists the proposed metrics and alerting.
  - `ev_d55e5ad81b4d1b98` [0:225]: Observability & Dashboards Expose metrics such as: Number of active batches Count of batches per status ( sent , completed , failed , etc.) Age distribution of sent batches Create dashboards and alerts based on these metrics.
- **C4.** QA guidance includes unit tests for video-analysis upload validation, including file limits, MIME types, concurrency and ownership checks.
  Sources: KEP-6913. Route: `graph`.
  Confidence: **high** — The test scope is stated directly.
  - `ev_4b28b4f82761e395` [0:151]: Unit tests ( tests/unit/test_video_analysis_*.py ) Validation: file size cap, MIME allowlist, per-chat concurrency, ownership of chat_id / network_id .
- **C5.** Recorded QA summaries provide stronger evidence of execution: one staging sanity run reports 33 queries, 24 passed and 9 failed; a production API suite summary reports 215 tests, 208 passed and 7 failed.
  Sources: KEP-2809, KEP-7078. Route: `graph`.
  Confidence: **high** — Both passages explicitly report environment-specific run totals and failures.
  - `ev_84c5dad01abf5e69` [0:146]: Sanity Test Results – Big Agent Kepler Staging Environment | 13.01.26 Queries Run: 33 Queries Passed: 24 Queries Failed: 9 Pass Percentage: 72.73%
  - `ev_4a2fbd0945ff738e` [0:136]: Prod API Suite Execution Result: QA-API-Suite — Production Execution Summary (2026-05-13) Total Tests: 215 | ✅ Passed: 208 | ❌ Failed: 7

## Unanswered

- Were the prescribed monitoring checks performed consistently, and what anomalies, alerts or responses were recorded?
- Were the cited QA failures fixed and verified by reruns or post-release monitoring?

## Limitations

- Checklists, test plans, ticket titles and administrative completion do not prove execution or effectiveness.
- The shown QA summaries concern distinct staging and production test suites and should not be combined into one trend.
- Citation validation checks source access and exact provenance, not semantic entailment or real-world truth.
