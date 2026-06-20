"""Validated data models for the Client Onboarding & KYC Agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ClientProfile(BaseModel):
    """Structured first-pass client profile extracted from onboarding material."""

    client_name: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    occupation: str | None = None
    marital_status: str | None = None
    dependents: str | None = None
    annual_income: float | None = Field(default=None, ge=0)
    financial_goals: list[str] = Field(default_factory=list)
    risk_tolerance: str | None = None
    investment_horizon: str | None = None
    liquidity_needs: str | None = None
    existing_investments: list[str] = Field(default_factory=list)
    notes: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    source_attribution: dict[str, str] = Field(default_factory=dict)

    @field_validator("financial_goals", "existing_investments", "missing_information", "followup_questions", mode="before")
    @classmethod
    def coerce_string_list(cls, value: Any) -> list[str]:
        """Accept comma/newline separated model output while preserving typed lists."""
        if value is None:
            return []
        if isinstance(value, str):
            parts = [part.strip(" -\t") for part in value.replace("\n", ",").split(",")]
            return [part for part in parts if part]
        return value

    @field_validator("client_name", "occupation", "marital_status", "dependents", "risk_tolerance", "investment_horizon", "liquidity_needs", "notes", mode="before")
    @classmethod
    def normalize_blank_strings(cls, value: Any) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("confidence_scores")
    @classmethod
    def confidence_between_zero_and_one(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: max(0.0, min(1.0, float(score))) for key, score in value.items()}

    def value_for_field(self, field_name: str) -> Any:
        """Return a display-friendly value for a profile field."""
        value = getattr(self, field_name)
        if isinstance(value, list):
            return ", ".join(value)
        return value


class GapAnalysis(BaseModel):
    """Missing KYC fields and rationale for advisor review."""

    missing_fields: list[str] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)
    reasoning_summary: str = "No gap analysis has been completed."


class ProcessingResult(BaseModel):
    """Full orchestrator output for UI rendering and export."""

    profile: ClientProfile
    gap_analysis: GapAnalysis
    advisor_summary: dict[str, str] = Field(default_factory=dict)
    mode: str = "openai-agents-sdk"
    warnings: list[str] = Field(default_factory=list)
    run_log: list[str] = Field(default_factory=list)
    last_agent: str | None = None
    trace_hint: str | None = None
