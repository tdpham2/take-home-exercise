"""Sequential, interleaved experiment matrix with immutable inputs and resumable outputs."""
from pathlib import Path
import json
import random
import time

from org_agent import OrganizationalAgent, save_result
from org_agent.artifacts import Artifacts, SourceArtifacts
from org_agent.models import AnswerResult
from org_memory.storage import atomic_json
from org_memory.evidence import stable_id
from org_memory.hosted import BudgetExceeded, ProviderUnavailable
from .baseline import TextRAG
from .benchmark import load_frozen
from .common import CallBudget, client_for, code_fingerprint, fingerprint, read_json
from .corpus import TextCorpus
from .judge import judge_answer, judge_consistency, JUDGE_PROMPT, CONSISTENCY_PROMPT
from .metrics import failure_judgment


APPROACHES = ("text_rag", "graph_only", "memory_graph")
VARIANTS = ("original", "repeat", "paraphrase")


def make_schedule(benchmark, split="final", seed=20261006):
    rng = random.Random(seed)
    questions = [q for q in benchmark["questions"] if q["split"] == split]
    variants = VARIANTS if split == "final" else ("original",)
    schedule = []
    for variant in variants:
        qs = questions.copy()
        rng.shuffle(qs)
        for q in qs:
            arms = list(APPROACHES)
            rng.shuffle(arms)
            for arm in arms:
                schedule.append({"run_id": f"{q['id']}__{variant}__{arm}", "question_id": q["id"],
                                 "variant": variant, "approach": arm,
                                 "question": q["paraphrase"] if variant == "paraphrase" else q["text"]})
    return schedule


def preflight(graph_path, memory_path=None):
    started = time.monotonic()
    source = SourceArtifacts.load(graph_path)
    corpus = TextCorpus(source)
    result = {"source_identity": source.identity, "corpus_fingerprint": corpus.fingerprint,
              "records": len(corpus.records), "unique_record_passages": sum(len(r["passages"]) for r in corpus.records),
              "provider_checked": False, "production_memory_ready": False}
    if memory_path:
        try:
            artifacts = Artifacts.load(graph_path, memory_path)
            result.update(production_memory_ready=True, memory_identity=artifacts.identity,
                          stored_patterns=len(artifacts.memory["patterns"]))
        except (ValueError, OSError, KeyError) as exc:
            result["memory_error"] = str(exc)
    result["source_index_elapsed_seconds"] = time.monotonic() - started
    return result


def run_matrix(graph_path, memory_path, benchmark_path, output, config, *, split="final", seed=20261006,
               max_calls=600, client_factory=None, max_runs=None):
    output = Path(output)
    started = time.monotonic()
    source = SourceArtifacts.load(graph_path)
    corpus = TextCorpus(source)
    benchmark = load_frozen(benchmark_path, corpus)
    # No provider is created until the input scopes and reviewed benchmark are valid.
    artifacts = Artifacts.load(graph_path, memory_path)
    if artifacts.identity.get("execution_scope") == "preview":
        raise ValueError("Evaluation excludes provisional memory")
    schedule = make_schedule(benchmark, split, seed)
    configuration = config.model_dump(exclude={"cache_dir"})
    manifest = {"version": "evaluation-run-v1", "source_identity": source.identity,
                "memory_identity": artifacts.identity, "corpus_fingerprint": corpus.fingerprint,
                "benchmark_fingerprint": benchmark["fingerprint"], "code_fingerprint": code_fingerprint(),
                "answer_configuration": configuration, "split": split, "seed": seed, "schedule": schedule,
                "baseline_top_k": 20, "synthetic_provider": client_factory is not None}
    manifest["fingerprint"] = fingerprint(manifest)
    path = output / "manifest.json"
    if path.exists():
        if read_json(path) != manifest:
            raise ValueError("Run inputs/configuration/code changed; use a new output directory")
    else:
        atomic_json(output / "inputs" / "graph.json", source.graph)
        atomic_json(output / "inputs" / "memory.json", artifacts.memory)
        atomic_json(output / "inputs" / "benchmark.json", benchmark)
        atomic_json(output / "setup.json", {"index_and_validation_seconds": time.monotonic() - started,
                    "memory_build_metadata": artifacts.memory.get("build_metadata", {}),
                    "abstraction_metadata": artifacts.memory.get("abstraction_metadata", {}),
                    "source_memory_path": str(Path(memory_path).resolve())})
        atomic_json(path, manifest)
    budget = CallBudget(output / "answer_calls.json", max_calls)
    # Index once per approach; each .answer call still owns fresh conversation state.
    index_started = time.monotonic()
    systems = {"text_rag": TextRAG(source, config, corpus=corpus),
               "graph_only": OrganizationalAgent(source, config, tool_profile="graph_only"),
               "memory_graph": OrganizationalAgent(artifacts, config)}
    setup_path = output / "setup.json"
    setup = read_json(setup_path)
    if "approach_index_seconds" not in setup:
        setup["approach_index_seconds"] = time.monotonic() - index_started
        atomic_json(setup_path, setup)
    count = 0
    for job in schedule:
        directory = output / "runs" / job["run_id"]
        answer_path = directory / "answer.json"
        if answer_path.exists():
            answer = read_answer(output, job["run_id"])
            if answer.get("manifest", {}).get("evaluation_fingerprint") != manifest["fingerprint"]:
                raise ValueError("Saved answer belongs to another experiment")
            if answer["question"] != job["question"]:
                raise ValueError("Saved answer question differs from scheduled question")
            continue
        allowance = 2 if job["approach"] == "text_rag" else config.max_model_calls
        if budget.limit - len(budget.state["attempts"]) < allowance or (max_runs is not None and count >= max_runs):
            break
        cfg = config.model_copy(update={"cache_dir": str(directory / "cache")})

        def factory():
            injected = (lambda: client_factory(job, cfg)) if client_factory else None
            return client_for(cfg, budget=budget, factory=injected)

        system = systems[job["approach"]]
        system.config, system.client_factory = cfg, factory
        trace_path = directory / "trace.jsonl"
        answer_started = time.monotonic()
        try:
            answer = system.answer(job["question"], trace_path=trace_path)
        except (RuntimeError, ValueError, OSError) as exc:
            # Keep already-flushed events when an error escapes the answering system.
            events = [json.loads(line) for line in trace_path.read_text().splitlines()] if trace_path.exists() else []
            answer = AnswerResult(question=job["question"], status="failed", stop_reason=f"{type(exc).__name__}: {str(exc)[:600]}",
                                  unanswered=["Execution failed before returning an answer."],
                                  trace=events, usage={
                                      "model_calls": max(sum(e["kind"] == "model_started" for e in events),
                                                         sum(e["kind"] == "model" for e in events)),
                                      "data_tool_calls": max(sum(e["kind"] == "tool_started" for e in events),
                                                             sum(e["kind"] == "tool" for e in events)),
                                      "total_elapsed_seconds": time.monotonic() - answer_started},
                                  limitations=["Inspect the stage call ledger for attempted calls and any missing usage."])
        answer.manifest.update(evaluation_fingerprint=manifest["fingerprint"], run=job)
        # Publish the receipt first: answer.json remains the commit marker. A crash
        # after answer publication can then resume without losing its integrity record.
        atomic_json(directory / "receipt.json", {"answer_fingerprint": fingerprint(answer.model_dump())})
        save_result(answer, directory)
        count += 1
        completed = sum((output / "runs" / s["run_id"] / "answer.json").exists() for s in schedule)
        atomic_json(output / "progress.json", {"status": "complete" if completed == len(schedule) else "incomplete",
                    "scheduled": len(schedule), "finished": completed, "last_run": job["run_id"]})
    completed = sum((output / "runs" / s["run_id"] / "answer.json").exists() for s in schedule)
    progress = {"status": "complete" if completed == len(schedule) else "incomplete",
                "scheduled": len(schedule), "finished": completed, "attempted_provider_calls": len(budget.state["attempts"])}
    atomic_json(output / "progress.json", progress)
    return progress


def read_answer(output, run_id):
    directory = Path(output) / "runs" / run_id
    answer = read_json(directory / "answer.json")
    receipt = read_json(directory / "receipt.json")
    if receipt.get("answer_fingerprint") != fingerprint(answer):
        raise ValueError(f"Answer changed after completion: {run_id}")
    return answer


def fork_scoring(source_output, benchmark_path, output):
    """Rescore saved answers against revised references without rerunning models.

    Questions/paraphrases must be identical; changing the asked question needs a new run.
    The old experiment, judgments and audit are left intact.
    """
    source_output, output = Path(source_output), Path(output)
    if output.exists():
        raise ValueError("Rescoring requires a new output directory")
    manifest, corpus, old = load_experiment(source_output)
    benchmark = load_frozen(benchmark_path, corpus)
    before = {q["id"]: (q["text"], q["paraphrase"], q["split"], q["category"]) for q in old["questions"]}
    after = {q["id"]: (q["text"], q["paraphrase"], q["split"], q["category"]) for q in benchmark["questions"]}
    if before != after:
        raise ValueError("Reference-only rescoring cannot change questions, paraphrases or categories")
    new = {k: v for k, v in manifest.items() if k != "fingerprint"}
    new.update(benchmark_fingerprint=benchmark["fingerprint"], answers_reused_from=manifest["fingerprint"])
    new["fingerprint"] = fingerprint(new)
    # Validate all existing answers before publishing anything.
    answers = {job["run_id"]: read_answer(source_output, job["run_id"]) for job in manifest["schedule"]
               if (source_output / "runs" / job["run_id"] / "answer.json").exists()}
    for name in ("graph", "memory"):
        atomic_json(output / "inputs" / f"{name}.json", read_json(source_output / "inputs" / f"{name}.json"))
    atomic_json(output / "inputs" / "benchmark.json", benchmark)
    for name in ("setup.json", "answer_calls.json", "progress.json"):
        atomic_json(output / name, read_json(source_output / name))
    for rid, a in answers.items():
        a["manifest"].update(evaluation_fingerprint=new["fingerprint"], original_evaluation_fingerprint=manifest["fingerprint"])
        atomic_json(output / "runs" / rid / "receipt.json", {"answer_fingerprint": fingerprint(a)})
        save_result(AnswerResult.model_validate(a), output / "runs" / rid)
    atomic_json(output / "manifest.json", new)
    return {"status": "ready_for_judging", "reused_answers": len(answers), "output": str(output)}


def load_experiment(output):
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    if manifest["fingerprint"] != fingerprint({k: v for k, v in manifest.items() if k != "fingerprint"}):
        raise ValueError("Experiment manifest fingerprint mismatch")
    source = SourceArtifacts.load(output / "inputs" / "graph.json")
    corpus = TextCorpus(source)
    benchmark = load_frozen(output / "inputs" / "benchmark.json", corpus)
    if benchmark["fingerprint"] != manifest["benchmark_fingerprint"] or source.identity != manifest["source_identity"]:
        raise ValueError("Experiment inputs changed")
    if stable_id("memory", read_json(output / "inputs" / "memory.json")) != manifest["memory_identity"]["memory_fingerprint"]:
        raise ValueError("Frozen experiment memory changed")
    return manifest, corpus, benchmark


def run_judging(output, config, *, max_calls=200, client_factory=None):
    output = Path(output)
    manifest, corpus, benchmark = load_experiment(output)
    if config.model == manifest["answer_configuration"]["model"]:
        raise ValueError("The agreed protocol requires a separate judge model")
    identity = {"configuration": config.model_dump(exclude={"cache_dir"}),
                "rubric_fingerprint": fingerprint([JUDGE_PROMPT, CONSISTENCY_PROMPT]),
                "benchmark_fingerprint": benchmark["fingerprint"], "code_fingerprint": code_fingerprint(),
                "synthetic_provider": client_factory is not None}
    identity_path = output / "judge_manifest.json"
    if identity_path.exists() and read_json(identity_path) != identity:
        raise ValueError("Judge/rubric changed; retain old results and use a new experiment directory")
    atomic_json(identity_path, identity)
    questions = {q["id"]: q for q in benchmark["questions"]}
    budget = CallBudget(output / "judge_calls.json", max_calls)
    cfg = config.model_copy(update={"cache_dir": str(output / "judge_cache"), "max_model_calls": 100})
    client = client_for(cfg, budget=budget, factory=client_factory)
    schedule = manifest["schedule"].copy()
    random.Random(manifest["seed"] + 1).shuffle(schedule)
    errors = []
    try:
        for job in schedule:
            ap = output / "runs" / job["run_id"] / "answer.json"
            jp = output / "judgments" / f"{job['run_id']}.json"
            if not ap.exists():
                continue
            answer = read_answer(output, job["run_id"])
            question = questions[job["question_id"]]
            if answer["status"] == "failed" and not answer["claims"]:
                atomic_json(jp, {"status": "complete", "origin": "deterministic_failure",
                                 "result": failure_judgment(question), "answer_fingerprint": fingerprint(answer)})
                continue
            try:
                judge_answer(client, question, answer, corpus, jp, identity)
            except ValueError as exc:
                errors.append({"run_id": job["run_id"], "error": str(exc)})
        if manifest["split"] == "final":
            for q in (q for q in benchmark["questions"] if q["split"] == "final"):
                for arm in APPROACHES:
                    for variant in ("repeat", "paraphrase"):
                        left_id, right_id = f"{q['id']}__original__{arm}", f"{q['id']}__{variant}__{arm}"
                        paths = [output / "runs" / rid / "answer.json" for rid in (left_id, right_id)]
                        if not all(p.exists() for p in paths):
                            continue
                        left, right = [read_answer(output, rid) for rid in (left_id, right_id)]
                        # Randomize sides independently to reduce a systematic side effect.
                        flipped = random.Random(f"{manifest['seed']}:{right_id}").choice([False, True])
                        if flipped:
                            left, right = right, left
                        cp = output / "consistency" / f"{right_id}.json"
                        try:
                            judge_consistency(client, left, right, cp, {**identity, "sides_flipped": flipped})
                        except ValueError as exc:
                            errors.append({"run_id": right_id, "error": str(exc)})
    except (BudgetExceeded, ProviderUnavailable, RuntimeError, OSError) as exc:
        errors.append({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        client.close()
    judged = sum(p.exists() and read_json(p).get("status") == "complete"
                 for p in (output / "judgments" / f"{s['run_id']}.json" for s in schedule))
    expected_consistency = 36 if manifest["split"] == "final" else 0
    completed_consistency = sum(read_json(p).get("status") == "complete" for p in (output / "consistency").glob("*.json"))
    result = {"status": "complete" if judged == len(schedule) and completed_consistency == expected_consistency and not errors else "incomplete",
              "judged": judged, "expected": len(schedule), "consistency_judged": completed_consistency,
              "consistency_expected": expected_consistency, "errors": errors}
    atomic_json(output / "judging_progress.json", result)
    return result
