# Organizational Memory and Evidence-Grounded Agents

A take-home implementation that builds organizational memory from a knowledge graph,
then evaluates an agent that uses that memory alongside the original evidence.

- **Task 1:** preserve source passages, select episodes and facts, assess outcomes,
  retain useful history, and synthesize patterns across records.
- **Task 2:** answer questions with memory and graph tools, and compare against
  graph-only and BM25 text retrieval baselines.

Read [METHODOLOGY.md](METHODOLOGY.md) for design choices and limitations, and
[DATA_UNDERSTANDING.md](DATA_UNDERSTANDING.md) for the source-data findings.

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

To use the assignment data, place the supplied **`KEP_2026.json`** at the repository
root. It is required for the full test suite and real-data commands:

```bash
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

The repository includes the selected memory and its inspection reports. The
raw `KEP_2026.json` dataset and all other generated runs remain outside Git; obtain
the supplied graph separately for real-data commands and the full test suite. The
memory includes source quotations. Historical runs and provider caches are not
needed to use it.

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

The final evaluation is **incomplete**. No final comparative benefit is established.
The eight-question reference checklist (two pilot, six final) was accepted by explicit
user assumption; exact citations were checked, but no human semantic review is claimed.
Keep partial runs separate from completed submission results.

With the graph, selected memory and frozen benchmark bundle available:

```bash
python run_evaluation.py preflight \
  --memory artifacts/memory/memory.json \
  --output artifacts/evaluation/preflight
```

This command makes no provider calls unless `--check-provider` is added. Use
`python run_evaluation.py --help` for the prepare, draft, freeze, run, judge, audit
and report stages. See the Task 2 notebook for complete experiment commands.

| Notebook | Purpose | Requirements |
| --- | --- | --- |
| `task1_hosted.ipynb` | Hosted construction walkthrough | Graph and provider access; executing it makes live calls |
| `task1_offline.ipynb` | Offline baseline walkthrough | Graph; no provider calls |
| `task2_evaluation.ipynb` | Read saved answers, traces and evaluation results | Graph, selected memory and benchmark; no provider calls |

The Task 2 notebook reads saved results and leaves missing results missing. To regenerate
the notebook source (clearing that notebook's outputs):

```bash
python scripts/create_notebook.py --mode hosted --output task1_hosted.ipynb
python scripts/create_notebook.py --mode offline --output task1_offline.ipynb
python scripts/create_evaluation_notebook.py
```

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
| `artifacts/` | Other generated runs and caches remain local |
