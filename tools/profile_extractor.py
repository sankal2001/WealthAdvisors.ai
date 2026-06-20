"""Tool for converting unstructured onboarding text into a ClientProfile."""

from __future__ import annotations

import logging
import re

from schemas.client_profile import ClientProfile

logger = logging.getLogger(__name__)


FIELD_PATTERNS: dict[str, list[str]] = {
    "client_name": [r"(?:client name|name)\s*[:\-]\s*([A-Z][A-Za-z .'-]+)", r"\b(?:meet|met with|for)\s+([A-Z][a-z]+ [A-Z][a-z]+)\b"],
    "age": [r"\bage\s*[:\-]\s*(\d{1,3})\b", r"\b(\d{2})\s*(?:years old|year-old)\b"],
    "occupation": [r"(?:occupation|profession|works as|job)\s*[:\-]\s*([^\n.;]+)"],
    "marital_status": [r"(?:marital status)\s*[:\-]\s*([^\n.;]+)", r"\b(single|married|divorced|widowed)\b"],
    "dependents": [r"(?:dependents|children)\s*[:\-]\s*([^\n.;]+)", r"\b(\d+\s+(?:children|dependents))\b"],
    "annual_income": [r"(?:annual income|income|earns)\s*[:\-]?\s*\$?((?=[\d,]*\d)[\d,]+(?:\.\d+)?)\s*(?:per year|annually|/year)?"],
    "risk_tolerance": [r"(?:risk tolerance|risk profile|risk appetite)\s*[:\-]\s*([^\n.;]+)", r"\b(conservative|moderate|balanced|aggressive)\s+(?:risk|investor|portfolio)\b"],
    "investment_horizon": [r"(?:investment horizon|time horizon|horizon)\s*[:\-]\s*([^\n.;]+)", r"\b(\d+\s*(?:year|years)\s*(?:horizon|time horizon)?)\b"],
    "liquidity_needs": [r"(?:liquidity needs|cash needs|liquidity requirement)\s*[:\-]\s*([^\n.;]+)"],
}

GOAL_TERMS = {
    "retirement": "Retirement planning",
    "college": "Education funding",
    "education": "Education funding",
    "home": "Home purchase",
    "estate": "Estate planning",
    "growth": "Long-term growth",
    "income": "Income generation",
    "tax": "Tax efficiency",
    "legacy": "Legacy planning",
}

INVESTMENT_TERMS = {
    "401(k)": "401(k)",
    "ira": "IRA",
    "brokerage": "Taxable brokerage",
    "mutual fund": "Mutual funds",
    "etf": "ETFs",
    "stock": "Individual stocks",
    "bond": "Bonds",
    "real estate": "Real estate",
    "private equity": "Private equity",
}


def _first_match(raw_text: str, field_name: str) -> tuple[str | None, float, str | None]:
    for pattern in FIELD_PATTERNS[field_name]:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(), 0.84, _source_for_match(raw_text, match.start())
    return None, 0.0, None


def _source_for_match(raw_text: str, index: int) -> str:
    before = raw_text[:index]
    paragraph = before.count("\n\n") + 1
    sentence = before.count(".") + before.count("?") + before.count("!") + 1
    return f"Paragraph {paragraph}, sentence {sentence}"


def _extract_terms(raw_text: str, terms: dict[str, str]) -> list[str]:
    found: list[str] = []
    lowered = raw_text.lower()
    for token, label in terms.items():
        if token.lower() in lowered and label not in found:
            found.append(label)
    return found


def extract_client_profile(raw_text: str) -> ClientProfile:
    """Convert raw onboarding text into structured profile data.

    This deterministic extractor is intentionally conservative. In live mode, the
    orchestrator may call this tool through the Agents SDK, but it also powers
    demos and tests when no API key is configured.
    """
    if not raw_text or not raw_text.strip():
        logger.info("Profile extraction received empty input")
        return ClientProfile(notes="No onboarding text was provided.")

    data: dict[str, object] = {}
    confidence: dict[str, float] = {}
    sources: dict[str, str] = {}

    for field_name in FIELD_PATTERNS:
        value, score, source = _first_match(raw_text, field_name)
        if value is None:
            continue
        if field_name == "age":
            data[field_name] = int(value)
        elif field_name == "annual_income":
            data[field_name] = float(value.replace(",", ""))
        else:
            data[field_name] = value.rstrip(" .")
        confidence[field_name] = score
        if source:
            sources[field_name] = source

    goals = _extract_terms(raw_text, GOAL_TERMS)
    investments = _extract_terms(raw_text, INVESTMENT_TERMS)
    if goals:
        data["financial_goals"] = goals
        confidence["financial_goals"] = 0.76
        sources["financial_goals"] = "Detected from goal-related keywords"
    if investments:
        data["existing_investments"] = investments
        confidence["existing_investments"] = 0.72
        sources["existing_investments"] = "Detected from investment-related keywords"

    data["notes"] = raw_text[:450].strip()
    profile = ClientProfile(**data, confidence_scores=confidence, source_attribution=sources)
    logger.info("Extracted profile for client=%s", profile.client_name or "unknown")
    return profile
