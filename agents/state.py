"""Shared LangGraph state for the story-audit workflow."""

from __future__ import annotations

from typing import Annotated, Literal, Self, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    id: int = Field(ge=1)
    type: Literal["reported", "verifiable_fact"]
    text: str = Field(min_length=1)


class ExtractedClaims(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    claims: list[ExtractedClaim]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        ids = [claim.id for claim in self.claims]
        if len(ids) != len(set(ids)):
            raise ValueError("claim ids must be unique")
        return self


class SourceScore(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    source: str = Field(min_length=1)
    reliability: float = Field(ge=0.0, le=1.0)
    corroboration: float = Field(ge=0.0, le=1.0)


class AnalysisMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    claims_total: int = Field(ge=0)
    claims_supported: int = Field(ge=0)
    claims_contradicted: int = Field(ge=0)
    claims_unverifiable: int = Field(ge=0)
    rhetoric_risk: float = Field(ge=0.0, le=1.0)


class AnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    overall_confidence: Literal["alta", "media", "baja", "en_revision"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_scores: list[SourceScore]
    metrics: AnalysisMetrics
    rationale: str = Field(min_length=1)


class StoryAuditState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    story: str
    claims: list[ExtractedClaim]
    fact_check: str
    rhetorical_audit: str
    judgment: str
    analysis: AnalysisOutput | None
    article: str
