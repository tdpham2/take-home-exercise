# Organizational Memory and Evidence-Grounded Agents

A take-home implementation that builds organizational memory from a knowledge graph,
then evaluates an agent that uses that memory alongside the original evidence.

- **Task 1:** preserve source passages, select episodes and facts, assess outcomes,
  retain useful history, and synthesize patterns across records.
- **Task 2:** answer questions with memory and graph tools, and compare against
  graph-only and BM25 text retrieval baselines.

Read [METHODOLOGY.md](METHODOLOGY.md) for design choices and limitations, and
[DATA_UNDERSTANDING.md](DATA_UNDERSTANDING.md) for the source-data findings.
Open [task1_results.ipynb](task1_results.ipynb) for the executed Task 1 walkthrough
of the completed CLI outputs, including the generation commands and model provenance.

## Setup

Use **Python 3.12** and one virtual environment for both tasks, notebooks and tests.
Run all commands from the repository root.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead. If using a notebook
editor, select this environment as its Python kernel. Jupyter's browser UI is not
required; notebooks can also be executed with `scripts/execute_notebook.py`.

No credentials are needed for tests, synthetic smoke checks or saved-memory validation.
For live calls, copy `.env.example` to `.env` and configure a provider. The Codex
provider requires a local login; the compatible API provider uses `MEMORY_API_KEY`
or `OPENAI_API_KEY`. See `.env.example` for settings. Never commit `.env`.

## Run without model calls

These smoke checks use synthetic fixtures and work without the assignment dataset:

```bash
python scripts/smoke_agent.py
python scripts/smoke_evaluation.py
```

The final evaluation includes a frozen copy of the assignment graph. To use commands
and tests that default to **`KEP_2026.json`**, copy it to the repository root once:

```bash
cp artifacts/evaluation/final-sol-v2/inputs/graph.json KEP_2026.json
python -m pytest -q
python run_task1.py --mode offline
python scripts/audit_data_understanding.py
```

The offline baseline writes to `artifacts/offline/`. It uses deterministic rules and
is separate from the selected hosted result. Tests and synthetic smoke checks verify
implementation behavior; they do not measure model quality.

## Selected memory

The selected result is `artifacts/memory/memory.json`:

| Contents | Count |
| --- | ---: |
| Episodes | 653 |
| Facts | 1,086 |
| Patterns | 46 |
| Outcome assessments | 791 |

Luna (`gpt-5.6-luna`) judged the base episodes, facts and outcomes;
**Astra (`gpt-6-astra`) generated only the pattern layer**. All 46 patterns are
already in `memory.json["patterns"]`. The enriched memory preserves source evidence
and the original base judgments. Both build stages
are complete; structural validation does not establish semantic correctness.

The repository includes the selected memory, its inspection reports, and the final
evaluation with frozen graph, memory and benchmark inputs. These artifacts include
source quotations. The root `KEP_2026.json` copy, historical runs and provider caches
remain outside Git.

Validate the selected memory against the graph without contacting a provider:

```bash
python run_task2.py \
  --memory artifacts/memory/memory.json --validate-only
```

Inspect patterns directly:

```python
import json
from pathlib import Path

memory = json.loads(Path("artifacts/memory/memory.json").read_text())
patterns = memory["patterns"]
```

## Answer a question

The following command makes live provider calls. Configure and authenticate the
provider first. It explicitly selects the answering model used for the evaluation:

```bash
python run_task2.py \
  --memory artifacts/memory/memory.json \
  --provider codex --model gpt-6-sol \
  --question "Which recurring reliability problems appear in the records?" \
  --output artifacts/task2/example
```

Use `--provider compatible --model <available-model>` for a compatible API instead.
Model access depends on your provider/account. The agent writes `answer.md`,
`answer.json`, `trace.jsonl` and `manifest.json`. Exit codes are 0 for complete,
2 for partial and 3 for failed. Its default limits are 12 model calls, 10 data-tool
calls and 200,000 serialized application characters, configurable through `--help`.

## Rebuild hosted memory

The submitted memory was generated with `run_task1.py` (Luna base judgments), then
`run_abstraction.py` (Astra patterns). The [Task 1 notebook](task1_results.ipynb)
documents the historical output paths and commands reconstructed from saved settings,
including the resumed base build. Its cells inspect saved artifacts without model calls.

Rebuilding is optional and makes live calls. Use new output directories to preserve
selected results. The base and pattern stages are separate:

```bash
python run_task1.py --mode hosted --provider codex --model gpt-5.6-luna \
  --batch-size 1 --max-calls 1000 --output artifacts/rebuild/base

python run_abstraction.py --memory artifacts/rebuild/base/memory.json \
  --provider codex --model gpt-6-astra --max-calls 40 \
  --output artifacts/rebuild/astra
```

Call caps are limits, not completion guarantees. Interrupted or budget-limited runs
save checkpoints; rerun with the same settings and cache to resume. Abstraction
requires a completed full-graph base. Add `--dry-run` to its command to inspect the
packet plan without model calls. Do not treat pilot or preview output as a completed
production memory. `run_abstraction_audit.py` optionally audits frozen proposals;
see its `--help` for usage.

## Evaluation and notebooks

`org_eval/` compares BM25 text RAG, graph-only and memory+graph. The final design is
six questions × three systems × original/repeat/paraphrase, or **54 answers**, with
`gpt-6-sol` answering and a separate `gpt-6.1-sol` judge.

The final experiment in `artifacts/evaluation/final-sol-v2` is complete: **54 answers,
54 answer judgments and 36 consistency comparisons**. Its report is `automated_only`;
all 54 answers have `partial` status, and no human answer audit has been imported.
Memory+graph achieved higher automated coverage
than text RAG (68.9% versus 58.9%), with lower groundedness (93.0% versus 95.7%) and
higher mean latency (66.1 versus 26.2 seconds). These results describe this small benchmark.
The eight-question reference checklist (two pilot, six final) was accepted by explicit
user assumption; exact citations were checked, but no human semantic review is claimed.
Completion here means the scheduled experiment finished, not that every answer fully
answered its question.

Open the [final HTML report](artifacts/evaluation/final-sol-v2/report/report.html)
locally in a browser, or read [task2_evaluation.ipynb](task2_evaluation.ipynb) on GitHub.
The report folder contains quality/cost charts, JSON results and CSV comparisons.
The evaluation also includes all 54 answers with traces, manifests and receipts,
54 answer judgments, 36 consistency judgments, usage ledgers and frozen inputs.
The frozen benchmark and its acceptance record are in `artifacts/evaluation/benchmark/`.

Regenerate the report or validate the inputs without model calls or credentials:

```bash
python run_evaluation.py report --output artifacts/evaluation/final-sol-v2

python run_evaluation.py preflight \
  --graph artifacts/evaluation/final-sol-v2/inputs/graph.json \
  --memory artifacts/memory/memory.json \
  --output artifacts/evaluation/preflight
```

This command makes no provider calls unless `--check-provider` is added. Use
`python run_evaluation.py --help` for the prepare, draft, freeze, run, judge, audit
and report stages. See the Task 2 notebook for complete experiment commands. Live
reruns must use new output directories: the bundled manifests preserve the original
code fingerprint, while saved-result inspection and report regeneration work with
the current code.

| Notebook | Purpose | Requirements |
| --- | --- | --- |
| [task1_results.ipynb](task1_results.ipynb) | Main Task 1 submission: inspect completed memory, patterns, retention and recall | Included memory; no graph file, credentials or model calls |
| `task1_hosted.ipynb` | Optional hosted construction pilot | Graph and provider access; executing it makes live calls |
| `task1_offline.ipynb` | Optional locally generated baseline walkthrough | Graph; regenerate the legacy local notebook before running |
| [task2_evaluation.ipynb](task2_evaluation.ipynb) | Main Task 2 submission: completed comparison, claims, provenance and tool traces | Included frozen inputs and evaluation artifacts; no provider calls |

The results notebooks read saved artifacts. The Task 2 notebook leaves missing results
missing. To regenerate notebook source (clearing that notebook's outputs):

```bash
python scripts/create_task1_results_notebook.py
python scripts/create_notebook.py --mode hosted --output task1_hosted.ipynb
python scripts/create_notebook.py --mode offline --output task1_offline.ipynb
python scripts/create_evaluation_notebook.py
```

Execute the two submission notebooks from the project root without rebuilding memory
or making model calls:

```bash
python scripts/execute_notebook.py --notebook task1_results.ipynb --in-process
python scripts/execute_notebook.py --notebook task2_evaluation.ipynb --in-process
```

The included [evaluation HTML report](artifacts/evaluation/final-sol-v2/report/report.html)
can be viewed without running a notebook. Generated notebook HTML exports remain local.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `org_memory/` | Evidence, proposals, judgments, abstraction, retention, recall and validation |
| `org_agent/` | Agent, memory/graph tools, bounded working context and citation validation |
| `org_eval/` | Benchmark, baselines, experiment runner, judging, metrics and reporting |
| `run_*.py` | Command-line entry points |
| `config/abstraction_questions.json` | Pattern-investigation questions and routing cues |
| `examples/reference_cases.json` | Development inspection cases; not held-out evaluation labels |
| `scripts/` | Notebook generation/execution, data audit and smoke checks |
| `tests/` | Regression tests, including tests against the supplied graph |
| `artifacts/memory/` | Selected memory: Luna-built base and Astra-generated patterns |
| `artifacts/evaluation/benchmark/` | Frozen questions, acceptance record and source checklist |
| `artifacts/evaluation/final-sol-v2/` | Final automated evaluation, report, answers, judgments and frozen inputs |
| `artifacts/` | Other generated runs and caches remain local |
