"""Public configuration and answer contracts for the organizational agent."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


VERSION = "task2-agent-v1"
Confidence = Literal["high", "medium", "low"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentConfig(StrictModel):
    provider: Literal["codex", "compatible"] = "codex"
    model: str = "gpt-5.6-luna"
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
    max_model_calls: int = Field(default=12, ge=3, le=100)
    max_tool_calls: int = Field(default=10, ge=1, le=100)
    max_request_chars: int = Field(default=200_000, ge=12000)
    no_gain_limit: int = Field(default=3, ge=1)
    cache_dir: str = "artifacts/cache-task2"
    timeout: float = Field(default=300, gt=0)


class Citation(StrictModel):
    evidence_id: str
    quote: str = Field(min_length=1)
    start: int = Field(ge=0, description="Exact zero-based character offset in the original evidence text.")


class DraftClaim(StrictModel):
    statement: str = Field(min_length=1, max_length=3000)
    kind: Literal["source_report", "prescription", "synthesis", "hypothesis"]
    citations: list[Citation] = Field(min_length=1, max_length=20)
    memory_ids: list[str] = Field(default_factory=list, max_length=20)
    confidence: Confidence
    confidence_reason: str = Field(min_length=1, max_length=1000)
    verification_note: str = Field(default="", max_length=1000)


class DraftAnswer(StrictModel):
    """Finish with atomic cited claims; put missing evidence in unanswered, not invented claims."""
    claims: list[DraftClaim] = Field(default_factory=list, max_length=12)
    unanswered: list[str] = Field(default_factory=list, max_length=12)
    limitations: list[str] = Field(default_factory=list, max_length=12)


class Claim(DraftClaim):
    id: str
    record_ids: list[str]
    source_mode: Literal["memory", "graph", "memory_confirmed_by_graph", "text"]


class AnswerResult(StrictModel):
    question: str
    status: Literal["complete", "partial", "failed"]
    provisional: bool = False
    claims: list[Claim] = Field(default_factory=list)
    unanswered: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    stop_reason: str | None = None
    trace: list[dict] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
    manifest: dict = Field(default_factory=dict)

    def markdown(self):
        lines = [f"# {self.question}", "", f"Status: {self.status}", ""]
        if self.provisional:
            lines += ["**Provisional preview: the organizational memory is not fully reviewed.**", ""]
        for claim in self.claims:
            records = ", ".join(claim.record_ids) or "No source record ID"
            lines += [f"- **{claim.id}.** {claim.statement}",
                      f"  Sources: {records}. Route: `{claim.source_mode}`.",
                      f"  Confidence: **{claim.confidence}** — {claim.confidence_reason}"]
            for citation in claim.citations:
                lines.append(f"  - `{citation.evidence_id}` [{citation.start}:{citation.start + len(citation.quote)}]: {citation.quote}")
        if not self.claims:
            lines.append("No validated claims are available.")
        for title, entries in [("Unanswered", self.unanswered), ("Limitations", self.limitations),
                               ("Validation errors", self.validation_errors)]:
            if entries:
                lines += ["", f"## {title}", "", *[f"- {entry}" for entry in entries]]
        return "\n".join(lines) + "\n"
