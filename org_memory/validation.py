"""Structural checks plus conservative guardrails; not a semantic truth oracle."""
from .evidence import stable_id
from .patterns import independent_support


def _validate_offline(memory, *, raise_on_error=False):
    errors = []
    evidence = memory["evidence"]
    nodes = memory["nodes"]
    all_items = [item for k in ["episodes", "facts", "patterns"] for item in memory[k]]
    if len({i["id"] for i in all_items}) != len(all_items):
        errors.append("Duplicate memory item IDs")
    for eid, e in evidence.items():
        if eid != stable_id("ev", e["raw_edge"]):
            errors.append(f"Modified raw evidence: {eid}")
        for node in [e["source_id"], e["target_id"]]:
            if node not in nodes:
                errors.append(f"Missing node: {node}")
    for item in all_items:
        if not item["evidence_ids"]:
            errors.append(f"Uncited item: {item['id']}")
        for eid in item["evidence_ids"]:
            if eid not in evidence:
                errors.append(f"Unknown evidence: {eid}")
        for claim in item["claims"]:
            if not claim["evidence_ids"] or not set(claim["evidence_ids"]) <= set(item["evidence_ids"]):
                errors.append(f"Unresolvable claim in {item['id']}")
            if claim["method"] == "verbatim_excerpt":
                if not any(claim["text"] == evidence[eid]["source_span"] for eid in claim["evidence_ids"] if eid in evidence):
                    errors.append(f"Nonverbatim extract in {item['id']}")
            if claim["status"] == "source_report":
                usable = [evidence[eid]["status"] for eid in claim["evidence_ids"] if eid in evidence]
                if not any(s == "source_report" for s in usable):
                    errors.append(f"Unsupported observation in {item['id']}")
        for node in item["node_ids"]:
            if node not in nodes:
                errors.append(f"Unknown node in {item['id']}: {node}")
        if not set(item["entity_ids"]) <= set(item["node_ids"]):
            errors.append(f"Ungrounded entity scope in {item['id']}")
    for ep in memory["episodes"]:
        for o in ep["outcomes"]:
            if o["evidence_status"] != "source_report" and (o["valence"] != "unknown" or o["signed_impact"] is not None):
                errors.append(f"Non-observed outcome promoted in {ep['id']}")
        for d in ep["time_evidence"]:
            if d["date"] is not None and d["status"] == "unplaced_without_year":
                errors.append(f"Fabricated year in {ep['id']}")
    episodes = {ep["id"]: ep for ep in memory["episodes"]}
    for p in memory["patterns"]:
        if len(p["supporting_episode_ids"]) < 2:
            errors.append(f"Pattern without two episodes: {p['id']}")
            continue
        if any(eid not in episodes for eid in p["supporting_episode_ids"]):
            errors.append(f"Missing pattern episode: {p['id']}")
            continue
        candidates = [(episodes[eid], p["support_by_episode"][eid]) for eid in p["supporting_episode_ids"]]
        for ep, refs in candidates:
            if not set(refs) <= set(ep["evidence_ids"]):
                errors.append(f"Pattern support outside episode: {p['id']}")
        selected, rejected = independent_support(memory, candidates)
        if rejected or len(selected) != p["independent_support_count"]:
            errors.append(f"Inflated independence count: {p['id']}")
    for alias in memory["entity_aliases"]:
        if alias["identity_merge"]:
            errors.append("Terminology-family alias incorrectly merged entity identities")
    result = {"passed": not errors, "errors": errors, "items_checked": len(all_items),
              "evidence_checked": len(evidence),
              "limitation": "Structural checks cannot establish semantic entailment or real-world truth."}
    if errors and raise_on_error:
        raise ValueError("\n".join(errors))
    return result


def validate_memory(memory, *, raise_on_error=False):
    return _validate_memory(memory, raise_on_error=raise_on_error)


def validate_checkpoint(memory, *, raise_on_error=False):
    """Replay every available base judgment while allowing explicitly missing work.

    This validates a schema 3.0 checkpoint's integrity, never its completion.
    """
    if memory.get("schema_version") != "3.0":
        raise ValueError("Checkpoint validation requires hosted schema 3.0")
    return _validate_memory(memory, raise_on_error=raise_on_error, allow_incomplete=True)


def _validate_memory(memory, *, raise_on_error=False, allow_incomplete=False):
    version = memory.get("schema_version")
    if version == "3.1":
        from .abstraction import validate_enriched
        return validate_enriched(memory, raise_on_error=raise_on_error)
    if version == "1.0":
        return _validate_offline(memory, raise_on_error=raise_on_error)
    if version != "3.0":
        result = {"passed": False, "errors": ["Unsupported memory schema; rebuild hosted schema 2.0 artifacts as 3.0."],
                  "items_checked": 0, "evidence_checked": 0}
        if raise_on_error:
            raise ValueError(result["errors"][0])
        return result
    import json
    from collections import defaultdict
    from .judged import construct_items, coverage, prepare
    from .evidence import date_mentions
    from .review import CONTRACT_VERSION, ROW_SCHEMAS, make_packet, requested_ids, validate_judgments
    errors = []
    evidence, nodes = memory["evidence"], memory["nodes"]
    items = [i for kind in ("episodes", "facts", "patterns") for i in memory[kind]]
    if len({i["id"] for i in items}) != len(items):
        errors.append("Duplicate memory item IDs")
    positions = {}
    index = {"evidence": evidence, "nodes": nodes, "incoming": defaultdict(list), "outgoing": defaultdict(list)}
    for eid, e in evidence.items():
        try:
            raw = e["raw_edge"]
            if eid != stable_id("ev", raw) or eid != e["id"]:
                errors.append(f"Modified raw evidence: {eid}")
            if "status" in e or "quality_flags" in e:
                errors.append(f"Heuristic annotation leaked into hosted evidence: {eid}")
            provenance = json.loads(raw["relation"]["provenance"])
            if provenance != e["provenance"] or e["source_span"] != provenance.get("source_span"):
                errors.append(f"Changed provenance: {eid}")
            if e["relation"] != raw["relation"]["type"] or e["record_id"] != raw["relation"].get("record_id", ""):
                errors.append(f"Changed relationship: {eid}")
            if provenance["kind"] == "extracted" and (not e["record_id"] or provenance.get("record_id") != e["record_id"]):
                errors.append(f"Inconsistent record provenance: {eid}")
            if provenance["kind"] not in {"extracted", "inferred"}:
                errors.append(f"Unknown provenance kind: {eid}")
            text = (e["source_span"] or "") if provenance["kind"] == "extracted" else (provenance.get("rationale") or "")
            if e["dates"] != date_mentions(text, eid, provenance["kind"]):
                errors.append(f"Changed date provenance: {eid}")
            for side in ("source", "target"):
                if raw[side]["id"] != e[f"{side}_id"] or nodes.get(e[f"{side}_id"]) != raw[side]:
                    errors.append(f"Modified or missing raw node: {eid}")
            for pos in e["raw_positions"]:
                if not isinstance(pos, int) or pos in positions:
                    errors.append(f"Duplicate or invalid edge position: {eid}")
                positions[pos] = raw
            index["incoming"][e["target_id"]].append(eid)
            index["outgoing"][e["source_id"]].append(eid)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"Malformed evidence {eid}: {type(exc).__name__}")
    metadata = memory["build_metadata"]
    if set(positions) != set(range(metadata["raw_edge_count"])):
        errors.append("Raw edge archive coverage differs from input")
    elif stable_id("graph", [positions[i] for i in range(len(positions))]) != metadata["graph_hash"]:
        errors.append("Raw graph fingerprint differs from input")
    if set(nodes) != {raw[side]["id"] for raw in positions.values() for side in ("source", "target")}:
        errors.append("Node archive differs from raw graph")
    if metadata.get("status") != "complete" and not (allow_incomplete and metadata.get("status") == "incomplete"):
        errors.append("Hosted build is incomplete")
    if not errors:
        try:
            candidates, proposals, jobs, _ = prepare(index, metadata["config"]["max_episode_decisions"],
                                                    metadata.get("selection_record_ids", []))
            if metadata.get("judging_contract") != CONTRACT_VERSION:
                raise ValueError("Unknown judging contract")
            if memory["candidates"] != candidates or memory["judge_jobs"] != jobs or memory["proposals"] != proposals:
                raise ValueError("Candidate membership or evidence assignment changed")
            by_job = {j["id"]: j for j in jobs}
            seen = {f: set() for f in ROW_SCHEMAS}
            for review in memory["reviews"]:
                if not review["job_ids"] or not isinstance(review["request_id"], str) or not review["request_id"].strip():
                    raise ValueError("Missing review request provenance")
                batch = [by_job[j] for j in review["job_ids"]]
                allowed = requested_ids(batch, proposals)
                requested = {f: [r["id"] for r in review["output"][f]] for f in ROW_SCHEMAS}
                for f, ids in requested.items():
                    if seen[f] & set(ids) or not set(ids) <= set(allowed[f]):
                        raise ValueError("Duplicate or unexpected accepted verdict")
                    seen[f].update(ids)
                packet = make_packet(index, batch, candidates, proposals, requested)
                validate_judgments(review["output"], packet, index)
            require_complete = not allow_incomplete or metadata.get("status") == "complete"
            if require_complete and any(seen[f] != set(ids) for f, ids in requested_ids(jobs, proposals).items()):
                raise ValueError("Not every requested proposal was judged exactly once")
            expected = construct_items(index, candidates, proposals, memory["reviews"])
            for field, value in expected.items():
                if memory.get(field) != value:
                    raise ValueError(f"Final {field} differ from validated judgments")
            expected_coverage = coverage(candidates, proposals, jobs, memory["reviews"])
            if metadata["coverage"] != expected_coverage:
                raise ValueError("Incorrect hosted judgment coverage")
            if memory["patterns"] or metadata["pattern_analysis"]["status"] != "deferred":
                raise ValueError("Hosted pattern synthesis must remain deferred")
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"Judgment validation: {exc}")
    if any(a["identity_merge"] for a in memory["entity_aliases"]):
        errors.append("Terminology aliases merged identities")
    result = {"passed": not errors, "errors": errors, "items_checked": len(items), "evidence_checked": len(evidence),
              "limitation": "Structural validation cannot establish semantic entailment or real-world truth."}
    if errors and raise_on_error:
        raise ValueError("\n".join(errors))
    return result
