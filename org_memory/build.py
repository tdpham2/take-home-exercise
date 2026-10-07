"""Reproducible offline construction and a separate hosted review pipeline.

The offline builder is an extractive baseline, not an LLM simulation. Its
mechanism hypotheses are explicitly declared in patterns.py and independently
counted. Full source evidence survives compression in a separate evidence map.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .evidence import BENEFIT, HARM, normalize_index, normalize, stable_id


@dataclass(frozen=True)
class BuildConfig:
    mode: str = "offline"
    max_claims_per_episode: int = 12
    max_episode_decisions: int = 8
    min_pattern_support: int = 2
    llm_max_calls: int = 200
    llm_batch_size: int = 6
    llm_max_patterns: int = 20
    llm_max_packet_chars: int = 100000


from .candidates import UnionFind


def claim_for(evidence, role=None):
    return {
        "text": evidence["source_span"],
        "evidence_ids": [evidence["id"]],
        "status": evidence["status"],
        "role": role or "source_statement",
        "method": "verbatim_excerpt",
        "confidence": "medium",  # source fidelity is high; extraction meaning is unreviewed
    }


def outcome_value(edge, index):
    status, text = edge["status"], edge["source_span"] or ""
    negative, positive = bool(HARM.search(text)), bool(BENEFIT.search(text))
    if status != "source_report":
        valence = "unknown"
    elif negative and positive:
        valence = "mixed"
    elif negative:
        valence = "harmful"
    elif positive:
        valence = "beneficial"
    else:
        valence = "unknown"
    # Only the actual outcome excerpt establishes impact; graph degree does not.
    if re.search(r"customer|tenant|all .*networks", text, re.I):
        impact = "customer-level"
    elif re.search(r"pipeline|service|outage|data collection|narrative updates", text, re.I):
        impact = "service-level"
    elif valence != "unknown":
        impact = "local"
    else:
        impact = "unknown"
    magnitude = {"local": 1, "service-level": 2, "customer-level": 3}.get(impact)
    sign = {"harmful": -1, "beneficial": 1}.get(valence)
    score = sign * magnitude if sign is not None and magnitude is not None else None
    nearby = index["outgoing"].get(edge["source_id"], [])
    resources = sorted({index["evidence"][i]["target_id"] for i in nearby
                        if index["evidence"][i]["relation"] == "AFFECTS"})
    return {
        "outcome_node_id": edge["target_id"], "evidence_ids": [edge["id"]],
        "valence": valence, "impact": impact, "signed_impact": score,
        "evidence_status": status, "related_resource_ids": resources,
        "causal_attribution": "unverified; PRODUCES is not a causal validation",
        "explanation": "Rule-based assessment of the source excerpt; closure/intention alone is unscored.",
    }


def episode_groups(index, config):
    """Decision bundles joined only by substantive extracted dependencies/events.

    Shared global decision IDs collect their cross-record evidence. They do not
    establish repeated executions: that uncertainty is retained in each bundle.
    """
    decisions = sorted(nid for nid, node in index["nodes"].items() if node["type"] == "decision")
    uf = UnionFind(decisions)
    trace, event_decisions = [], defaultdict(set)
    for e in sorted(index["evidence"].values(), key=lambda x: x["id"]):
        if e["status"] in {"inferred", "administrative", "structural_metadata", "missing"}:
            continue
        s, t = e["source_id"], e["target_id"]
        if s in uf.parent and t in uf.parent and e["relation"] in {"DEPENDS_ON", "CAUSES"}:
            if uf.union(s, t, config.max_episode_decisions):
                trace.append({"action": "merge_decision_bundles", "node_ids": [s, t],
                              "evidence_ids": [e["id"]], "reason": "substantive extracted decision dependency"})
        for event, decision in [(s, t), (t, s)]:
            if decision in uf.parent and index["nodes"][event]["type"] == "event":
                event_decisions[(e["record_id"], event)].add(decision)
    for (record, event), linked in sorted(event_decisions.items()):
        linked = sorted(linked)
        if len(linked) > config.max_episode_decisions:
            continue
        for decision in linked[1:]:
            if uf.union(linked[0], decision, config.max_episode_decisions):
                evidence_ids = [eid for eid in index["by_record"][record]
                                if event in (index["evidence"][eid]["source_id"], index["evidence"][eid]["target_id"])]
                trace.append({"action": "merge_decision_bundles", "node_ids": [linked[0], decision],
                              "evidence_ids": evidence_ids, "reason": "same extracted event in the same source record"})
    groups = defaultdict(list)
    for d in decisions:
        groups[uf.find(d)].append(d)
    return list(groups.values()), trace


def _role(e, index):
    if e["relation"] == "PRODUCES":
        return "reported_impact" if HARM.search(e["source_span"] or "") else "result_or_intention"
    if e["status"] == "requirement":
        return "requirement"
    if index["nodes"][e["target_id"]]["type"] == "risk":
        return "problem"
    if any(index["nodes"][n]["type"] == "event" for n in [e["source_id"], e["target_id"]]):
        return "event"
    if e["status"] == "intended":
        return "intended_action"
    if e["status"] == "verification_request":
        return "verification_request"
    return "context_or_action"


def build_episode(decisions, index, config):
    all_eids = sorted({eid for d in decisions for eid in
                       index["incoming"].get(d, []) + index["outgoing"].get(d, [])})
    rows = [index["evidence"][eid] for eid in all_eids]
    extracted = [e for e in rows if e["provenance"]["kind"] == "extracted"]
    if not extracted:
        return None
    substantive = [e for e in extracted if e["status"] not in {"administrative", "structural_metadata", "missing"}]
    source_text = " ".join(e["source_span"] or "" for e in substantive)
    title = " / ".join(index["nodes"][d]["label"] for d in decisions[:2])
    routine = bool(re.search(r"twice daily|two times a day|every day|weekly|monthly|each morning", source_text, re.I))
    harmed = bool(HARM.search(source_text))
    policy = any(e["status"] == "requirement" for e in substantive)
    change = bool(re.search(r"implemented|merged|increased|deployed|replaced|migrat", source_text, re.I))
    cosmetic = bool(re.search(r"hover|font|spacing|color|styling|pixel|alignment", title, re.I))
    if not substantive:
        retention, reason = "compressed", "Only administrative or hierarchy evidence; operational result unknown."
    elif cosmetic and not re.search(r"customer|outage|data loss", source_text, re.I):
        retention, reason = "compressed", "Cosmetic work compressed; original evidence remains available."
    elif harmed or routine or policy or change:
        retention, reason = "retained", "Preserve supported incident, routine, requirement, or implementation context."
    else:
        retention, reason = "compressed", "Sparse one-off work; retain references for elaboration without prominent recall."
    # Observations and impact precede requirements. Dedupe verbatim repeated excerpts.
    priority = {"reported_impact": 0, "problem": 1, "event": 2, "context_or_action": 3,
                "result_or_intention": 4, "requirement": 5, "intended_action": 6, "verification_request": 7}
    unique = {}
    for e in sorted(substantive, key=lambda e: (priority[_role(e, index)], e["id"])):
        key = normalize(e["source_span"])
        if key in unique:
            unique[key]["evidence_ids"].append(e["id"])
        else:
            unique[key] = claim_for(e, _role(e, index))
    claims = list(unique.values())[:config.max_claims_per_episode] if retention == "retained" else []
    node_ids = sorted({n for e in extracted for n in [e["source_id"], e["target_id"]]})
    entities = [n for n in node_ids if index["nodes"][n]["type"] == "resource"]
    outcomes = [outcome_value(e, index) for e in extracted if e["relation"] == "PRODUCES"]
    flags = sorted({flag for e in rows for flag in e["quality_flags"]})
    uncertainties = [
        "Decision-based episode boundaries are provisional; shared IDs do not prove one occurrence.",
        "Source excerpts are incomplete and may omit later changes or recovery.",
    ]
    if not any(o["valence"] == "beneficial" and o["evidence_status"] == "source_report" for o in outcomes):
        uncertainties.append("No directly supported beneficial result was identified; recovery is unverified.")
    if "closure_is_not_verified_recovery" in flags:
        uncertainties.append("Administrative closure does not verify the operational outcome.")
    episode = {
        "id": stable_id("episode", sorted(decisions)), "type": "episode", "title": title,
        "title_origin": "graph decision labels; not a verified account of completed action",
        "kind": "documented_routine" if routine else "incident_or_change_bundle",
        "decision_ids": sorted(decisions), "node_ids": node_ids, "entity_ids": entities,
        "record_ids": sorted({e["record_id"] for e in extracted}),
        "evidence_ids": [e["id"] for e in extracted],
        "inferred_link_ids": [e["id"] for e in rows if e["status"] == "inferred"],
        "claims": claims, "outcomes": outcomes, "quality_flags": flags,
        "time_evidence": [d for e in extracted for d in e["dates"]],
        "retention": retention, "retention_reason": reason,
        "confidence": "medium" if substantive else "low", "uncertainties": uncertainties,
        "construction": "offline_rules", "summary": "\n".join(c["text"] for c in claims),
        "independent_record_ids": sorted({e["record_id"] for e in substantive
                                           if not e["record_id"].startswith("Community_")}),
    }
    return episode


def build_facts(index):
    facts = {}
    for e in index["evidence"].values():
        if e["status"] not in {"requirement", "source_report"}:
            continue
        span = e["source_span"] or ""
        rule = index["nodes"][e["target_id"]]["type"] == "rule"
        routine = bool(re.search(r"twice daily|two times a day|weekly|monthly|every day", span, re.I))
        change = e["relation"] == "AFFECTS" and bool(re.search(
            r"\b(implemented|increased|merged|migrated|replaced)\b", span, re.I))
        if not (rule or routine or change or (e["status"] == "requirement" and e["relation"] == "AFFECTS")):
            continue
        if len(span) < 15 or len(span) > 1600:
            continue
        kind = "documented_routine" if routine else ("requirement" if e["status"] == "requirement" else "historical_statement")
        # Keep scope: identical wording about different entities is not auto-merged.
        entity = e["target_id"]
        key = (normalize(span), entity, kind)
        if key not in facts:
            fid = stable_id("fact", key)
            facts[key] = {
                "id": fid, "type": "fact", "kind": kind, "title": span,
                "statement": span, "summary": span, "claims": [claim_for(e, kind)],
                "evidence_ids": [], "record_ids": [], "entity_ids": [entity],
                "node_ids": [], "confidence": "medium", "retention": "retained",
                "retention_reason": "Reusable requirement, documented routine, or explicit historical change.",
                "uncertainties": ["Historical source statement; not proof of present-day behavior or consistent execution."],
                "construction": "offline_rules",
            }
        fact = facts[key]
        fact["evidence_ids"].append(e["id"])
        fact["record_ids"].append(e["record_id"])
        fact["node_ids"].extend([e["source_id"], e["target_id"]])
    for fact in facts.values():
        for field in ["evidence_ids", "record_ids", "node_ids"]:
            fact[field] = sorted(set(fact[field]))
        fact["claims"][0]["evidence_ids"] = fact["evidence_ids"][:]
    return sorted(facts.values(), key=lambda f: f["id"])


def build_aliases(index):
    """Technology-family search aids. They never collapse entity identities."""
    families = [
        ("DocumentDB", ["docdb", "documentdb"], r"\b(?:docdb|documentdb)\b"),
        ("Elasticsearch", ["elasticsearch", "ES"], r"\belasticsearch\b"),
        ("Narrative pruning", ["pruning", "hidden narratives", "hiding rules"], r"prun|hidden narratives|hiding rules"),
    ]
    aliases = []
    for family, names, pattern in families:
        matched = [n for n in index["nodes"].values() if n["type"] == "resource" and re.search(pattern, n["label"], re.I)]
        for n in sorted(matched, key=lambda n: n["id"]):
            eids = sorted(set(index["incoming"].get(n["id"], []) + index["outgoing"].get(n["id"], [])))
            label = n["label"].casefold()
            environment = next((v for v, p in [("staging", r"staging"), ("development", r"\bdev\b|development"),
                                                 ("production", r"\bprod\b|production")] if re.search(p, label)), "unspecified")
            aliases.append({"family": family, "aliases": names, "node_id": n["id"],
                            "label": n["label"], "environment": environment, "evidence_ids": eids,
                            "identity_merge": False, "method": "declared terminology family + label match",
                            "limitation": "Shared technology does not establish the same cluster, environment, or tenant."})
    return aliases


def build_memory(data, config=None, *, client=None, index=None, progress=None, checkpoint=None, record_ids=()):
    config = config or BuildConfig()
    if config.mode not in {"offline", "hosted"}:
        raise ValueError("mode must be offline or hosted")
    if config.mode == "hosted" and client is None:
        raise ValueError("Hosted mode requires a configured client; no silent fallback")
    index = normalize_index(data, index, annotate_offline=config.mode == "offline")
    if config.mode == "hosted":
        from .judged import build_judged_memory
        return build_judged_memory(index, config, client, progress=progress, checkpoint=checkpoint, record_ids=record_ids)
    if record_ids:
        raise ValueError("Record selection is supported only for hosted pilots")
    groups, traces = episode_groups(index, config)
    episodes = [ep for group in groups if (ep := build_episode(group, index, config)) is not None]
    facts = build_facts(index)
    memory = {
        "schema_version": "1.0", "episodes": sorted(episodes, key=lambda e: e["id"]),
        "facts": facts, "patterns": [], "evidence": index["evidence"],
        "nodes": index["nodes"], "entity_aliases": build_aliases(index), "traces": traces,
        "build_metadata": {
            "mode": config.mode, "config": asdict(config), "graph_hash": index["graph_hash"],
            "raw_edge_count": index["raw_edge_count"], "node_count": len(index["nodes"]),
            "embedding_space": "supplied 512-dimensional node vectors; encoder unknown",
            "rules_version": "1.0", "hosted_calls": 0,
            "limitations": [
                "Offline mode is extractive and uses declared mechanism hypotheses; no hosted model was called.",
                "Episode boundaries follow decision evidence and can conflate repeated undated occurrences.",
                "Confidence describes support in this export, not independently verified operational truth.",
            ],
        },
    }
    for item in episodes + facts:
        traces.append({"action": "construct_memory_item", "item_id": item["id"],
                       "method": "offline_rules", "evidence_ids": item["evidence_ids"],
                       "retention": item["retention"], "reason": item["retention_reason"]})
    from .patterns import build_patterns
    memory["patterns"], pattern_trace = build_patterns(memory, config.min_pattern_support)
    traces.extend(pattern_trace)
    memory["build_metadata"]["counts"] = {
        "episodes": len(memory["episodes"]), "facts": len(memory["facts"]),
        "patterns": len(memory["patterns"]),
        "episode_retention": dict(Counter(e["retention"] for e in memory["episodes"])),
        "evidence_status": dict(Counter(e["status"] for e in index["evidence"].values())),
    }
    return memory


def get_item(memory, item_id, *, include_evidence=True):
    for kind in ["episodes", "facts", "patterns"]:
        for item in memory[kind]:
            if item["id"] == item_id:
                return {**item, **({"evidence": [memory["evidence"][e] for e in item["evidence_ids"]]}
                                  if include_evidence else {})}
    raise KeyError(f"Unknown memory item: {item_id}")


def save_memory(memory, path):
    path = Path(path)
    incomplete = (memory.get("build_metadata", {}).get("status") == "incomplete"
                  or memory.get("abstraction_metadata", {}).get("status") in {"incomplete", "preview"})
    if incomplete and path.name == "memory.json":
        raise ValueError("Incomplete hosted memory must be saved as a checkpoint, not memory.json")
    from .storage import atomic_json
    atomic_json(path, memory)


def _reviewed_scope(refs, index):
    return {"evidence_ids": sorted(set(refs)),
            "record_ids": sorted({index["evidence"][eid]["record_id"] for eid in refs if index["evidence"][eid]["record_id"]}),
            "node_ids": sorted({n for eid in refs for n in (index["evidence"][eid]["source_id"], index["evidence"][eid]["target_id"])})}
