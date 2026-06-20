"""Tool for identifying missing KYC information."""

from __future__ import annotations

from schemas.client_profile import ClientProfile, GapAnalysis


REQUIRED_FIELDS: dict[str, str] = {
    "client_name": "Client name",
    "age": "Age",
    "occupation": "Occupation",
    "marital_status": "Marital status",
    "dependents": "Dependents",
    "annual_income": "Annual income",
    "financial_goals": "Financial goals",
    "risk_tolerance": "Risk tolerance",
    "investment_horizon": "Investment horizon",
    "liquidity_needs": "Liquidity needs",
    "existing_investments": "Existing investments",
}


def analyze_profile_gaps(profile: ClientProfile) -> GapAnalysis:
    """Identify incomplete fields and advisor attention areas."""
    missing: list[str] = []
    risk_areas: list[str] = []

    for field_name, label in REQUIRED_FIELDS.items():
        value = getattr(profile, field_name)
        if value is None or value == "" or value == []:
            missing.append(label)

    if "Risk tolerance" in missing:
        risk_areas.append("Risk tolerance cannot be finalized without direct advisor/client confirmation.")
    if "Investment horizon" in missing:
        risk_areas.append("Suitability review needs a clear investment horizon.")
    if "Liquidity needs" in missing:
        risk_areas.append("Liquidity needs are required before recommending allocation constraints.")
    if profile.risk_tolerance and profile.risk_tolerance.lower() in {"aggressive", "high"}:
        risk_areas.append("High-risk profile should be verified against goals, horizon, and liquidity needs.")

    if missing:
        reasoning = f"{len(missing)} KYC fields need advisor follow-up before the profile can be treated as complete."
    else:
        reasoning = "Core onboarding fields appear complete, but advisor approval is still required."

    return GapAnalysis(missing_fields=missing, risk_areas=risk_areas, reasoning_summary=reasoning)
