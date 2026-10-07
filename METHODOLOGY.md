# An Organizational Memory and the Agent That Uses It

Artifact paths below refer to the local evaluation workspace. The selected submission
memory combines a Luna-built base with an Astra-generated pattern layer, saved
in `artifacts/memory/`. Historical pilots, comparisons and unfinished evaluation
outputs are not part of the initial source-code commit.

Author: Thang Pham.

This work is co-authored with a Codex coding assistant.

I use deterministic proposals followed by LLM judgments to build traceable organizational memory, then give an agent separate tools for that memory and its source graph. The completed Task 1 workflow preserves original evidence, selects episodes and facts for recall, and adds a separate layer of inferred patterns. The [Task 2 methodology](#task-2-agent-methodology) describes how the agent uses that memory and how its answers are evaluated. Completing and validating memory construction does not establish semantic correctness or downstream usefulness.

## Task 1. Organizational Memory Methodology

### 2.1. Evidence and facts

*Figure 1. Workflow for evidence and facts creation.*

**Preserve the evidence.** I index the supplied graph's 3,098 nodes and 4,051 edges, preserving original excerpts, node IDs, record IDs and provenance. The archive contains 3,239 extracted edges and 812 inferred edges. Extracted passages provide potential factual support; inferred relationships remain contextual hypotheses. All evidence remains available, including material excluded from recall.

**Generate proposals using deterministic rules.** Each decision node starts as an episode candidate. Code joins decisions through nonempty extracted `DEPENDS_ON` or `CAUSES` links, or a shared event within one record, with a maximum of eight decisions per group. Shared resources and inferred links do not trigger grouping. Starting with 990 decisions, 148 successful dependency joins and 17 shared-event joins produce 825 candidates. Of these, 816 contain extracted evidence and qualify for review; nine inferred-only candidates remain archived. Each candidate contains all evidence attached to its decisions across records.

Separately, each nonempty extracted excerpt becomes a fact proposal scoped to the edge's target node. Identical text/subject pairs share one proposal while retaining every reference, producing 2,911 fact proposals. Extracted `PRODUCES` edges generate 791 outcome proposals. Narrow guards exclude whole excerpts consisting only of administrative fields, such as closure status or epic links, without filtering those words out of substantive prose. These guards reject 669 fact proposals and mark 569 closure-only outcomes unobserved, leaving 2,242 facts and 222 outcomes for model judgment.

**Use the LLM to judge the proposals.** The model, `gpt-5.6-luna`, evaluates episode coherence and memory value separately. For facts, it judges whether the entire excerpt supports useful knowledge about the proposed subject, classifying accepted passages as historical statements, requirements or documented routines. For outcomes, it judges whether an actual result was reported, its direction and its supported impact scope. An observed outcome means that the source reports a result; it does not mean that the result was independently verified. Facts are judged independently of episode acceptance.

The model returns structured judgments and short reasons. It cannot rewrite quotations, extract smaller subclaims, or split and merge episode candidates. Accepting an episode does not verify every attached graph label or causal relationship. In the completed run, its judgments supported 653 episodes and accepted 1,086 facts.

**Construct memory from the judgments.** Code creates stable IDs, exact quotations, citations, membership and retention states. Of the 653 supported episodes, the LLM judged 547 worth remembering and 106 low-value. Code retains 547 for default recall and marks 106 as `compressed`. Compression preserves their excerpts and excludes them from default recall; it does not shorten or delete the archived evidence. Accepted facts enter default recall independently. Rejected proposals remain archived with reasons, and all 791 outcome assessments remain inspectable, including unknown results.

**Validate, checkpoint and support recall.** Validation checks source fidelity, judgment coverage and consistency between judgments and constructed items. It cannot establish semantic correctness. Production uses one candidate and its assigned fact and outcome proposals per initial call, with cached judgments and checkpoints supporting recovery. Completed, validated builds publish base memory (`artifacts/hosted/codex/gpt-5.6-luna/judge-v1/production-batch1/memory.json`, local artifact); the validation report (`artifacts/hosted/codex/gpt-5.6-luna/judge-v1/production-batch1/validation.json`, local artifact) records the structural checks.

Recall combines BM25 lexical matching, supplied node-vector associations and shared-entity expansion, with common hubs discounted. Because the supplied embedding encoder is unknown, query vectors are derived from lexically matched graph nodes. Recall therefore still depends on finding useful lexical anchors. Pattern abstraction runs as the separate downstream stage described next.

### 2.2. Abstraction

*Figure 2. Workflow for the abstraction process, starting from the base memory obtained in §2.1.*

**Start from the completed memory.** I validate and fingerprint the completed base memory before abstraction begins. This fixes the evidence and judgments available to the run and prevents changed inputs from silently reusing earlier results. The base contains 653 episodes, 1,086 accepted facts and 4,051 evidence records. Abstraction preserves these items and adds a separate pattern layer; it does not revise earlier judgments or repair episode boundaries.

**Prepare source evidence for comparison.** Code selects nonempty extracted passages, excludes inferred relationships and narrow administrative text, and deduplicates identical excerpts while retaining their original references. It groups passages associated with retained episodes and adds accepted-fact evidence not already covered by those episodes. This produces 697 evidence bundles: 547 associated with retained episodes and 150 containing additional fact evidence. The model receives original excerpts, source references and fact-kind annotations. Generated summaries and graph labels do not become independent factual support.

**Select evidence using explicit questions.** Four [configured areas](config/abstraction_questions.json) guide discovery: reliability, data consistency, operational routines, and narrative/pruning. They draw on the Task 2 example questions. Each area has a natural-language question for the LLM and keyword cues for deterministic retrieval. The questions ask for comparison without supplying an expected pattern. BM25 scores each bundle's text against the cues, and every positive-scoring bundle qualifies for selection. The highest-scoring remaining bundle starts a packet; code then adds related bundles using shared resource entities and word overlap, with rarer shared entities receiving more weight.

Each packet contains up to 18 primary bundles and two related retained-episode bundles for context. Context bundles can contribute qualifications or counterexamples even when they do not match the question's cues. A 100,000-character limit bounds serialized packet size; oversized packets lose context first and are split if necessary. A single bundle that still exceeds the limit is reported rather than silently truncated.

The completed run selected 293 distinct bundles as primary evidence across 23 packets. A bundle can appear in more than one question area, and context can reuse evidence. The 697 prepared bundles therefore do not represent 697 reviewed or independent occurrences. The [coverage report](artifacts/memory/coverage.json) records selected, processed, contextual and omitted evidence. Lexical selection can miss relevant passages that use different vocabulary.

**Use the LLM to compare occurrences.** Each packet receives one independent synthesis call to `gpt-6-astra`. The model may propose zero to three abstractions: a reported recurrence, a hypothesized mechanism, or a prescribed routine. Each proposal must cite supplied passage IDs, classify its support, explain what comparison adds, describe differences or counterevidence, state uncertainty, and explain its practical usefulness. Instructions distinguish requirements from execution and tentative explanations from established causality. The model can abstain when comparison adds no useful insight. Selected evidence cannot establish prevalence or the absence of counterexamples.

**Construct and admit traceable patterns.** Code checks the response schema, citation membership, support labels and statement length. Reported recurrences require support labeled as reported occurrences; prescribed routines require prescription support. Passages annotated exclusively as requirements or routines cannot establish execution, although those base annotations are themselves fallible.

Each proposal must have at least two conservatively independent support groups. Shared records, decisions, events or repeated passages connect overlapping evidence so that multiple excerpts from one occurrence do not automatically count as recurrence. All references retained during deduplication participate in this check; a shared generic resource alone does not connect support groups. This is a structural proxy for independent occurrences, not proof that the boundaries are correct.

Code removes exact duplicate statements within the same category, flags substantial wording overlap, and constructs admitted patterns with stable IDs, exact quotations and links to supporting episodes and facts. All pattern claims remain marked inferred with low heuristic confidence. That confidence is not a calibrated probability. The [completed schema 3.1 memory](artifacts/memory/memory.json) adds the pattern layer while preserving the schema 3.0 base items and judgments.

**Preserve rejected proposals and inspect usefulness.** The Astra run produced 68 proposals across 23 calls: 46 passed admission and 22 were rejected. Rejected proposals retain their text, references and reasons in the [rejection report](artifacts/memory/rejected_proposals.json). The [inspection examples](artifacts/memory/inspection_examples.json) pair proposals with supplied passages, and the [validation report](artifacts/memory/validation.json) records structural consistency.

Caching and checkpoints support recovery, while one limited correction request can repair a malformed response. Structurally invalid proposals are rejected without another semantic judgment pass. The [recall comparison](artifacts/memory/recall_comparison.json) provides additional inspection questions using the same base with and without patterns. Its questions have no independently labeled relevance judgments, so this is an inspection aid. Admission counts, valid citations and retrieval changes do not establish semantic accuracy or downstream usefulness.

### 2.3. Explanation of design choices

**LLM model choice.** For these Task 1 runs, I used the Codex SDK with Codex subscription access to keep full-dataset review practical within the take-home budget. For evidence and fact judgments, I used `gpt-5.6-luna` with medium reasoning. For abstraction, I used `gpt-6-astra`, also with medium reasoning. The choices reflected the available budget and the number of calls required for each task. The reported construction counts are not model-accuracy measurements.

**One semantic review pass.** Each initial base-memory call reviews one candidate episode together with its assigned fact and outcome proposals. Sharing context avoids separate calls for closely related judgments. I omitted iterative splitting, merging and rejudging to keep cost and execution predictable. Limited correction requests handle malformed or missing verdicts. The trade-off is that the model can reject an unsuitable boundary but cannot repair it. Whole-excerpt fact selection similarly simplifies citation checking but can lose useful subclaims when a passage mixes observation, speculation and intent.

**Batch size 1.** In the six-candidate pilot, reviewing candidates individually produced better judgments on several inspected cases, including administrative episodes and unsupported recovery claims. It used 36,523 tokens and 70.13 seconds of build time, compared with 22,024 tokens and 47.31 seconds for batch size 3: approximately 66% more tokens and 48% more build time. I accepted that cost for production while treating the result as limited development evidence, rather than a general accuracy finding. The batch-1 pilot (`artifacts/hosted/codex/gpt-5.6-luna/judge-v1/pilot-batch1/memory.json`, local artifact) and batch-3 pilot (`artifacts/hosted/codex/gpt-5.6-luna/judge-v1/pilot/memory.json`, local artifact) preserve the judgments and reported usage.

**Rules for structural safeguards; the LLM for interpretation.** Code preserves quotations, constructs provenance and excludes narrow administrative formats. Consequently, all 569 closure-only outcome proposals receive unobserved judgments with unknown direction and impact. The LLM handles contextual questions such as whether a supported statement is worth remembering, whether an instruction describes a routine, and whether “Test Pass” actually demonstrates a harmful defect.

For observed outcomes with a supported direction and scope, code assigns beneficial/harmful signs of +1/−1 and local/service/customer scope weights of 1/2/3. Their product is an ordinal comparison; mixed or unknown results remain unscored. These weights do not measure business value or prove causality. Retention similarly selects material for recall without implementing age-based forgetting or automatically updating old facts.

**Preserve uncertainty instead of silently repairing the graph.** Original IDs, excerpts and relationships remain available for audit. Inferred relationships cannot directly establish facts, observed outcomes or episode boundaries, and supersession edges do not automatically erase previous memory. The [data-understanding audit](DATA_UNDERSTANDING.md) connects concrete extraction problems to these safeguards and their limits.

The design prevents several graph errors from automatically becoming accepted memory. Closure-only evidence such as `status: Done` does not establish successful deployment or recovery. This includes KEP-6444's 50 outcomes and COT-708's 16 outcomes, whose detailed outcome labels are unsupported by their closure fields. All receive unobserved/unknown judgments. Inferred relationships—including 43 whose rationales explicitly say “reject”—cannot directly drive grouping or support facts and observed outcomes. KEP-5480's retest title likewise does not automatically supersede the earlier decision. In the batch-1 pilot, the LLM recognized that successfully bypassing Weibo validation was harmful despite the words “Test Pass.” Its customer-level impact assignment remained insufficiently supported.

**Surviving errors and inspection examples.** These safeguards do not comprehensively repair the graph. A concrete failure remains in the completed production memory: Community_534's passage mentions `RedditPostMetadata`, but the model accepted it as a fact about the Twitter resource node. The stored fact, `fact_59af81ef6bfea7e3`, cites `ev_9af8da11382aa82a` and assigns `resource_08ce433d` (“Twitter comment download status tracking”) as its entity. The quotation is accurate; the entity assignment is unsupported.

Fixed grouping also cannot separate occurrences already collapsed into one decision. The node `decision_93b61398` spans 21 records, yet the model can only accept or reject the candidate boundary containing it. Entity identity, occurrence boundaries and causal interpretation remain imperfect. Marking `PRODUCES` as causally unverified does not explicitly separate an outage from the intervention responding to it.

Dates inside parsing errors, such as KEP-4091 and KEP-4387, and the S3 paths in KEP-5571 still enter the dated-mention list. The stored metadata identifies them as mentions with unspecified event roles, but that does not resolve their temporal meaning. I therefore claim protection against specific failure modes and use these surviving errors as explicit inspection examples. Source fidelity and structural validation cannot establish general semantic correctness.

## Task 2 agent methodology

**Purpose and input.** I designed the agent for a new engineering lead who needs to
distinguish recurring problems, reported causes, documented routines, and changes over
time. A useful answer should make those distinctions inspectable, including what the
records cannot establish. I freeze the memory before evaluating answers so that later
results cannot silently alter the evidence or abstractions being tested.

The selected [schema 3.1 memory](artifacts/memory/memory.json) contains
653 episodes, 1,086 facts, 46 patterns, and 791 outcome assessments. All 816 eligible
base candidates and 23 abstraction packets were processed; completion does not mean
that every candidate was accepted or every outcome was observed. The source-only
corpus contains 901 records and 2,322 distinct passages after deduplication within each
record. These are extracted passages preserved in the supplied graph, not complete
external tickets. Input validation checks memory, graph, and embedding identities and
rejects incomplete production inputs. I use the completed memory (Luna base, Astra
patterns) unchanged; its structural validation does not establish semantic accuracy
or downstream QA performance.

### Division of labor and tool selection

I use one LangChain agent with a JSON adapter over the existing provider client. Each
model call selects one registered read-only action or finishes with `DraftAnswer`.
This keeps action selection flexible while making evidence access and costs auditable.
There is no fixed memory-first workflow: a narrow record question can start with the
graph, while a comparative question can start with a stored pattern.

| Family and tool | Purpose and design reason |
|---|---|
| Memory: `recall_memory` | Find compact entry points from a partial cue, reducing the need to rediscover related records. |
| Memory: `inspect_memory` | Elaborate a selected item with original passages, uncertainty, and counterevidence before relying on it. |
| Memory: `list_patterns` | Expose stored comparisons across records, their support, and their limits. |
| Memory: `list_outcomes` | Find observed or uncertain outcome assessments, including those outside accepted episodes; ordinal impact is not measured business value. |
| Memory: `memory_timeline` | Separate explicit dated mentions from unplaced evidence without inventing order from ticket IDs. |
| Graph: `search_graph` | Locate passages and distinct entity IDs when memory omits a useful record or vocabulary. |
| Graph: `graph_neighborhood` | Inspect local relationships and their provenance while preserving direction. |
| Graph: `graph_paths` | Explore possible connections using bounded paths; connectivity suggests investigation, not causality. |
| Graph: `get_evidence` | Read exact source slices with offsets and continuation positions for detail and citation checking. |

Memory contributes selection and previously computed comparisons. Its potential speed
benefit comes from avoiding repeated discovery; speed remains an empirical question.
The graph provides access to details outside the selected memory and lets the agent
check whether a remembered interpretation matches its source. Both tools can expose
the same passage, so this division is about access and abstraction, not independent
evidence sources.

Recall combines BM25 with similarity to existing node vectors and bounded memory
associations. Because the supplied embedding encoder is unknown, the query vector is
derived from lexically matched node labels rather than a new incompatible text encoder.
Rank fusion, confidence multipliers, and association decay are heuristics. This supports
partial-cue recall but still depends on useful lexical anchors. Terminology aliases
expand queries without merging entity identities; common hubs are discounted. Default
recall omits compressed episodes, which can be requested explicitly. Duplicate
facts of the same text, scope, and kind and results outside the retrieval limit receive
recorded exclusion reasons.

The agent is instructed to inspect original graph evidence for causes, claimed fixes,
and chronology. It must distinguish source reports from prescriptions and hypotheses.
Neither `CAUSES`/`PRODUCES` links nor administrative closure establish a permanent fix;
repeated procedural instructions do not prove repeated execution. Timelines use explicit
date mentions, which are not automatically incident or recovery dates. These interpretive
rules guide the model; exact citation validation alone cannot enforce their meaning.

### Working memory and stopping

I keep persistent organizational memory separate from the agent's per-question context.
Each question starts with fresh conversational state. Instructions, the question,
artifact identity, tool/action schemas, and selected message exchanges enter the model
request. Discovery tools supply compact cards or excerpts; inspection adds selected
source text. Pagination makes additional detail an explicit action rather than inserting
the whole archive into every request.

Before each call, the application projects the conversation into **200,000 canonical
serialized characters**. This is a reproducible application-input bound, not a model-token
limit or the provider's full wire size. The agent may pin previously shown evidence
supporting active claims or material counterevidence, and discard previously shown memory
items with short relevance reasons. Projection removes discarded cards unless protected
by pinned evidence, removes older duplicate tool exchanges, and then evicts the oldest
unpinned whole exchanges until the request fits. Keeping call/result pairs intact avoids
orphaned tool messages. The question, pinned evidence, and newest remaining exchange are
preserved; if they cannot fit, the run stops explicitly. There is no generated rolling
summary that could silently rewrite a quotation.

The default is 200,000 characters for all three systems. Both `run_task2.py` and
`run_evaluation.py run` expose `--max-request-chars`. The original pilot used 48,000
characters and its BrightData graph-only answer exceeded that cap. I preserve that run
in `pilot-sol-v1`; the revised pilot and final use new `pilot-sol-v2` and `final-sol-v2`
directories because changed configurations cannot resume an existing experiment.

The full ledger stays outside model context and records what was returned, actually
shown, discarded, and evicted. Citation-access checks retain the history of previously
shown spans, even after eviction; they do not assert that every cited span remained in
the final request. The context events make that distinction inspectable.

The default per-question limits are twelve model calls and ten data-tool calls.
Retrieval also stops after three consecutive calls adding no new item, node, evidence,
or source span, or when only two model calls remain for finishing and correction. A
new page of an existing source counts as progress. These bounds limit repeated searching
and leave room to produce a partial answer; they have not been optimized experimentally.
Invalid citations receive at most one correction using already-seen evidence, without
further retrieval. Remaining invalid claims are excluded and recorded. Missing evidence,
provider failures, and budget stops remain visible as partial or failed results.

### Claims provenance confidence and trace

Each answer contains up to twelve atomic claims. A claim identifies its statement and
kind (`source_report`, `prescription`, `synthesis`, or `hypothesis`), exact evidence IDs,
quotations and character offsets, relevant memory IDs, confidence and its justification,
and a short verification note. The application derives source record IDs and checks that
cited spans were actually shown and memory references link to the cited evidence. Each
claim needs substantive extracted support; graph labels, inferred rationales, and closure
metadata alone are insufficient.

| Recorded source route | Operational meaning |
|---|---|
| `memory` | Linked memory items were used; not every cited span was also accessed through graph tools. |
| `graph` | No memory item is attributed and graph evidence was accessed. |
| `memory_confirmed_by_graph` | Memory items were used and every cited span was also shown through a graph tool. |
| `text` | The baseline used retrieved source text without memory attribution. |

The confirmed route is an access-based label, not proof of entailment, independent
corroboration, or a causal account of everything influencing the model. Memory IDs are
declared by the model and checked against access and support links. An exact quotation
can still support less than the claim asserts, which is why semantic grounding is judged
separately.

Confidence is qualitative: high for unambiguous direct support, medium for qualified
synthesis, and low for hypotheses or unresolved conflicts. Hypotheses are mechanically
required to carry low confidence; other confidence-to-evidence relationships depend on
model judgment. These labels are not calibrated probabilities, and the evaluation does
not measure calibration.

The requested reasoning trace is an execution and evidence trace: action purpose, tool
name and arguments, returned memory items, evidence access, ranking exclusions, explicit
relevance discards, context evictions, and claim support. It contains concise evidence
explanations rather than private chain-of-thought. Ranking exclusions, model discards,
and context eviction are separate events because they have different causes. The full
JSONL is streamed during execution and retained alongside the answer and manifest; an
absent discard event is not given an invented explanation.

## Task 2 evaluation methodology

### Comparison and questions

I compare three systems to separate the combined system's value from the contribution
of memory access. **Text RAG** performs one BM25 retrieval of up to twenty positive-scoring
records and one generation, with at most one format/citation correction. Identical
passages within a record are collapsed while preserving equivalent evidence references.
Whole records are added in rank order if they fit the request cap; oversized records are
logged as omitted and later candidates can still fit. The baseline sees extracted text,
not graph labels, inferred links, or memory items. BM25 is a simple, inspectable standard
baseline, but this comparison does not cover dense retrieval, reranking, or iterative RAG.

**Graph-only** uses the four graph tools and never loads memory or builds its indexes.
**Memory+graph** adds the five memory tools, stored abstractions, and memory-derived
terminology expansion. All three use `gpt-6-sol` at medium reasoning, shared evidence
rules, the same answer schema, and the 200,000-character cap. Both agents have identical
call limits. The selected models are passed explicitly because CLI defaults differ.
Tool schemas and prompts consume part of the cap, so equal request limits do not imply
equal available source text. Costs are measured rather than equalized: additional
retrieval may buy quality at additional expense.

Memory+graph versus text RAG evaluates the combined approach. Memory+graph versus
graph-only estimates the contribution of the memory package, including vocabulary
expansion and changed tool/prompt affordances. It does not isolate patterns, facts,
outcome valuations, or any single recall mechanism.

| Final question focus | Capability and distinction being tested |
|---|---|
| Recurring processing failures in narrative generation and collection | Compare independent occurrences while preserving different mechanisms. |
| Government tenant's April narrative outage | Distinguish the reported processing cause, detection/response failures, and what the timeout change addressed. |
| DocDB/Elasticsearch gaps | Separate supported explanations from an unsupported universal cause. |
| April collection incident and backfill | Order reported events without equating a deployment or backfill instruction with verified recovery. |
| Monitoring and QA routines | Distinguish prescribed cadence, reported execution, and demonstrated effectiveness. |
| Narrative pruning and remediation | Compare behavior and fixes while acknowledging uncertain chronology. |

These six questions cover patterns, root causes, routines, and change over time. Two
additional pilot questions cover conflicting Weibo validation/retest evidence and
BrightData migration plans versus outcomes. Pilots are for protocol inspection and are
excluded from final scores. Assignment examples and abstraction themes overlap with the
questions; these are known-corpus diagnostics, not held-out generalization tests.

### Reference criteria without gold answers

I use an evidence-linked checklist instead of a model-written answer key. Reference
preparation combines seed records and BM25 searches over original passages, retaining
search queries, included records, and omissions from bounded packets. Each question has
four to eight facets specifying essential facts or justified uncertainty, exact evidence
spans, and whether any listed source or all listed sources are needed. Cautions identify
tempting unsupported conclusions. This makes missing coverage inspectable without
requiring one preferred wording or narrative.

The saved frozen benchmark (`artifacts/evaluation/benchmark/benchmark.frozen.json`, local artifact) has
eight questions and 43 facets: 33 final and ten pilot facets. Its generation metadata
records authorship by the coding assistant from inspected excerpts after the configured
SDK drafting attempt failed. It was frozen under the explicit instruction, “Let's assume
they are correct,” recorded as `review_basis: user_assumption`. Exact quotations and
offsets passed structural validation. This is not human semantic review, an exhaustive
reference search, or gold-answer correctness. Freezing preserves a reproducible
comparison; it does not remove reference bias.

A separate `gpt-6.1-sol` judge at medium reasoning receives an anonymous answer, reference
facets and cautions, and source context from cited and reference-pool records. System
identity, tool history, memory IDs, and route labels are withheld. Blinding reduces
explicit system preference but cannot guarantee that answer style reveals nothing.
The judge splits compound claims into propositions and checks each against that claim's
own citations: another passage in the reference packet cannot rescue a bad citation.
Equivalent supported answers can satisfy facets; useful material outside the checklist
is flagged as a reference omission rather than silently enlarging the denominator.

### Measures and interpretation

| Dimension | Operational definition and interpretation |
|---|---|
| Coverage | Mean facet credit: 1 fully covered with support, 0.5 partially covered with support, 0 absent or contradicted. Factual facets need supported claims; justified uncertainty may appear in limitations or unanswered aspects. |
| Groundedness | Fully supported atomic propositions divided by all judged propositions. Partial, unsupported, and contradicted propositions remain separate counts. No propositions means undefined groundedness, not a perfect score. |
| Specificity | Supported-detail score from 0 to 4: no useful detail; topic only; scoped systems and symptoms/routines; mechanisms/actions/outcomes; precise distinctions appropriate to the question. Unsupported detail earns no credit. |
| Consistency | Jaccard overlap of fully covered facet sets, plus contradiction rate among comparable proposition pairs, for original versus repeat and original versus paraphrase. An empty union or no comparable pairs is undefined. Internal contradictions are also counted. |
| Cost | Reported input/output tokens, model and data-tool calls, and answering wall time. Index/setup time, memory construction, and judging overhead are reported separately. |

Exact citation validity is an additional structural diagnostic, separate from semantic
groundedness. Consistency measures stability rather than truth: two wrong answers can
agree. Empty or failed answers cannot earn specificity or known-fact coverage through
abstention. A failed run receives zero coverage and specificity and undefined grounding;
a run that has not occurred remains missing. Completion and missingness counts accompany
means, which exclude undefined values.

I pair each final question with an identical repeat and an equivalent paraphrase. Across
three systems this schedules 54 answers and 36 consistency comparisons, in addition to
six pilot answers. A seeded schedule (`20261006`) varies question/system order within
each variant block. Each answer starts fresh and uses a distinct response-cache directory
so repeats are not fulfilled by replaying the original answer. Fingerprints bind code,
settings, source, memory, and benchmark; resume preserves completed answers, including
failures. Changed configurations or retries of saved failures require a new experiment.

The report averages variants within each question, then averages question-level values
and reports paired memory+graph differences against each comparator. Six questions remain
six evaluation units; the repeats do not create eighteen independent questions. Per-run
tables remain necessary because missing variants can make aggregate comparisons uneven.
I interpret direction and size descriptively, without a significance or generalization
claim from this small, development-exposed set.

Token totals use provider-reported usage. Cached-input and reasoning tokens are subsets,
not additional totals. Missing usage stays unknown with available lower bounds; response
cache replays are excluded from fresh-cost aggregates. Construction costs are shown
separately, with amortized tokens per question at 10, 100, and 1,000 questions only when
build and online usage are available. These are accounting scenarios, not forecasts.
Subscription access does not provide a defensible dollar estimate. Stage call caps count
failed attempts and cache lookups, so a budget allowance is not measured spend.

### Audit and evidence of memory value

Automated semantic judgments remain fallible. The audit workflow selects all eighteen
canonical final answers, all flagged answers and flagged/contradictory consistency
comparisons, plus a seeded twenty percent of remaining noncanonical answers. A named
human reviewer can accept or replace a judgment with notes while preserving the original.
An exported template is not a completed audit, and benchmark acceptance by assumption
does not attest that this later review occurred. No answer audit has yet been performed.

To demonstrate value, I would pair a score difference with a trace showing the recalled
item, inspected source, and supported distinction a comparator missed. A regression
should identify the irrelevant or overgeneralized memory and its effect. The existing
facet-visibility diagnostic distinguishes reference evidence never shown from evidence
shown but not fully used; it measures visibility of this checklist's evidence, not
exhaustive retrieval recall. Route counts show use, not usefulness. Attributing gains to
individual memory components would require further ablations.

## Submission coverage and current evidence

The [Task 2 notebook](task2_evaluation.ipynb) runs top to bottom as an artifact reader.
It imports supporting code, validates frozen inputs, and displays saved outputs; it does
not execute live experiments. The [README reproduction instructions](README.md#task-2-agent-and-evaluation-submission)
and notebook list the separate CLI stages. This allows a reviewer to inspect available
evidence without provider access or accidental spending, while making the reproduction
boundary explicit.

| Task 2 requirement | Implementation or evidence | Remaining work |
|---|---|---|
| Agent chooses memory and graph tools | Nine tools and an adaptive action loop; offline contract tests | Observe tool choices in successful live answers. |
| Explicit working-memory design | Context projection, pins, discards, eviction reasons, and bounded calls | Measure its effect on real questions. |
| Claims, provenance, trace, and confidence for every answer | Structured answer contract, exact citation checks, and JSONL ledger | Produce real final answers under the selected cap. |
| At least four questions spanning required capabilities | Six final questions and two separate pilots, frozen with cited facets | Execute six pilot and 54 final answers. |
| RAG comparison on all five dimensions | Baseline, graph-only ablation, judge, metrics, and reporting code | Complete judgments, 36 consistency comparisons, and human audit. |
| Runnable code and inline outputs | Supporting modules/CLIs, artifact-only notebook, input tables, and failure trace | Populate real answer tables, quality/cost charts, and case studies. |
| Reasons for design decisions and final reflection | This methodology and matching notebook prose | Update the empirical reflection after evaluating real answers. |

The terminal answering check (`artifacts/task2/sol-pilot-check-v2/answer.json`, local artifact) returned
a cited partial answer and the judge probe (`artifacts/evaluation/preflight-sol-v2/preflight.json`, local artifact)
succeeded. The original pilot (`artifacts/evaluation/pilot-sol-v1/progress.json`, local artifact) finished
six attempts and judging, with one graph-only failure under the old context cap.
Earlier sandbox startup failures (`artifacts/evaluation/preflight-sol-v1/runtime_diagnostic.json`, local artifact)
remain historical diagnostics. The revised pilot, final comparison, and memory benefit
are still pending. Offline tests verify contracts and reporting behavior with scripted
responses; the submission never substitutes their synthetic scores for measurements.

## Final reflection

**What worked.** Preserving exact quotations and recording separate decisions made
mistakes inspectable. The Task 1 batch-1 pilot distinguished closure from observed
improvement in the inspected cases, and the Task 2 contract checks reject unseen or
altered citations. This is evidence of auditability and application behavior, not yet
evidence of reliable live answers.

**What surprised me about the data.** Records are not independent incidents. Shared
decision nodes, repeated excerpts, and Community summaries can make one observation
look like several. The [data audit](DATA_UNDERSTANDING.md) also shows a retest summary
claiming resolution while the cited ticket reports validation still absent. Even
“success” can refer to successfully reproducing harmful behavior.

**Which memory earned its place and which was decoration.** Source-linked facts,
episode context, and preserved uncertainty earned their place in inspection because
they make claims challengeable. Administrative closure and duplicate associations add
little useful history and are guarded or de-emphasized. Patterns are more than labels
when they preserve a supported comparison and counterevidence, but their downstream
value remains unmeasured. Numeric impact scores, confidence weights, and association
paths could still be decoration if they do not improve answers relative to their cost;
being stored or retrieved does not demonstrate that improvement.

**The single biggest flaw.** Fixed episode boundaries can split one incident or combine
different occurrences. The judge can reject a candidate but cannot repair its boundary.
That can distort both what is recalled and how many independent occurrences support a
pattern, even when every quotation is correct.

**What I would do next.** Establish a working provider runtime, inspect the six pilot
answers, freeze settings, and execute the final comparison and judgment audit. I would
then examine misses in a small independent source sample, including rejected memory,
before changing boundaries or ranking. Component ablations and new questions would test
whether patterns, aliases, and outcome scores justify their complexity. I would not
tune those components against the final answers and present the same set as held out.

**Likely first error.** “If the team asked this agent a question tomorrow, the first
wrong thing it would tell them is that a defect affected customers when the evidence
only established a failed test.” This prediction follows the inspected Weibo pilot's
unsupported customer-level outcome assignment; it is not an observed Task 2 answer.
