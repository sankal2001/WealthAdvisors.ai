"""Production-oriented OpenAI Agents SDK orchestration."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from schemas.client_profile import ClientProfile, GapAnalysis, ProcessingResult
from tools.followup_generator import generate_followup_questions
from tools.gap_analyzer import analyze_profile_gaps
from tools.profile_extractor import extract_client_profile

try:
    from agents import Agent, Runner, function_tool
except Exception:  # pragma: no cover - optional runtime dependency
    Agent = None
    Runner = None

    def function_tool(func):
        return func

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.5")
LIVE_AGENTS_AVAILABLE = Agent is not None and Runner is not None


def _require_agents_sdk() -> None:
    if Agent is None or Runner is None:
        raise RuntimeError(
            "The openai-agents package is not available in the current Python environment. "
            "Activate the project venv and run the app with d:/WealthAdvisors_AI/.venv/Scripts/python.exe -m streamlit run app.py"
        )


def _shorten(value: Any, limit: int = 180) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _describe_stream_event(event: Any) -> str | None:
    event_type = getattr(event, "type", event.__class__.__name__)
    if event_type == "agent_updated_stream_event":
        agent = getattr(event, "new_agent", None)
        return f"Agent updated: {getattr(agent, 'name', 'unknown')}"

    if event_type != "run_item_stream_event":
        return None

    name = getattr(event, "name", "run_item")
    item = getattr(event, "item", None)
    item_type = getattr(item, "type", item.__class__.__name__ if item is not None else "unknown")

    if name == "handoff_occured":
        source_agent = getattr(item, "source_agent", None)
        target_agent = getattr(item, "target_agent", None)
        return (
            f"Handoff: {getattr(source_agent, 'name', 'unknown')} -> {getattr(target_agent, 'name', 'unknown')}"
        )

    if name == "tool_called":
        tool_name = getattr(item, "tool_name", None) or getattr(getattr(item, "raw_item", None), "name", None)
        call_id = getattr(item, "call_id", None)
        suffix = f" [{call_id}]" if call_id else ""
        return f"Tool called: {tool_name or item_type}{suffix}"

    if name == "tool_output":
        output = getattr(item, "output", None)
        return f"Tool output: {_shorten(output)}"

    if name == "reasoning_item_created":
        raw_item = getattr(item, "raw_item", None)
        summary = getattr(raw_item, "summary", None) or getattr(raw_item, "text", None)
        return f"Reasoning: {_shorten(summary)}" if summary else "Reasoning item created"

    if name == "message_output_created":
        raw_item = getattr(item, "raw_item", None)
        content = getattr(raw_item, "content", None)
        return f"Message: {_shorten(content)}" if content else "Message output created"

    if name == "handoff_requested":
        return f"Handoff requested by {getattr(getattr(item, 'agent', None), 'name', 'unknown')}"

    return f"{name}: {item_type}"


def _build_summary(profile: ClientProfile) -> dict[str, str]:
    goals = ", ".join(profile.financial_goals) or "No reliable goals extracted."
    investments = ", ".join(profile.existing_investments) or "No existing investments extracted."
    missing = "\n".join(f"- {field}" for field in profile.missing_information) or "No core KYC gaps detected. Advisor approval remains mandatory."
    questions = "\n".join(f"- {question}" for question in profile.followup_questions) or "No follow-up questions generated."
    return {
        "Client Overview": (
            f"Name: {profile.client_name or 'Unknown'}\n"
            f"Age: {profile.age or 'Unknown'}\n"
            f"Occupation: {profile.occupation or 'Unknown'}\n"
            f"Marital Status: {profile.marital_status or 'Unknown'}\n"
            f"Dependents: {profile.dependents or 'Unknown'}\n"
            f"Annual Income: {profile.annual_income or 'Unknown'}"
        ),
        "Goals": f"Financial Goals: {goals}\nInvestment Horizon: {profile.investment_horizon or 'Unknown'}",
        "Risk Profile": (
            f"Risk Tolerance: {profile.risk_tolerance or 'Requires advisor follow-up'}\n"
            f"Liquidity Needs: {profile.liquidity_needs or 'Unknown'}\n"
            f"Existing Investments: {investments}"
        ),
        "Missing Information": missing,
        "Recommended Follow-Up": questions,
    }


@function_tool
def extract_client_profile_tool(raw_text: str) -> dict[str, Any]:
    """Extract structured client profile data from raw onboarding text."""
    return extract_client_profile(raw_text).model_dump()


@function_tool
def analyze_profile_gaps_tool(profile_json: str) -> dict[str, Any]:
    """Analyze a JSON-serialized client profile for missing KYC information."""
    profile = ClientProfile.model_validate_json(profile_json)
    return analyze_profile_gaps(profile).model_dump()


@function_tool
def generate_followup_questions_tool(missing_fields: list[str]) -> list[str]:
    """Generate professional advisor-ready follow-up questions."""
    return generate_followup_questions(missing_fields)


@function_tool
def build_advisor_summary_tool(profile_json: str) -> dict[str, str]:
    """Build advisor-facing summary sections from a JSON-serialized profile."""
    profile = ClientProfile.model_validate_json(profile_json)
    return _build_summary(profile)


if Agent is not None:
    profile_extractor_agent = Agent(
        name="Profile Extractor Agent",
        handoff_description="Extracts a structured ClientProfile from onboarding material.",
        instructions=(
            "Extract only facts supported by the source text. Use extract_client_profile_tool. "
            "Do not infer suitability, approve KYC, or finalize risk tolerance."
        ),
        model=DEFAULT_MODEL,
        tools=[extract_client_profile_tool],
    )

    gap_analyzer_agent = Agent(
        name="KYC Gap Analyzer Agent",
        handoff_description="Finds missing KYC fields and risk review areas.",
        instructions=(
            "Analyze the extracted profile for missing KYC information. Use analyze_profile_gaps_tool with a JSON string. "
            "Keep all compliance decisions with the advisor."
        ),
        model=DEFAULT_MODEL,
        tools=[analyze_profile_gaps_tool],
    )

    followup_agent = Agent(
        name="Follow-Up Question Agent",
        handoff_description="Generates concise advisor-ready client follow-up questions.",
        instructions=(
            "Generate professional, client-friendly questions for missing fields. "
            "Use generate_followup_questions_tool and keep wording concise."
        ),
        model=DEFAULT_MODEL,
        tools=[generate_followup_questions_tool],
    )

    onboarding_orchestrator = Agent(
        name="Client Onboarding Orchestrator",
        instructions=(
            "You are the orchestrator for a wealth advisor KYC onboarding workflow. "
            "Coordinate the specialist agents and tools in this order: extract profile, analyze gaps, "
            "generate follow-up questions, build advisor summary. When tools need the profile, pass it as a JSON string. Return a ProcessingResult. "
            "Never approve KYC, finalize risk tolerance, make suitability/compliance decisions, or submit data. "
            "Advisor approval is mandatory before export."
        ),
        model=DEFAULT_MODEL,
        tools=[
            extract_client_profile_tool,
            analyze_profile_gaps_tool,
            generate_followup_questions_tool,
            build_advisor_summary_tool,
        ],
        handoffs=[profile_extractor_agent, gap_analyzer_agent, followup_agent],
        output_type=ProcessingResult,
    )
else:
    profile_extractor_agent = None
    gap_analyzer_agent = None
    followup_agent = None
    onboarding_orchestrator = None


def _log_result_items(result: Any) -> list[str]:
    entries: list[str] = []
    for item in getattr(result, "new_items", []) or []:
        item_type = getattr(item, "type", item.__class__.__name__)
        agent_name = getattr(getattr(item, "agent", None), "name", None)
        entries.append(f"{item_type}" + (f" via {agent_name}" if agent_name else ""))
    return entries


async def _run_live(raw_text: str) -> ProcessingResult:
    _require_agents_sdk()
    logs = [
        f"OpenAI Agents SDK initialized with model: {DEFAULT_MODEL}",
        "Registered agents: Client Onboarding Orchestrator, Profile Extractor Agent, KYC Gap Analyzer Agent, Follow-Up Question Agent",
        "Starting Runner.run_streamed(...)",
    ]
    stream_result = Runner.run_streamed(onboarding_orchestrator, raw_text)
    async for event in stream_result.stream_events():
        description = _describe_stream_event(event)
        if description:
            logs.append(description)
    if stream_result.run_loop_exception:
        raise stream_result.run_loop_exception
    result = stream_result
    logs.extend(_log_result_items(result))
    final_output = result.final_output
    parsed = final_output if isinstance(final_output, ProcessingResult) else ProcessingResult.model_validate(final_output)
    parsed.mode = "openai-agents-sdk"
    parsed.last_agent = getattr(getattr(result, "last_agent", None), "name", None)
    parsed.trace_hint = "Open the OpenAI Traces dashboard to inspect model calls, tool calls, handoffs, and guardrails."
    parsed.run_log = logs + [
        f"Last agent: {parsed.last_agent or 'unknown'}",
        "Validated ProcessingResult with Pydantic",
    ]
    return parsed


def build_error_result(message: str, raw_text: str = "") -> ProcessingResult:
    """Return a typed UI result when live execution cannot start."""
    profile = extract_client_profile(raw_text)
    gap_analysis = GapAnalysis(reasoning_summary="Live OpenAI Agents SDK run did not execute.")
    return ProcessingResult(
        profile=profile,
        gap_analysis=gap_analysis,
        advisor_summary=_build_summary(profile),
        mode="not-run",
        warnings=[message],
        run_log=[message],
    )


def run_onboarding_agent(raw_text: str) -> ProcessingResult:
    """Run the live OpenAI Agents SDK onboarding workflow."""
    if not raw_text or not raw_text.strip():
        return build_error_result("Please provide onboarding text or upload a supported file.")
    if Agent is None or Runner is None:
        return build_error_result(
            "The openai-agents package is not available in the current Python environment. Activate the project venv and run the app with d:/WealthAdvisors_AI/.venv/Scripts/python.exe -m streamlit run app.py",
            raw_text,
        )
    if not os.getenv("OPENAI_API_KEY"):
        return build_error_result("OPENAI_API_KEY is required for a live OpenAI Agents SDK demo.", raw_text)
    try:
        return asyncio.run(_run_live(raw_text))
    except Exception as exc:
        logger.exception("OpenAI Agents SDK run failed")
        return build_error_result(f"OpenAI Agents SDK run failed: {exc}", raw_text)


if __name__ == "__main__":
    print(
        "This module is imported by app.py. Start the project with: "
        "d:/WealthAdvisors_AI/.venv/Scripts/python.exe -m streamlit run app.py"
    )
