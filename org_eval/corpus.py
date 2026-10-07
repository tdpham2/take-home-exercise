"""Text retrieval over source records, without memory or graph assertions."""
from collections import defaultdict

from org_memory.recall import BM25
from .common import fingerprint


class TextCorpus:
    def __init__(self, source):
        self.source = source
        grouped = defaultdict(lambda: defaultdict(list))
        for eid, evidence in sorted(source.index["evidence"].items()):
            text = evidence.get("source_span") or ""
            if evidence["provenance"]["kind"] == "extracted" and text.strip():
                grouped[evidence["record_id"]][text].append(eid)
        self.records = []
        for rid, passages in sorted(grouped.items()):
            self.records.append({"record_id": rid, "passages": [
                {"evidence_id": ids[0], "equivalent_evidence_ids": ids, "record_id": rid,
                 "quote": text, "start": 0, "end": len(text)}
                for text, ids in sorted(passages.items(), key=lambda pair: pair[1][0])]})
        self.by_record = {r["record_id"]: r for r in self.records}
        self.bm25 = BM25([" ".join([r["record_id"], *[p["quote"] for p in r["passages"]]])
                          for r in self.records])
        self.fingerprint = fingerprint(self.records)

    def search(self, query, limit=20):
        if not query.strip() or limit < 1:
            raise ValueError("Search needs a nonempty query and a positive limit")
        scores = self.bm25.scores(query)
        order = sorted(range(len(self.records)), key=lambda i: (-float(scores[i]), self.records[i]["record_id"]))
        return [{**self.records[i], "score": float(scores[i])} for i in order if scores[i] > 0][:limit]

    def passage(self, eid):
        e = self.source.index["evidence"].get(eid)
        if e is None or e["provenance"]["kind"] != "extracted":
            raise ValueError(f"Expected original extracted evidence: {eid}")
        return {"evidence_id": eid, "record_id": e["record_id"], "quote": e.get("source_span") or "",
                "start": 0, "end": len(e.get("source_span") or "")}

    def aliases(self, eid):
        e = self.source.index["evidence"][eid]
        return {p for r in self.by_record[e["record_id"]]["passages"]
                if r["quote"] == e["source_span"] for p in r["equivalent_evidence_ids"]}
