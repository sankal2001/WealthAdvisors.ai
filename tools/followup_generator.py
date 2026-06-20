"""Tool for generating advisor-ready follow-up questions."""

from __future__ import annotations


QUESTION_BANK: dict[str, str] = {
    "Client name": "Could you confirm the client's full legal name for the onboarding profile?",
    "Age": "Could you confirm the client's age or date of birth for planning assumptions?",
    "Occupation": "What is the client's current occupation and employment status?",
    "Marital status": "Could you confirm the client's marital status for household planning context?",
    "Dependents": "Does the client have any dependents we should account for in the plan?",
    "Annual income": "What is the client's approximate annual income before taxes?",
    "Financial goals": "What are the client's top financial goals for the next 3 to 10 years?",
    "Risk tolerance": "What level of investment volatility would the client be comfortable experiencing over a market cycle?",
    "Investment horizon": "What time horizon should we use for the client's primary investment objective?",
    "Liquidity needs": "How much cash or near-term liquidity does the client expect to need over the next 12 to 24 months?",
    "Existing investments": "What existing accounts, holdings, or investment products should be included in the review?",
}


def generate_followup_questions(missing_fields: list[str]) -> list[str]:
    """Generate concise client-friendly questions for missing fields."""
    return [QUESTION_BANK.get(field, f"Could you provide more detail about {field.lower()}?") for field in missing_fields]
