# What does the history say teams should routinely do for monitoring and QA, and what establishes actual execution or effectiveness?

Status: partial

- **C1.** QA should check that chat history remains specific to the selected network, including after a meta-agent query.
  Sources: KEP-6579. Route: `text`.
  Confidence: **high** — The passages explicitly state QA checks.
  - `ev_15bdf5a436847088` [0:155]: As a QA tester, when I test the chat history management, I want to ensure that network A cannot see network B's history so that data privacy is maintained.
  - `ev_2108cead365df520` [0:161]: As a QA tester, when I access chat history from the dashboard, I want to confirm the history remains network-specific after a query triggers from the meta agent.
- **C2.** QA should also test cross-network actions from chat history: a production QA report says accounts or sources could be added to the currently open network rather than the network where the chat originated.
  Sources: KEP-6429. Route: `text`.
  Confidence: **medium** — The reported defect directly supports this QA focus, but the routine recommendation is a synthesis.
  - `ev_02824c23f9963f4f` [0:89]: RETESTING - 🪲QA: prod : Accounts/Sources from Chat History get added to the wrong network
  - `ev_9472a4c8aa1f432d` [0:144]: The account/source gets added to the currently open network (Network B) instead of the original network (Network A) where the chat was generated
- **C3.** QA should test that switching chat histories clears stale Add Account suggestions.
  Sources: KEP-6432. Route: `text`.
  Confidence: **high** — The expected behavior is stated directly.
  - `ev_c392133930f7643c` [0:182]: The Add Account panel should only display account suggestions related to the currently opened chat history , and any previous history data should be cleared when switching histories.
- **C4.** For privacy-sensitive monitoring, the record identifies verbose observability and logging as an exposure concern, particularly detailed CA execution context.
  Sources: KEP-6793. Route: `text`.
  Confidence: **high** — The concern is explicitly reported.
  - `ev_7778294f2b79271d` [0:60]: observability/logging is currently the largest exposure path
  - `ev_bf0b962c02eb9f84` [0:90]: CA is the primary concern: logging is very verbose and includes detailed execution context
- **C5.** The moderation record calls for evaluating the OpenAI Moderation API's effectiveness and performance in detecting unsafe content.
  Sources: KEP-6733. Route: `text`.
  Confidence: **high** — The evaluation need is explicit.
  - `ev_2d07c3633d4fdf58` [0:111]: We need to evaluate the effectiveness and performance of the OpenAI Moderation API for detecting unsafe content
- **C6.** The production QA API-suite summary reports an execution on 2026-05-13: 215 tests, 208 passed, and 7 failed.
  Sources: KEP-7078. Route: `text`.
  Confidence: **high** — A dated execution summary supplies counts and environment.
  - `ev_4a2fbd0945ff738e` [0:136]: Prod API Suite Execution Result: QA-API-Suite — Production Execution Summary (2026-05-13) Total Tests: 215 | ✅ Passed: 208 | ❌ Failed: 7
- **C7.** A QA note reports seeing network-specific chat history and says new network chat history was working, while also reporting a PDF-download bug.
  Sources: KEP-6579. Route: `text`.
  Confidence: **high** — These are direct QA observations with a stated remaining bug.
  - `ev_4a6e925afa46e1d6` [0:48]: I can see chat history specific to networks now.
  - `ev_97ba21303787884b` [0:71]: New chat history for networks is working. Raised bug for pdf download -
- **C8.** A staging-environment QA note reports that a Narrative image was working there after a broken-image report.
  Sources: KEP-5451. Route: `text`.
  Confidence: **high** — The passages directly report the defect and a staging observation.
  - `ev_4487f5d076bd9041` [0:86]: A broken image icon is displayed in the Narrative section instead of the actual image.
  - `ev_a6bcd74ea646c69c` [0:32]: It's working on staging env now.
- **C9.** A ticket marked Done is not, by itself, evidence that the reported cross-network account/source issue was fixed or that retesting passed.
  Sources: KEP-6429. Route: `text`.
  Confidence: **medium** — The supplied status and retesting label do not include a passing result.
  - `ev_2509c7cf9fccbd58` [0:31]: resolution: Done | status: Done
  - `ev_02824c23f9963f4f` [0:89]: RETESTING - 🪲QA: prod : Accounts/Sources from Chat History get added to the wrong network

## Unanswered

- The passages do not specify a monitoring or QA cadence, named owners, alert thresholds, or a comprehensive routine checklist.
- No supplied result establishes the effectiveness of the OpenAI Moderation API evaluation.
- The supplied passages do not establish resolution of the seven failed production API-suite tests or sustained production effectiveness.

## Limitations

- Expected results and test intentions are not evidence of execution.
- The records cover distinct systems and environments; staging observations and AIR issues should not be treated as Kepler production outcomes.
- BM25 over extracted record text; exact citations do not establish semantic correctness.
