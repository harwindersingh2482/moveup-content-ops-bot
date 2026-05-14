# MoveUp Content Ops Bot

AI-powered management workspace for YouTube content operations and channel benchmarking.

The app collects public video metrics from any YouTube channel handles or channel URLs pasted into the sidebar, filters the dataset by a selected publish-time window, scores performance, generates a structured report, and lets operators ask natural-language questions through a conversational content ops agent.

## What It Does

- Starts with `@Netflu` and `@ThePlayoffsTV` by default for the MoveUp Media test case.
- Lets operators paste any public YouTube channel handles or channel links to compare up to 6 channels.
- Supports publish-time windows: latest uploads, last 7 days, last 30 days, or a custom date/time range.
- Uses the latest 10 public uploads per selected channel by default, and expands the fetch window when date filters are active so reports can cover broader ranges.
- Filters dashboards, source data sheets, CSV exports, and reports by the selected channel set and publish-time range.
- Analyzes views, likes, comments, engagement rate, recency velocity, and relative channel benchmarks.
- Produces a Markdown performance report with channel summaries, per-video ratings, top/bottom videos, and actionable recommendations.
- Exposes the workflow through a FastAPI backend and Streamlit management platform.
- Includes a sample-data demo mode so reviewers can run the project without API keys.

Public YouTube Data API responses do not expose CTR or audience retention, so the report does not invent them. Engagement rate and views-per-day are used as public-data proxies.

## Quick Start

From WSL Ubuntu:

```bash
cd ~/AI-Projects/moveup-content-ops-bot
source .venv/bin/activate
```

Create a local environment file:

```bash
cp .env.example .env
```

Run the backend:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Run the management platform in a second terminal:

```bash
streamlit run frontend/dashboard.py \
  --server.headless true \
  --browser.gatherUsageStats false
```

Open Streamlit at `http://localhost:8501`.

In the sidebar, paste one YouTube channel per line. The app works with public YouTube channels, not only the default MoveUp channels. Supported formats include:

```text
@Netflu
https://www.youtube.com/@ThePlayoffsTV
https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx
```

Use the Report Window control to switch between latest uploads, last 7 days, last 30 days, or a custom date/time range.

## API Keys

The app runs out of the box with `USE_SAMPLE_DATA=true`.

For live YouTube data, set:

```bash
YOUTUBE_API_KEY=your-youtube-data-api-v3-key
USE_SAMPLE_DATA=false
```

For LLM-generated wording, set:

```bash
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
```

The app also supports OpenAI-compatible Groq inference:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
```

If no LLM key is present, the app still generates a deterministic structured report and the conversational agent answers with local analysis tools.

## Deployment

The live demo can be deployed on Streamlit Community Cloud.

Use this main file path:

```text
frontend/dashboard.py
```

Recommended Streamlit secrets for a live demo:

```toml
YOUTUBE_API_KEY = "your-youtube-data-api-v3-key"
USE_SAMPLE_DATA = "false"

LLM_PROVIDER = "groq"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "llama-3.1-8b-instant"

APP_ENV = "production"
```

For a no-key reviewer demo, set `USE_SAMPLE_DATA = "true"`.

## API Endpoints

- `GET /health` - service health.
- `GET /api/report?refresh=true` - fetch default channel metrics and generate the report.
- `GET /api/report?start_at=2026-04-01T00:00:00Z&end_at=2026-05-01T23:59:00Z` - generate a report for a publish-time window.
- `GET /api/videos` - return normalized video metrics, with optional `start_at` and `end_at` query parameters.
- `POST /api/chat` - ask the conversational agent a question.

Example:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What should we focus on this week?"}'
```

## Prompt Strategy

The report prompt explicitly sets:

- Role: senior media analyst for MoveUp Media.
- Context: weekly YouTube content operations for a digital agency.
- Output: Markdown with executive summary, per-channel analysis, per-video ratings, top/bottom videos, and recommendations.
- Metrics: views, engagement rate, likes, comments, recency velocity, and relative channel benchmarks.
- Constraint: do not fabricate CTR or retention because they are not available from public YouTube API data.

The conversational agent receives the latest report plus structured video metrics and answers only from that context.

## Tests

```bash
pytest
ruff check .
```

## Architecture

```text
backend/   FastAPI application and API routes
frontend/  Streamlit management dashboard
agents/    Conversational content operations agent
services/  YouTube ingestion, analytics, reporting, workflow orchestration
prompts/   Prompt notes and future prompt variants
database/  Placeholder for persistence and scheduling state
reports/   Placeholder for generated exports
tests/     Automated tests for API and analysis behavior
docs/      Architecture and engineering documentation
scripts/   Developer and operations scripts
```

## Next Extensions

1. Add weekly scheduling for automatic report generation.
2. Add saved channel benchmark presets for recurring competitor sets.
3. Store normalized metrics in SQLite with SQLAlchemy models for long-term history.
4. Add authentication for team usage.

Generated JSON reports are local exports and are ignored by Git by default.
