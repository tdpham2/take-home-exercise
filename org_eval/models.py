"""Small, strict contracts for reference criteria and auditable semantic judgments."""
from typing import Literal

from pydantic import Field
from org_agent.models import StrictModel, Citation


class Facet(StrictModel):
    id: str
    description: str = Field(min_length=1)
    kind: Literal["fact", "uncertainty"]
    evidence: list[Citation] = Field(min_length=1)
    evidence_rule: Literal["any", "all"]
    rationale: str = Field(min_length=1)


class Caution(StrictModel):
    statement: str = Field(min_length=1)
    evidence: list[Citation] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class QuestionDraft(StrictModel):
    text: str = Field(min_length=1, max_length=8000)
    paraphrase: str = Field(min_length=1, max_length=8000)
    facets: list[Facet] = Field(min_length=4, max_length=8)
    cautions: list[Caution] = Field(min_length=1)
    reference_limitations: list[str] = Field(min_length=1)


class ClaimVerdict(StrictModel):
    claim_id: str
    atomic_statement: str = Field(min_length=1)
    verdict: Literal["supported", "partial", "unsupported", "contradicted"]
    evidence_ids: list[str]
    rationale: str = Field(min_length=1)


class FacetVerdict(StrictModel):
    facet_id: str
    score: Literal[0, 0.5, 1]
    claim_ids: list[str]
    rationale: str = Field(min_length=1)


class Specificity(StrictModel):
    score: int = Field(ge=0, le=4)
    rationale: str = Field(min_length=1)


class Contradiction(StrictModel):
    claim_ids: list[str] = Field(min_length=2)
    rationale: str = Field(min_length=1)


class Judgment(StrictModel):
    claims: list[ClaimVerdict]
    facets: list[FacetVerdict]
    specificity: Specificity
    internal_contradictions: list[Contradiction]
    reference_omissions: list[str]
    review_flags: list[str]


class PropositionPair(StrictModel):
    left_claim_id: str
    right_claim_id: str
    relation: Literal["agreement", "contradiction"]
    rationale: str = Field(min_length=1)


class ConsistencyJudgment(StrictModel):
    comparable_pairs: list[PropositionPair]
    review_flags: list[str]
