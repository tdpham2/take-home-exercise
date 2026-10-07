"""Read-only dataset operations; LangChain only supplies schemas and dispatch."""
from collections import deque
import re
from typing import Literal

import numpy as np
from langchain_core.tools import StructuredTool

from org_memory.recall import BM25, RecallIndex


def page(rows, offset=0, limit=20):
    if offset < 0 or not 1 <= limit <= 20:
        raise ValueError("offset must be nonnegative; limit must be 1..20")
    end = min(len(rows), offset + limit)
    return {"results": rows[offset:end], "total": len(rows),
            "next_offset": end if end < len(rows) else None}


def text_of(evidence):
    return (evidence.get("source_span") or "") if evidence["provenance"]["kind"] == "extracted" else (evidence["provenance"].get("rationale") or "")


class DatasetTools:
    def __init__(self, artifacts, *, tool_profile="full"):
        if tool_profile not in {"full", "graph_only"}:
            raise ValueError("Unknown tool profile")
        self.tool_profile = tool_profile
        self.index = artifacts.index
        self.memory = artifacts.memory if tool_profile == "full" else None
        self.items = {i["id"]: i for group in ("episodes", "facts", "patterns", "outcome_assessments")
                      for i in self.memory[group]} if self.memory is not None else {}
        self.recall_indexes = {False: RecallIndex(self.memory, artifacts.graph["id2embeddings"]),
                               True: RecallIndex(self.memory, artifacts.graph["id2embeddings"], include_compressed=True)} if self.memory is not None else {}
        self.eids = sorted(self.index["evidence"])
        self.nids = sorted(self.index["nodes"])
        self.evidence_bm25 = BM25([text_of(self.index["evidence"][eid]) for eid in self.eids])
        self.node_bm25 = BM25([self.index["nodes"][nid]["label"] for nid in self.nids])

    def expand(self, cue):
        if self.memory is None:
            return cue
        expansions = []
        for alias in self.memory["entity_aliases"]:
            if any(re.search(r"\b" + re.escape(a) + r"\b", cue, re.I) for a in alias["aliases"]):
                expansions.extend(alias["aliases"])
        return " ".join([cue, *sorted(set(expansions))])

    def excerpt(self, eid, start=0, chars=800):
        e = self.index["evidence"][eid]
        text = text_of(e)
        if not 0 <= start <= len(text) or not 1 <= chars <= 4000:
            raise ValueError("Invalid excerpt offset or character limit (1..4000)")
        end = min(len(text), start + chars)
        return {"evidence_id": eid, "record_id": e["record_id"], "provenance_kind": e["provenance"]["kind"],
                "source_id": e["source_id"], "target_id": e["target_id"], "relation": e["relation"],
                "quote": text[start:end], "start": start, "end": end, "total_chars": len(text),
                "next_start": end if end < len(text) else None, "dates": e["dates"],
                "limitation": "Extracted text can contain plans or administrative closure; inferred rationale is not original source testimony."}

    def card(self, item):
        summary = item.get("summary", item.get("reason", ""))
        result = {k: item[k] for k in ("id", "type", "kind", "retention", "confidence", "evidence_ids", "record_ids", "entity_ids",
                    "observed", "valence", "impact", "signed_impact", "independent_support_count", "supporting_episode_ids", "supporting_fact_ids") if k in item}
        result.update(item_id=item["id"], title=item.get("title", "")[:500], preview=summary[:800],
                      preview_truncated=len(summary) > 800,
                      title_origin=item.get("title_origin", "memory item"))
        for key, value in list(result.items()):
            if isinstance(value, list) and len(value) > 20:
                result[key] = value[:20]
                result[key + "_total"] = len(value)
                result[key + "_truncated"] = True
        return result

    def recall_memory(self, cue: str, limit: int = 6, include_compressed: bool = False) -> dict:
        """Recall memory entry points by cue. Inspect useful IDs for evidence before citing them."""
        if not 1 <= limit <= 20:
            raise ValueError("limit must be 1..20")
        expanded = self.expand(cue)
        response = self.recall_indexes[include_compressed].recall(expanded, limit)
        rows = []
        for row in response["results"]:
            rows.append({**self.card(self.items[row["item_id"]]),
                         **{k: row[k] for k in ("score", "routes", "association", "why")}})
        return {"cue": cue, "expanded_cue": expanded, "results": rows, "trace": response["trace"],
                "limitation": "Aliases expand vocabulary, not identity. Scores and memory judgments are fallible."}

    def inspect_memory(self, item_id: str, offset: int = 0, limit: int = 6) -> dict:
        """Elaborate an episode, fact, pattern, or outcome with paginated original evidence and uncertainty."""
        item = self.items[item_id]
        refs = sorted(set(item["evidence_ids"]) | set(item.get("counterevidence_evidence_ids", [])))
        selected = page(refs, offset, limit)
        details = {k: item[k] for k in ("retention_reason", "uncertainties", "uncertainty", "comparison_insight",
                   "differences_counterevidence",
                   "causal_attribution", "limitation", "reason") if k in item}
        counter = set(item.get("counterevidence_evidence_ids", []))
        return {**self.card(item), **details,
                "counterevidence_count": len(counter),
                "evidence": [{**self.excerpt(eid, chars=1200),
                              "memory_role": "counterevidence" if eid in counter else "source_or_support"}
                             for eid in selected["results"]],
                "next_offset": selected["next_offset"], "total_evidence": len(refs),
                "limitation": "Grouping and fact classification are Task 1 judgments, not independent verification. Inspect source wording."}

    def list_patterns(self, cue: str | None = None, offset: int = 0, limit: int = 20) -> dict:
        """List stored comparisons with support counts. Schema 3.0 has no generated patterns."""
        items = self.memory["patterns"]
        if cue:
            scores = BM25([i["summary"] for i in items]).scores(self.expand(cue))
            items = [items[i] for i in np.argsort(-scores, kind="stable") if scores[i] > 0]
        return {"available": self.memory["schema_version"] == "3.1", **page([self.card(i) for i in items], offset, limit),
                "limitation": "Question-focused comparisons do not establish prevalence. Inspect each pattern's counterevidence and uncertainty."}

    def list_outcomes(self, entity_id: str | None = None, observed: bool | None = None,
                      valence: Literal["harmful", "beneficial", "mixed", "unknown"] | None = None,
                      offset: int = 0, limit: int = 20) -> dict:
        """List top-level outcome judgments, including those outside accepted episodes. Impact is ordinal, not measured utility."""
        if entity_id and entity_id not in self.index["nodes"]:
            raise ValueError("Unknown entity ID")
        rows = [self.card(o) for o in self.memory["outcome_assessments"]
                if (not entity_id or entity_id in o["node_ids"]) and (observed is None or o["observed"] == observed)
                and (valence is None or o["valence"] == valence)]
        return {**page(rows, offset, limit), "limitation": "PRODUCES and administrative Done do not establish recovery or causality. Judgments can be wrong."}

    def memory_timeline(self, entity_id: str, offset: int = 0, limit: int = 20) -> dict:
        """Return explicit dated mentions and separately unplaced evidence from episodes, facts, and outcomes; ticket IDs are not dates."""
        if entity_id not in self.index["nodes"]:
            raise ValueError("Unknown entity ID")
        links = {}
        for item in self.items.values():
            if item.get("type") == "pattern" or entity_id not in item.get("node_ids", []):
                continue
            for eid in item["evidence_ids"]:
                links.setdefault(eid, []).append(item["id"])
        dated, unplaced = [], []
        for eid in sorted(links):
            e = self.index["evidence"][eid]
            dates = e["dates"] or [{"status": "unplaced", "reason": "no explicit date"}]
            for date in dates:
                row = {**date, "evidence_id": eid, "record_id": e["record_id"], "memory_ids": links[eid]}
                (dated if date["status"] == "explicit_date_mention" else unplaced).append(row)
        dated.sort(key=lambda d: (d["date"], d["evidence_id"]))
        return {"dated": page(dated, offset, limit), "unplaced": page(unplaced, offset, limit),
                "limitation": "Dates are mentions, not verified incident, deployment, or recovery chronology. Inspect source evidence."}

    def search_graph(self, query: str, mode: Literal["both", "records", "entities"] = "both", offset: int = 0, limit: int = 10) -> dict:
        """Search original passages or node labels. Labels and inferred rationales are unverified; use distinct node IDs."""
        if not query.strip():
            raise ValueError("query must be nonempty")
        expanded = self.expand(query)
        normalized = re.sub(r"[^a-z0-9]", "", query.casefold())
        records, entities = [], []
        if mode != "entities":
            scores = self.evidence_bm25.scores(expanded)
            for i in np.argsort(-scores, kind="stable"):
                eid = self.eids[i]
                exact = re.sub(r"[^a-z0-9]", "", self.index["evidence"][eid]["record_id"].casefold()) == normalized
                if scores[i] > 0 or exact:
                    records.append((not exact, -float(scores[i]), eid))
            records.sort()
        if mode != "records":
            scores = self.node_bm25.scores(expanded)
            entities = [{**self.index["nodes"][self.nids[i]], "label_status": "unverified graph label"}
                        for i in np.argsort(-scores, kind="stable") if scores[i] > 0 or self.nids[i] == query]
        result = {"expanded_query": expanded, "records": page(records, offset, limit), "entities": page(entities, offset, limit)}
        result["records"]["results"] = [self.excerpt(row[2]) for row in result["records"]["results"]]
        return result

    def graph_neighborhood(self, node_id: str, direction: Literal["both", "incoming", "outgoing"] = "both",
                           relations: list[str] | None = None, offset: int = 0, limit: int = 40) -> dict:
        """Inspect one-hop relationships, keeping incoming/outgoing directions and extracted/inferred provenance separate."""
        if node_id not in self.index["nodes"]:
            raise ValueError("Unknown node ID")
        if offset < 0 or not 1 <= limit <= 40:
            raise ValueError("offset must be nonnegative; limit must be 1..40")
        refs = set()
        for side in ("incoming", "outgoing"):
            if direction in ("both", side):
                refs.update(self.index[side].get(node_id, []))
        refs = sorted(e for e in refs if not relations or self.index["evidence"][e]["relation"] in relations)
        end = min(len(refs), offset + limit)
        return {"node": self.index["nodes"][node_id], "results": [self.excerpt(e, chars=400) for e in refs[offset:end]],
                "total": len(refs), "next_offset": end if end < len(refs) else None}

    def graph_paths(self, source_id: str, target_id: str, max_hops: int = 3, limit: int = 3,
                    direction: Literal["forward", "either"] = "either") -> dict:
        """Find bounded simple connecting paths. Original arrows are preserved; connectivity does not establish cause."""
        if source_id not in self.index["nodes"] or target_id not in self.index["nodes"]:
            raise ValueError("Unknown endpoint ID")
        if not 1 <= max_hops <= 3 or not 1 <= limit <= 3:
            raise ValueError("max_hops and limit must be 1..3")
        queue, paths, visited_edges = deque([(source_id, [source_id], [])]), [], 0
        while queue and len(paths) < limit and visited_edges < 1000:
            node, nodes, edges = queue.popleft()
            if node == target_id:
                paths.append({"node_ids": nodes, "edges": edges})
                continue
            if len(edges) == max_hops:
                continue
            refs = set(self.index["outgoing"].get(node, []))
            if direction == "either":
                refs.update(self.index["incoming"].get(node, []))
            for eid in sorted(refs):
                if visited_edges >= 1000:
                    break
                visited_edges += 1
                e = self.index["evidence"][eid]
                forward = e["source_id"] == node
                other = e["target_id"] if forward else e["source_id"]
                if other not in nodes:
                    queue.append((other, nodes + [other], edges + [{**self.excerpt(eid, chars=300), "traversed_forward": forward}]))
        return {"paths": paths, "examined_edges": visited_edges, "search_truncated": bool(queue) or visited_edges >= 1000,
                "limitation": "Bounded connectivity search, not a causal argument or exhaustive proof of absence."}

    def get_evidence(self, evidence_ids: list[str], start: int = 0, chars: int = 4000) -> dict:
        """Fetch exact original text with offsets for citation. Use next_start for long text; inferred rationale stays labeled."""
        if not 1 <= len(evidence_ids) <= 6:
            raise ValueError("Request 1..6 evidence IDs")
        return {"results": [self.excerpt(eid, start, chars) for eid in dict.fromkeys(evidence_ids)]}

    def registered(self):
        if self.tool_profile == "graph_only":
            return [StructuredTool.from_function(getattr(self, name)) for name in
                    ("search_graph", "graph_neighborhood", "graph_paths", "get_evidence")]
        names = ("recall_memory", "inspect_memory", "list_patterns", "list_outcomes", "memory_timeline",
                 "search_graph", "graph_neighborhood", "graph_paths", "get_evidence")
        return [StructuredTool.from_function(getattr(self, name)) for name in names]
