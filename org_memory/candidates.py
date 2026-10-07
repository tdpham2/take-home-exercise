"""Deterministic structural proposals. No semantic annotation or retention gates."""
from collections import defaultdict

from .evidence import stable_id


class UnionFind:
    def __init__(self, values):
        self.parent = {v: v for v in values}
        self.members = {v: {v} for v in values}

    def find(self, value):
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, a, b, cap=None):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if cap and len(self.members[a] | self.members[b]) > cap:
            return False
        a, b = sorted([a, b])
        self.parent[b] = a
        self.members[a] |= self.members.pop(b)
        return True


def structural_links(index, *, same_record):
    """Only extracted, nonempty dependencies and shared event connections."""
    decisions = {n for n, node in index["nodes"].items() if node["type"] == "decision"}
    events = defaultdict(dict)
    links = []
    for e in sorted(index["evidence"].values(), key=lambda e: e["id"]):
        if e["provenance"]["kind"] != "extracted" or not (e["source_span"] or "").strip():
            continue
        s, t = e["source_id"], e["target_id"]
        if s in decisions and t in decisions and e["relation"] in {"DEPENDS_ON", "CAUSES"}:
            links.append({"decision_ids": [s, t], "evidence_ids": [e["id"]],
                          "reason": "extracted decision dependency"})
        for event, decision in ((s, t), (t, s)):
            if decision in decisions and index["nodes"][event]["type"] == "event":
                key = (e["record_id"] if same_record else "", event)
                events[key].setdefault(decision, []).append(e["id"])
    for (record, event), linked in sorted(events.items()):
        ids = sorted(linked)
        for d in ids[1:]:
            links.append({"decision_ids": [ids[0], d], "event_id": event,
                          "event_degree": len(ids), "record_id": record,
                          "evidence_ids": sorted(linked[ids[0]] + linked[d]),
                          "reason": "shared event in one record" if same_record else "shared event across records"})
    return links


def build_candidates(index, max_decisions=8, *, include_review_units=True):
    if max_decisions < 1:
        raise ValueError("max_decisions must be positive")
    decisions = sorted(n for n, node in index["nodes"].items() if node["type"] == "decision")
    uf, traces = UnionFind(decisions), []
    links = structural_links(index, same_record=True)
    for link in links:
        a, b = link["decision_ids"]
        # A broad event hub does not arbitrarily collect its first eight nodes.
        eligible = link.get("event_degree", 0) <= max_decisions
        joined = eligible and uf.union(a, b, max_decisions)
        traces.append({"action": "candidate_grouping", **link, "joined": bool(joined)})
    candidates = []
    for members in sorted(uf.members.values(), key=lambda m: sorted(m)):
        refs = sorted({eid for d in members for eid in index["incoming"].get(d, []) + index["outgoing"].get(d, [])})
        candidate = {
            "id": stable_id("candidate", sorted(members)), "decision_ids": sorted(members),
            "evidence_ids": refs,
            "record_ids": sorted({index["evidence"][eid]["record_id"] for eid in refs if index["evidence"][eid]["record_id"]}),
            "eligible": any(index["evidence"][eid]["provenance"]["kind"] == "extracted" for eid in refs),
            "grouping_reasons": [t for t in traces if t["joined"] and set(t["decision_ids"]) <= members],
        }
        candidates.append(candidate)
    candidates.sort(key=lambda c: c["id"])
    if not include_review_units:
        return candidates, [], traces
    by_decision = {d: c["id"] for c in candidates if c["eligible"] for d in c["decision_ids"]}
    unit_uf = UnionFind(sorted(set(by_decision.values())))
    unit_links = []
    for link in structural_links(index, same_record=False):
        a, b = (by_decision.get(d) for d in link["decision_ids"])
        if a is not None and b is not None and a != b:
            unit_uf.union(a, b)
            unit_links.append({**link, "candidate_ids": sorted([a, b])})
    units = []
    by_id = {c["id"]: c for c in candidates}
    for members in unit_uf.members.values():
        units.append({"id": stable_id("unit", sorted(members)), "candidate_ids": sorted(members),
                      "evidence_ids": sorted({eid for c in members for eid in by_id[c]["evidence_ids"]}),
                      "connections": [link for link in unit_links if set(link["candidate_ids"]) <= members]})
    return candidates, sorted(units, key=lambda u: u["id"]), traces
