"""Export review packets and import attributable human decisions without replacing judges."""
from pathlib import Path
import math
import random

from org_memory.storage import atomic_json
from .common import fingerprint, read_json
from .judge import judge_packet, validate_judgment, validate_consistency
from .models import Judgment, ConsistencyJudgment
from .runner import load_experiment


def audit_basis(output):
    output = Path(output)
    return fingerprint({"manifest": read_json(output / "manifest.json"),
        "judge_manifest": read_json(output / "judge_manifest.json"),
        "answers": {p.parent.name: fingerprint(read_json(p)) for p in sorted((output / "runs").glob("*/answer.json"))},
        "judgments": {str(p.relative_to(output)): fingerprint(read_json(p))
                      for d in ("judgments", "consistency") for p in sorted((output / d).glob("*.json"))}})


def flagged(judgment):
    return bool(judgment.get("review_flags") or judgment.get("reference_omissions") or
                judgment.get("internal_contradictions") or
                any(c["verdict"] != "supported" for c in judgment.get("claims", [])))


def export_audit(output):
    output = Path(output)
    manifest, corpus, benchmark = load_experiment(output)
    progress = read_json(output / "judging_progress.json")
    if progress["status"] != "complete":
        raise ValueError("Finish judging before exporting the final audit sample")
    questions = {q["id"]: q for q in benchmark["questions"]}
    required, remaining = [], []
    for job in manifest["schedule"]:
        path = output / "judgments" / f"{job['run_id']}.json"
        j = read_json(path)["result"]
        (required if job["variant"] == "original" or flagged(j) else remaining).append(job)
    rng = random.Random(manifest["seed"] + 2)
    rng.shuffle(remaining)
    required += remaining[:math.ceil(len(remaining) * .2)]
    items = []
    for job in required:
        rid = job["run_id"]
        answer = read_json(output / "runs" / rid / "answer.json")
        j = read_json(output / "judgments" / f"{rid}.json")["result"]
        items.append({"id": rid, "kind": "answer", "reviewed": False, "decision": "accept",
                      "override": None, "notes": "", "original_judgment": j,
                      "inspection": judge_packet(questions[job["question_id"]], answer, corpus)})
    for path in sorted((output / "consistency").glob("*.json")):
        saved = read_json(path)
        j = saved["result"]
        if j["review_flags"] or any(p["relation"] == "contradiction" for p in j["comparable_pairs"]):
            items.append({"id": path.stem, "kind": "consistency", "reviewed": False, "decision": "accept",
                          "override": None, "notes": "", "original_judgment": j,
                          "inspection": saved["request"]["packet"]})
    audit = {"basis_fingerprint": audit_basis(output), "reviewer": "", "items": items,
             "sampling": "All canonical answers, all flagged answers/pairs, seeded 20% of remaining repeat answers.",
             "instructions": "Review the evidence and judgments. Set reviewed=true, decision=accept or override, and explain in notes. An override supplies the entire corrected judgment. Do not change original_judgment or inspection."}
    atomic_json(output / "audit.template.json", audit)
    return {"review_items": len(items), "path": str(output / "audit.template.json")}


def import_audit(output, review_path):
    output = Path(output)
    review = read_json(review_path)
    template = read_json(output / "audit.template.json")
    if review.get("basis_fingerprint") != audit_basis(output) or review["basis_fingerprint"] != template["basis_fingerprint"]:
        raise ValueError("Audit is stale after a change to answers, rubric, or judgments")
    if not review.get("reviewer", "").strip():
        raise ValueError("Audit requires a named human reviewer")
    expected = {(i["kind"], i["id"]): i for i in template["items"]}
    if len(review["items"]) != len(expected) or {(i["kind"], i["id"]) for i in review["items"]} != expected.keys():
        raise ValueError("Every selected audit item needs exactly one decision")
    manifest, corpus, benchmark = load_experiment(output)
    questions = {q["id"]: q for q in benchmark["questions"]}
    jobs = {j["run_id"]: j for j in manifest["schedule"]}
    accepted, agreement, overrides = [], [], 0
    for item in review["items"]:
        original = expected[(item["kind"], item["id"])]
        if any(item.get(k) != original[k] for k in ("original_judgment", "inspection")):
            raise ValueError("Audit inspection material was altered")
        if item.get("reviewed") is not True or not item.get("notes", "").strip():
            raise ValueError("Audit decision needs explicit review and notes")
        if item["decision"] not in {"accept", "override"}:
            raise ValueError("Audit decision must be accept or override")
        if item["decision"] == "accept" and item.get("override") is not None:
            raise ValueError("Accept cannot also supply an override")
        result = item["override"] if item["decision"] == "override" else item["original_judgment"]
        if item["kind"] == "answer":
            j = Judgment.model_validate(result)
            answer = read_json(output / "runs" / item["id"] / "answer.json")
            question = questions[jobs[item["id"]]["question_id"]]
            allowed = {s["evidence_id"] for s in original["inspection"]["sources"]}
            validate_judgment(j, question, answer, allowed)
            before = original["original_judgment"]
            agreement += [a["score"] == b.score for a, b in zip(sorted(before["facets"], key=lambda x: x["facet_id"]),
                                                                 sorted(j.facets, key=lambda x: x.facet_id))]
        else:
            j = ConsistencyJudgment.model_validate(result)
            validate_consistency(j, original["inspection"]["left"], original["inspection"]["right"])
        overrides += item["decision"] == "override"
        accepted.append({"id": item["id"], "kind": item["kind"], "decision": item["decision"],
                         "notes": item["notes"], "result": j.model_dump()})
    final = {"basis_fingerprint": review["basis_fingerprint"], "reviewer": review["reviewer"], "items": accepted,
             "overrides": overrides, "audited_items": len(accepted),
             "facet_score_agreement": sum(agreement) / len(agreement) if agreement else None,
             "limitation": "Agreement is descriptive for this audit sample; it is not calibrated evaluator accuracy."}
    final["fingerprint"] = fingerprint(final)
    path = output / "audit.json"
    if path.exists() and read_json(path) != final:
        raise ValueError("An imported audit is immutable; retain it before replacing the experiment")
    atomic_json(path, final)
    return {k: v for k, v in final.items() if k != "items"}
