# Client Onboarding & KYC Live Agents

Production-ready Streamlit demo of a live OpenAI Agents SDK workflow for advisor-facing client onboarding and KYC review.

The app uploads onboarding files, runs a real Agents SDK orchestrator, shows agent/tool execution logs in the frontend, lets the advisor review/edit the output, and exports an advisor-approved profile.

## Architecture

- `app.py`: Streamlit interface, multi-file uploads, advisor edits, JSON/report exports.
- `kyc_agents/onboarding_agent.py`: live OpenAI Agents SDK orchestration with one orchestrator agent and three specialist agents.
- `tools/profile_extractor.py`: `extract_client_profile` tool.
- `tools/gap_analyzer.py`: `analyze_profile_gaps` tool.
- `tools/followup_generator.py`: `generate_followup_questions` tool.
- `schemas/client_profile.py`: Pydantic validation for `ClientProfile`, `GapAnalysis`, and `ProcessingResult`.
- `sample_uploads/`: generated PDF, Word, Excel, CSV, and audio files for upload demos.
- `scripts/generate_sample_uploads.py`: regenerates the sample upload dataset.

## Live Agent Workflow

1. Advisor uploads PDF, Word, Excel, CSV, audio, TXT, or pasted onboarding content.
2. `Client Onboarding Orchestrator` runs through `Runner.run(...)`.
3. Orchestrator coordinates specialist agents:
   - `Profile Extractor Agent`
   - `KYC Gap Analyzer Agent`
   - `Follow-Up Question Agent`
4. Agents call function tools and return a validated `ProcessingResult`.
5. Streamlit displays run logs, missing fields, follow-up questions, evidence, editable fields, and gated exports.

## Tool Descriptions

- `extract_client_profile(raw_text) -> ClientProfile`: converts unstructured text into structured client data.
- `analyze_profile_gaps(profile) -> GapAnalysis`: identifies missing KYC fields and advisor attention areas.
- `generate_followup_questions(missing_fields) -> list[str]`: creates concise client-friendly questions.

## What Was Mocked

The agent run itself is not mocked. `OPENAI_API_KEY` is required for a live demo. If no key is configured, the UI shows a typed error result instead of pretending an agent ran.

The extraction/gap/question functions are local function tools exposed to the live SDK agent. Audio transcription also uses OpenAI when `OPENAI_API_KEY` is configured.

## Supported Uploads

- Documents: `.txt`, `.pdf`, `.docx`
- Spreadsheets: `.xlsx`, `.xls`, `.csv`
- Audio: `.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`

Audio files are accepted in the upload queue. Transcription requires `OPENAI_API_KEY`; otherwise the UI prompts the advisor to paste the transcript.

## Tradeoffs

- Live SDK orchestration is required for the demo; local fallback is intentionally not used as a fake agent run.
- Confidence and source attribution are lightweight; production should use deeper evidence spans and audit trails.
- Advisor approval remains mandatory because suitability and KYC decisions require human oversight.
- No CRM submission is included because automatic submission would conflict with the human-in-the-loop requirement.
- No persistent storage is included to reduce privacy risk for sensitive financial data.

## Future Improvements

- OCR for scanned PDFs.
- Stronger extraction with evidence spans per field.
- Role-based access, audit logging, and encrypted storage.
- CRM integration after explicit advisor approval.
- Evaluation set with precision/recall tracking for extracted fields.
- Rich PDF/DOCX report export.

## How To Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Set `OPENAI_API_KEY` in `.env` before running a live demo. Optional: set `OPENAI_AGENT_MODEL` to another Agents SDK-compatible model if needed.

## Deploy To GitHub

This project is ready to live in a GitHub repository and deploy from there.

1. Create a new GitHub repo and push this workspace.
2. Keep `app.py` as the Streamlit entry point.
3. Connect the repo to Streamlit Community Cloud or your preferred GitHub-based deploy target.
4. Add `OPENAI_API_KEY` as a secret/environment variable in the deployment settings.
5. Optionally set `OPENAI_AGENT_MODEL` if you want to override the default model.
6. The included GitHub Actions workflow validates installs and imports on every push and pull request.

For Streamlit Community Cloud, the app path is `app.py` and the dependency list comes from `requirements.txt`.

To recreate the sample upload dataset:

```bash
python scripts/generate_sample_uploads.py
```

## Demo Video

Suggested 5-minute flow:

1. Problem and product rationale.
2. Architecture: orchestrator, specialist agents, and function tools.
3. Upload a sample file from `sample_uploads`.
4. Run live agents and show the `Agent Logs` tab.
5. Advisor edits and approval before export.
