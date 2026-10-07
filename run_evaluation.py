"""Build and audit the organizational-memory evaluation without implicit hosted calls."""
import argparse
import json
from pathlib import Path

from org_agent import AgentConfig
from org_agent.artifacts import SourceArtifacts
from org_agent.models import StrictModel
from org_memory.hosted import load_env, BudgetExceeded, ProviderUnavailable
from org_memory.storage import atomic_json
from org_eval.audit import export_audit, import_audit
from org_eval.benchmark import prepare, draft_benchmark, freeze, write_review_template, reference_report
from org_eval.common import CallBudget, client_for, checked_call
from org_eval.corpus import TextCorpus
from org_eval.report import report
from org_eval.runner import preflight, run_matrix, run_judging, fork_scoring
from typing import Literal


class ProviderProbe(StrictModel):
    status: Literal["ok"]


def config(args, judge=False):
    return AgentConfig(provider=args.provider, model=args.judge_model if judge else args.model,
                       reasoning_effort=args.reasoning_effort, timeout=args.timeout,
                       max_request_chars=getattr(args, "max_request_chars", AgentConfig.model_fields["max_request_chars"].default),
                       max_model_calls=100 if judge else 12)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="stage", required=True)
    for name in ("preflight", "prepare", "draft", "review-template", "freeze", "run", "judge", "rescore", "audit-export", "audit-import", "report"):
        p = subs.add_parser(name)
        p.add_argument("--graph", default="KEP_2026.json")
        p.add_argument("--output", default="artifacts/evaluation/final", required=name in {"freeze", "review-template", "rescore"})
        if name in {"preflight", "draft", "run", "judge"}:
            p.add_argument("--provider", choices=["codex", "compatible"], default="codex")
            p.add_argument("--model", default="gpt-5.6-luna")
            p.add_argument("--judge-model", default="gpt-6-sol", help="gpt-5.6-sol is the alternate; no silent fallback")
            p.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
            p.add_argument("--timeout", type=float, default=300)
        if name in {"prepare", "draft"}:
            p.add_argument("--benchmark-dir", default="artifacts/evaluation/benchmark")
        if name in {"preflight", "run"}:
            p.add_argument("--memory", required=name == "run")
        if name == "preflight":
            p.add_argument("--check-provider", action="store_true", help="One explicit synthetic judge-provider call")
        if name in {"draft", "run", "judge"}:
            p.add_argument("--max-calls", type=int, default={"draft": 20, "run": 600, "judge": 200}[name],
                           help="Cumulative application-call cap for this stage, including retries and cache lookups")
        if name in {"freeze", "review-template"}:
            p.add_argument("--draft", default="artifacts/evaluation/benchmark/benchmark.draft.json")
        if name in {"freeze", "audit-import"}:
            p.add_argument("--review", required=True)
        if name == "run":
            p.add_argument("--max-request-chars", type=int, default=AgentConfig.model_fields["max_request_chars"].default,
                           help="Serialized application-input character cap for all systems (default: 200000; not tokens)")
            p.add_argument("--benchmark", default="artifacts/evaluation/benchmark/benchmark.frozen.json")
            p.add_argument("--split", choices=["pilot", "final"], default="final")
            p.add_argument("--seed", type=int, default=20261006)
            p.add_argument("--max-runs", type=int, help="Finish at most this many additional answers, then checkpoint")
        if name == "rescore":
            p.add_argument("--source-run", required=True)
            p.add_argument("--benchmark", required=True)
    args = parser.parse_args(argv)
    try:
        if args.stage in {"preflight", "draft", "run", "judge"}:
            load_env()
        if args.stage == "preflight":
            result = preflight(args.graph, args.memory)
            if args.check_provider:
                cfg = config(args, True).model_copy(update={"cache_dir": str(Path(args.output) / "probe_cache")})
                budget = CallBudget(Path(args.output) / "probe_calls.json", 2)
                client = client_for(cfg, budget=budget)
                result["provider_probe"] = {"model": cfg.model, "reasoning_effort": cfg.reasoning_effort}
                try:
                    checked_call(client, "Return the requested JSON status.", {"status": "ok", "model": cfg.model},
                                 ProviderProbe, "evaluation_provider_probe", Path(args.output) / "provider_probe.json")
                    result["provider_checked"] = True
                    result["provider_probe"]["status"] = "complete"
                except (ValueError, BudgetExceeded, ProviderUnavailable, RuntimeError, OSError) as exc:
                    result.update(status="incomplete", provider_error=f"{type(exc).__name__}: {exc}")
                    result["provider_probe"]["status"] = "failed"
                finally:
                    client.close()
            atomic_json(Path(args.output) / "preflight.json", result)
        elif args.stage == "prepare":
            prepared = prepare(TextCorpus(SourceArtifacts.load(args.graph)), args.benchmark_dir)
            result = {k: prepared[k] for k in ("status", "fingerprint", "packets")}
        elif args.stage == "draft":
            cfg = config(args, True).model_copy(update={"cache_dir": str(Path(args.benchmark_dir) / "draft_cache")})
            budget = CallBudget(Path(args.benchmark_dir) / "draft_budget.json", args.max_calls)
            client = client_for(cfg, budget=budget)
            try:
                b = draft_benchmark(TextCorpus(SourceArtifacts.load(args.graph)), args.benchmark_dir, client,
                                    cfg.model_dump(exclude={"cache_dir"}))
                result = {"status": b["status"], "questions": len(b["questions"]), "path": str(Path(args.benchmark_dir) / "benchmark.draft.json")}
            finally:
                client.close()
        elif args.stage == "review-template":
            write_review_template(args.draft, args.output)
            reference_report(args.draft, TextCorpus(SourceArtifacts.load(args.graph)), Path(args.output).with_suffix(".html"))
            result = {"path": args.output}
        elif args.stage == "freeze":
            b = freeze(TextCorpus(SourceArtifacts.load(args.graph)), args.draft, args.review, args.output)
            result = {"status": b["status"], "fingerprint": b["fingerprint"], "path": args.output}
        elif args.stage == "run":
            if args.max_runs is not None and args.max_runs < 1:
                raise ValueError("--max-runs must be positive")
            result = run_matrix(args.graph, args.memory, args.benchmark, args.output, config(args),
                                split=args.split, seed=args.seed, max_calls=args.max_calls, max_runs=args.max_runs)
        elif args.stage == "judge":
            result = run_judging(args.output, config(args, True), max_calls=args.max_calls)
        elif args.stage == "rescore":
            result = fork_scoring(args.source_run, args.benchmark, args.output)
        elif args.stage == "audit-export":
            result = export_audit(args.output)
        elif args.stage == "audit-import":
            result = import_audit(args.output, args.review)
        else:
            r = report(args.output)
            result = {"status": r["status"], "synthetic": r["synthetic"], "path": str(Path(args.output) / "report" / "report.html")}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("status") == "incomplete" else 0
    except (ValueError, OSError, KeyError, BudgetExceeded, ProviderUnavailable, RuntimeError) as exc:
        print(json.dumps({"status": "incomplete", "error": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
