"""Frozen, validated Task 1 inputs. Loading never opens a model connection."""
from dataclasses import dataclass
import json
from pathlib import Path

from org_memory import validate_memory
from org_memory.evidence import index_graph, stable_id


PREVIEW_NOTICE = ("Provisional agent test on a frozen, partially reviewed memory and selected abstraction packets. "
                  "The raw graph remains available in full. Missing memory items do not establish absence from the records; "
                  "this is not a completed-memory evaluation.")


@dataclass(frozen=True)
class SourceArtifacts:
    """Raw inputs only: constructing this object never reads organizational memory."""
    graph: dict
    index: dict
    identity: dict

    @classmethod
    def load(cls, graph_path):
        graph = json.loads(Path(graph_path).read_text())
        index = index_graph(graph, annotate_offline=False)
        return cls(graph, index, {
            "graph_hash": index["graph_hash"],
            "embedding_fingerprint": stable_id("embeddings", graph["id2embeddings"]),
            "execution_scope": "source_only",
        })


@dataclass(frozen=True)
class Artifacts:
    memory: dict
    graph: dict
    index: dict
    identity: dict

    @classmethod
    def load(cls, graph_path, memory_path, *, preview=False):
        memory_path = Path(memory_path)
        if memory_path.name.endswith(".incomplete.json"):
            raise ValueError("Agent requires a completed memory artifact, not an incomplete checkpoint")
        memory = json.loads(memory_path.read_text())
        if not isinstance(memory, dict):
            raise ValueError("Memory artifact must be a JSON object")
        meta = memory.get("build_metadata", {})
        enriched = memory.get("abstraction_metadata", {})
        if memory.get("schema_version") not in {"3.0", "3.1"}:
            raise ValueError("Agent supports hosted memory schemas 3.0 and 3.1")
        if preview:
            if (memory["schema_version"] != "3.1" or enriched.get("execution_scope") != "preview"
                    or enriched.get("status") != "preview" or enriched.get("preview_status") != "complete"
                    or meta.get("scope") != "full_graph" or meta.get("status") not in {"complete", "incomplete"}):
                raise ValueError("--preview requires a finished abstraction preview over a frozen full_graph base")
        elif enriched.get("execution_scope") == "preview":
            raise ValueError("Provisional abstraction requires explicit --preview (Python: preview=True)")
        elif meta.get("status") != "complete" or meta.get("scope") != "full_graph":
            raise ValueError("Agent requires completed full_graph memory; incomplete and pilot inputs are ineligible")
        if memory["schema_version"] == "3.1" and not preview:
            if enriched.get("status") != "complete" or enriched.get("execution_scope") != "production":
                raise ValueError("Agent requires completed production abstraction for schema 3.1")
        for name in ("build_progress.json", "checkpoint.json"):
            sibling = memory_path.parent / name
            if sibling.exists():
                progress = json.loads(sibling.read_text())
                expected_status = "preview" if preview and name == "checkpoint.json" else "complete"
                if progress.get("status") != expected_status:
                    raise ValueError(f"Stale memory artifact: sibling {name} is not complete")
                if name == "build_progress.json" and progress.get("graph_hash") != meta.get("graph_hash"):
                    raise ValueError("Progress and memory graph identity differ")
                if name == "checkpoint.json" and memory["schema_version"] == "3.1":
                    if progress.get("run_id") != memory["abstraction_metadata"].get("run_id"):
                        raise ValueError("Abstraction checkpoint and memory run identity differ")
                    if preview and (progress.get("metadata", {}).get("preview_status") != "complete"
                                    or progress["metadata"].get("execution_scope") != "preview"):
                        raise ValueError("Preview checkpoint has unfinished packets or a different scope")
        if preview:
            from org_memory.abstraction import fingerprint, validate_enriched
            validate_enriched(memory, preview=True, raise_on_error=True)
            snapshot_path = memory_path.parent / "preview_input.json"
            if snapshot_path.exists():
                snapshot = json.loads(snapshot_path.read_text())
                if (fingerprint(snapshot["memory"]) != snapshot["base_fingerprint"]
                        or snapshot["base_fingerprint"] != enriched["base_fingerprint"]):
                    raise ValueError("Preview input and enriched memory fingerprints differ")
        else:
            validate_memory(memory, raise_on_error=True)
        graph = json.loads(Path(graph_path).read_text())
        index = index_graph(graph, annotate_offline=False)
        if index["graph_hash"] != meta["graph_hash"]:
            raise ValueError("Supplied graph does not match the memory graph")
        if index["nodes"] != memory["nodes"] or index["evidence"] != memory["evidence"]:
            raise ValueError("Supplied graph evidence differs from memory archive")
        return cls(memory, graph, index, {
            "graph_hash": index["graph_hash"], "memory_fingerprint": stable_id("memory", memory),
            "embedding_fingerprint": stable_id("embeddings", graph["id2embeddings"]),
            "schema_version": memory["schema_version"],
            "abstraction_run_id": memory.get("abstraction_metadata", {}).get("run_id"),
            "execution_scope": "preview" if preview else "production",
            "preview_notice": PREVIEW_NOTICE if preview else None,
            "coverage": {
                "base_status": meta["status"],
                "reviewed_candidates": meta["coverage"]["reviewed_candidates"],
                "selected_candidates": meta["coverage"]["selected_candidates"],
                "processed_abstraction_packets": enriched.get("coverage", {}).get("processed_packets", 0),
                "planned_abstraction_packets": enriched.get("coverage", {}).get("planned_packets", 0),
            },
        })
