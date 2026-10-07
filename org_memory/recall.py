"""BM25, optional known-encoder dense search, and bounded memory association.

Without a hosted encoder, semantic expansion uses existing node vectors seeded
by lexically matched node labels. It never embeds free text in the unknown
512-dimensional space. That offline limitation is explicit in every trace.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

import numpy as np


STOPWORDS = set("a an and are as at be been but by can for from has have how i in is it its of on or that the their then there these they this to was were what when which with would you".split())


def tokens(text):
    terms = re.findall(r"[a-z0-9]+", text.casefold())
    variants = {"retries": "retry", "retrying": "retry", "jobs": "job", "rules": "rule",
                "narratives": "narrative", "updates": "update", "deleted": "delete",
                "deleting": "delete", "failures": "failure", "stores": "store"}
    return [variants.get(w, w) for w in terms if w not in STOPWORDS and len(w) > 1]


class BM25:
    def __init__(self, texts):
        self.docs = [Counter(tokens(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = sum(self.lengths) / max(1, len(self.docs)) or 1
        df = Counter(word for d in self.docs for word in d)
        n = len(self.docs)
        self.idf = {word: math.log(1 + (n - count + .5) / (count + .5)) for word, count in df.items()}

    def scores(self, query):
        query_terms = set(tokens(query))
        scores = np.zeros(len(self.docs), dtype=np.float64)
        for i, counts in enumerate(self.docs):
            norm = 1.5 * (.25 + .75 * self.lengths[i] / self.average)
            for term in query_terms:
                freq = counts.get(term, 0)
                if freq:
                    scores[i] += self.idf.get(term, 0) * freq * 2.5 / (freq + norm)
        return scores


def unit(matrix):
    matrix = np.asarray(matrix, dtype=np.float32)
    if not np.isfinite(matrix).all():
        raise ValueError("Embedding values must be finite")
    return matrix / np.maximum(np.linalg.norm(matrix, axis=-1, keepdims=True), 1e-12)


def item_text(item):
    return "\n".join([item.get("title", ""), item.get("summary", ""), item.get("kind", "")])


class RecallIndex:
    def __init__(self, memory, node_embeddings=None, *, encoder=None, include_compressed=False):
        self.memory = memory
        self.items = sorted([item for kind in ["episodes", "facts", "patterns"] for item in memory[kind]
                             if include_compressed or item["retention"] == "retained"], key=lambda i: i["id"])
        self.by_id = {item["id"]: item for item in self.items}
        self.positions = {item["id"]: i for i, item in enumerate(self.items)}
        self.lexical = BM25([item_text(item) for item in self.items])
        self.encoder = encoder
        self.dense = unit(encoder.embed([item_text(i) for i in self.items])) if encoder and self.items else None
        self.node_ids = sorted(memory["nodes"])
        self.node_lexical = BM25([memory["nodes"][nid]["label"] for nid in self.node_ids])
        self.node_vectors = None
        self.item_node_vectors = None
        if node_embeddings:
            self.node_vectors = unit([node_embeddings[n] for n in self.node_ids])
            if not np.isfinite(self.node_vectors).all():
                raise ValueError("Node embeddings must be finite")
            node_position = {n: i for i, n in enumerate(self.node_ids)}
            vectors = []
            for item in self.items:
                # Decisions/events/risks describe situations more specifically than generic hubs.
                ids = [n for n in item["node_ids"] if memory["nodes"][n]["type"] in {"decision", "event", "risk"}]
                ids = ids or item["node_ids"]
                vectors.append(np.mean([self.node_vectors[node_position[n]] for n in ids], axis=0)
                               if ids else np.zeros(512))
            self.item_node_vectors = unit(vectors) if vectors else np.zeros((0, 512))
        self.entity_items = defaultdict(set)
        for item in self.items:
            for entity in item["entity_ids"]:
                self.entity_items[entity].add(item["id"])
        self.links = defaultdict(dict)
        for pattern in memory["patterns"]:
            for eid in pattern["supporting_episode_ids"]:
                if eid in self.by_id and pattern["id"] in self.by_id:
                    self.links[eid][pattern["id"]] = (1.0, "supports this cross-episode pattern")
                    self.links[pattern["id"]][eid] = (1.0, "episode supplies evidence for this pattern")
            for fid in pattern.get("supporting_fact_ids", []):
                if fid in self.by_id and pattern["id"] in self.by_id:
                    self.links[fid][pattern["id"]] = (1.0, "supports this cross-record pattern")
                    self.links[pattern["id"]][fid] = (1.0, "fact supplies evidence for this pattern")

    def _neighbors(self, item_id):
        linked = dict(self.links[item_id])
        item = self.by_id[item_id]
        for entity in item["entity_ids"]:
            peers = self.entity_items[entity]
            # High-degree entity hubs are poor associative evidence.
            if len(peers) > 30:
                continue
            weight = .5 / math.log2(2 + len(peers))
            for other in sorted(peers):
                if other != item_id and (other not in linked or linked[other][0] < weight):
                    label = self.memory["nodes"][entity]["label"]
                    linked[other] = (weight, f"shares scoped entity {label} ({entity})")
        return linked

    def recall(self, cue, limit=10, *, max_hops=2, association=True):
        if not isinstance(cue, str) or not cue.strip():
            raise ValueError("cue must be nonempty text")
        if limit < 1 or not 0 <= max_hops <= 2:
            raise ValueError("limit must be positive and max_hops must be between 0 and 2")
        lexical = self.lexical.scores(cue)
        ranks = {"lexical": [int(i) for i in np.argsort(-lexical, kind="stable")[:40] if lexical[i] > 0]}
        semantic_scores = np.zeros(len(self.items))
        anchors = []
        if self.encoder and self.items:
            q = unit(self.encoder.embed([cue]))[0]
            semantic_scores = np.einsum("ij,j->i", self.dense, q)
            ranks["dense"] = [int(i) for i in np.argsort(-semantic_scores, kind="stable")[:40] if semantic_scores[i] > .15]
            mode = "BM25 + hosted text embeddings in one identified encoder space"
        elif self.node_vectors is not None and ranks["lexical"]:
            ns = self.node_lexical.scores(cue)
            selected = [int(i) for i in np.argsort(-ns, kind="stable")[:3] if ns[i] > 0]
            if selected:
                q = unit(np.average(self.node_vectors[selected], axis=0, weights=ns[selected]))
                semantic_scores = np.einsum("ij,j->i", self.item_node_vectors, q)
                ranks["node_association"] = [int(i) for i in np.argsort(-semantic_scores, kind="stable")[:40]
                                             if semantic_scores[i] > .35]
                anchors = [{"node_id": self.node_ids[i], "label": self.memory["nodes"][self.node_ids[i]]["label"],
                            "lexical_score": float(ns[i])} for i in selected]
            mode = "offline BM25 + cue-anchored node similarity; not direct semantic query encoding"
        else:
            mode = "BM25 only"
        scores, paths, routes = defaultdict(float), {}, defaultdict(list)
        for name, order in ranks.items():
            for rank, pos in enumerate(order, 1):
                iid = self.items[pos]["id"]
                scores[iid] += 1 / (60 + rank)
                routes[iid].append(name)
        for iid in list(scores):
            scores[iid] *= {"high": 1, "medium": .85, "low": .65}[self.by_id[iid]["confidence"]]
        seeds = sorted(scores, key=lambda k: (-scores[k], k))[:8]
        seed_scores = {iid: scores[iid] for iid in seeds}
        if association:
            for seed in seeds:
                frontier = [(seed, seed_scores[seed], [seed], [])]
                for _ in range(max_hops):
                    next_frontier = []
                    for current, strength, path, reasons in frontier:
                        peers = self._neighbors(current)
                        for other in sorted(peers, key=lambda k: (-peers[k][0], k))[:20]:
                            if other in path:
                                continue
                            weight, reason = peers[other]
                            score = strength * .6 * weight
                            candidate = {"path": path + [other], "reasons": reasons + [reason], "score": score}
                            if other not in paths or score > paths[other]["score"]:
                                paths[other] = candidate
                            next_frontier.append((other, score, path + [other], reasons + [reason]))
                    frontier = next_frontier[:100]
            for iid, path in paths.items():
                scores[iid] += path["score"]
                routes[iid].append("memory_association")
        results, discarded, seen_claims = [], [], set()
        for iid in sorted(scores, key=lambda k: (-scores[k], k)):
            item = self.by_id[iid]
            fingerprint = (item.get("statement", item.get("summary", "")),
                           tuple(sorted(item.get("entity_ids", []))), item.get("kind"))
            # The same wording about distinct subjects/environments is not a duplicate.
            if item["type"] == "fact" and fingerprint in seen_claims:
                discarded.append({"item_id": iid, "reason": "duplicate fact text, scope, and kind in this result set"})
                continue
            if len(results) >= limit:
                discarded.append({"item_id": iid, "reason": "outside result budget"})
                continue
            if item["type"] == "fact":
                seen_claims.add(fingerprint)
            pos = self.positions[iid]
            results.append({
                "item_id": iid, "type": item["type"], "title": item["title"],
                "summary": item.get("summary", ""), "score": round(scores[iid], 8),
                "confidence": item["confidence"], "record_ids": item["record_ids"],
                "evidence_ids": item["evidence_ids"], "routes": routes[iid],
                "association": paths.get(iid), "lexical_score": float(lexical[pos]),
                "similarity": float(semantic_scores[pos]),
                "why": "; ".join(routes[iid]) + ("; " + " → ".join(paths[iid]["reasons"]) if iid in paths else ""),
            })
        return {"cue": cue, "results": results, "trace": {
            "mode": mode, "anchor_nodes": anchors, "seed_item_ids": seeds,
            "discarded": discarded, "max_hops": max_hops if association else 0,
            "score_note": "RRF k=60; support multipliers 1/.85/.65; association decay .6 per hop. Heuristics, not probabilities.",
        }}


def recall(memory, cue, limit=10, *, index=None, node_embeddings=None):
    index = index or RecallIndex(memory, node_embeddings)
    return index.recall(cue, limit)


def entity_timeline(memory, entity_id):
    if entity_id not in memory["nodes"]:
        raise KeyError(entity_id)
    ids = {eid for item in memory["episodes"] if entity_id in item["node_ids"] for eid in item["evidence_ids"]}
    dated, unplaced = [], []
    for eid in sorted(ids):
        e = memory["evidence"][eid]
        if not e["dates"]:
            unplaced.append({"evidence_id": eid, "record_id": e["record_id"], "reason": "no explicit date"})
        for d in e["dates"]:
            if d["status"] == "explicit_date_mention":
                dated.append({**d, "record_id": e["record_id"], "source_span": e["source_span"]})
            else:
                unplaced.append({**d, "record_id": e["record_id"]})
    return {"entity_id": entity_id, "dated_mentions": sorted(dated, key=lambda d: (d["date"], d["evidence_id"])),
            "unplaced": unplaced,
            "limitation": "Dates are source mentions, not a verified chronology of implementation or recovery."}
