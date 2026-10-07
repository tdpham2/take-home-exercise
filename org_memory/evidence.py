"""One raw-graph traversal; immutable evidence plus explicit derived annotations.

Rules classify the wording of an excerpt, not the truth of an original ticket.
The raw edge is never rewritten. A warning is a review candidate, not a repair.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import defaultdict
from datetime import date


def stable_id(prefix, value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return prefix + "_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.casefold())).strip()


ADMIN = re.compile(r"^(?:(?:status|resolution):\s*done\s*(?:\|\s*)?)+$", re.I)
METADATA = re.compile(r"(?:epic_link_key|parent_key|is_root)\s*:", re.I)
PLANNED = re.compile(
    r"\b(proposed|to be done|required to|needed to|needs? to|we will|we should|"
    r"plan to|aims? to|should|must|expected result|expected behavior|frequency)\b", re.I)
IMPERATIVE = re.compile(
    r"^(?:implement|add|fix|update|create|run|log|notify|alert|validate|verify|"
    r"investigate|restrict|ensure|remove|enable|disable|perform|execute|design|define)\b", re.I)
OBSERVED = re.compile(
    r"\b(?:was|were|has been|have been|implemented|merged|deployed|resolved|"
    r"completed|observed|stopped|occurred|identified and fixed)\b", re.I)
HARM = re.compile(
    r"\b(?:outage|missing|degraded|failing|failure|failed|killed|terminated|"
    r"incomplete|inconsistent|drift|mismatch|does not|did not|not caught|no action|"
    r"no automated alarm|no output|without .*updates)\b", re.I)
BENEFIT = re.compile(
    r"\b(?:restored|resolved|fixed|working as expected|successfully|passed|"
    r"implemented|merged|completed|deployed)\b", re.I)


def classify_evidence(edge, provenance):
    if provenance["kind"] == "inferred":
        return "inferred"
    span = (provenance.get("source_span") or "").strip()
    if not span:
        return "missing"
    if ADMIN.fullmatch(span):
        return "administrative"
    if METADATA.search(span):
        return "structural_metadata"
    if re.match(r"^[A-Z]{2,8}-\d+\s*[–—-]", span):
        return "cross_reference"
    if re.search(r"^\s*(?:retest(?:ing)?|QA\s*[:–-].*retest)\b", span, re.I) and not re.search(
            r"\b(passed|verified|working as expected)\b", span, re.I):
        return "verification_request"
    if re.search(r"\b(?:acceptance criteria|scope of testing|proposed fix|ensure robust|add guardrails|"
                 r"add logic|create dashboards|expose metrics|define clear|design the)\b", span, re.I):
        return "requirement" if edge["target"]["type"] == "rule" else "intended"
    # A mixed excerpt with expectations is not promoted wholesale to observation.
    if PLANNED.search(span):
        return "requirement" if edge["target"]["type"] == "rule" or re.search(
            r"\b(should|must|expected|frequency)\b", span, re.I) else "intended"
    if IMPERATIVE.search(span):
        return "requirement" if edge["target"]["type"] == "rule" else "intended"
    if re.search(r"\b(likely|possibly|suspect|may be|might be)\b", span, re.I):
        return "uncertain_report"
    return "source_report"


def quality_flags(edge, provenance, status):
    flags = []
    relation = edge["relation"]["type"]
    span = provenance.get("source_span") or ""
    if status == "inferred":
        flags.append("automated_cross_record_inference")
    if relation == "PRODUCES":
        if status == "administrative":
            flags.append("closure_is_not_verified_recovery")
        if status in {"intended", "requirement"}:
            flags.append("intended_outcome_is_not_observed")
        if HARM.search(span):
            flags.append("causal_attribution_requires_review")
    if relation.startswith("SUPERSEDES"):
        if re.search(r"\bretest(?:ing)?\b", span, re.I):
            flags.append("retest_does_not_establish_supersession")
        elif not re.search(r"\b(replaces?|supersedes?|instead of|no longer)\b", span, re.I):
            flags.append("supersession_not_explicit_in_excerpt")
    if status == "structural_metadata":
        flags.append("hierarchy_metadata_is_not_operational_evidence")
    return flags


MONTHS = {name.casefold(): i for i, name in enumerate([
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))


def date_mentions(text, evidence_id, status):
    """Normalize only dates with an explicit year in their own match.

    A month/day without a year stays unplaced, even when another edge has a year.
    Mention order is never treated as event order or intervention completion.
    """
    found = []
    matches = list(re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text))
    for m in matches:
        try:
            value = date(*map(int, m.groups())).isoformat()
        except ValueError:
            continue
        found.append({"raw": m.group(), "date": value, "evidence_id": evidence_id})
    pat = rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:\s*[–-]\s*(\d{{1,2}}))?(?:,?\s+(20\d{{2}}))?\b"
    for m in re.finditer(pat, text, re.I):
        month, start, end, year = m.groups()
        value = None
        end_value = None
        if year:
            try:
                value = date(int(year), MONTHS[month.casefold()], int(start)).isoformat()
                if end:
                    end_value = date(int(year), MONTHS[month.casefold()], int(end)).isoformat()
            except ValueError:
                continue
        found.append({"raw": m.group(), "date": value, "end_date": end_value,
                      "evidence_id": evidence_id})
    for item in found:
        item["status"] = "tentative_inference" if status == "inferred" else (
            "unplaced_without_year" if item["date"] is None else "explicit_date_mention")
        item["event_role"] = "unspecified; a date mention is not a verified event timestamp"
        item["approximate"] = bool(re.search(r"approximately|\babout\b|~", text, re.I))
    return found


def index_graph(data, annotate_offline=True):
    """Index every original edge once, preserving directed parallel relations."""
    nodes, evidence = {}, {}
    by_record, incoming, outgoing = defaultdict(list), defaultdict(list), defaultdict(list)
    for position, edge in enumerate(data["graph"]):
        for side in ("source", "target"):
            node = edge[side]
            if node["id"] in nodes and nodes[node["id"]] != node:
                raise ValueError(f"Conflicting node payload for {node['id']}")
            nodes[node["id"]] = copy.deepcopy(node)
        p = json.loads(edge["relation"]["provenance"])
        if not isinstance(p, dict) or p.get("kind") not in {"extracted", "inferred"}:
            raise ValueError("Unknown provenance kind")
        if any(p.get(field) is not None and not isinstance(p[field], str) for field in ("source_span", "rationale")):
            raise ValueError("Source excerpts and inferred rationales must be strings or null")
        record_id = edge["relation"].get("record_id", "")
        if p["kind"] == "extracted" and (not record_id or p.get("record_id") != record_id):
            raise ValueError("Extracted evidence must have matching record identifiers")
        eid = stable_id("ev", edge)
        if eid in evidence:
            evidence[eid]["raw_positions"].append(position)
            continue
        text = (p.get("source_span") or "") if p["kind"] == "extracted" else (p.get("rationale") or "")
        item = {
            "id": eid, "source_id": edge["source"]["id"], "target_id": edge["target"]["id"],
            "relation": edge["relation"]["type"], "record_id": record_id,
            "provenance": p, "source_span": p.get("source_span"),
            "dates": date_mentions(text, eid, p["kind"]), "raw_positions": [position],
            "raw_edge": copy.deepcopy(edge),
        }
        if annotate_offline:
            status = classify_evidence(edge, p)
            item.update(status=status, quality_flags=quality_flags(edge, p, status))
        evidence[eid] = item
        if record_id:
            by_record[record_id].append(eid)
        outgoing[item["source_id"]].append(eid)
        incoming[item["target_id"]].append(eid)
    if set(nodes) != set(data["id2embeddings"]):
        raise ValueError("Embedding IDs must match graph node IDs")
    lengths = {len(v) for v in data["id2embeddings"].values()}
    if lengths != {512}:
        raise ValueError(f"Expected 512-dimensional embeddings, got {lengths}")
    return {
        "nodes": nodes, "evidence": evidence, "by_record": dict(by_record),
        "incoming": dict(incoming), "outgoing": dict(outgoing),
        "graph_hash": stable_id("graph", data["graph"]),
        "raw_edge_count": len(data["graph"]),
    }


def normalize_index(data, index, *, annotate_offline):
    """Validate supplied structural indexes and return a mode-specific owned copy.

    Reindexing also checks embeddings and original provenance. Derived semantic
    fields are never trusted or carried from an offline index into hosted mode.
    """
    canonical = index_graph(data, annotate_offline=annotate_offline)
    if index is not None:
        for field in ("nodes", "by_record", "incoming", "outgoing", "graph_hash", "raw_edge_count"):
            if index.get(field) != canonical[field]:
                raise ValueError(f"Supplied index differs from graph: {field}")
        if set(index.get("evidence", {})) != set(canonical["evidence"]):
            raise ValueError("Supplied index has different evidence IDs")
        for eid, original in canonical["evidence"].items():
            for field, value in original.items():
                if field not in {"status", "quality_flags", "dates"} and index["evidence"][eid].get(field) != value:
                    raise ValueError(f"Supplied index differs from graph: {eid}.{field}")
    return canonical
