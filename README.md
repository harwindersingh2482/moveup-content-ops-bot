# MoveUp Content Ops Bot

AI-powered management workspace for MoveUp Media's YouTube content operations.

The app collects the last 10 videos from the official MoveUp channels, scores recent performance, generates a structured report, and lets operators ask natural-language questions through a conversational content ops agent.

## What It Does

- Collects public YouTube metrics for `@Netflu` and `@ThePlayoffsTV`.
- Filters dashboards, source data sheets, CSV exports, and reports by selected publish date/time.
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

## API Endpoints

- `GET /health` - service health.
- `GET /api/report?refresh=true` - fetch metrics and generate the report.
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
2. Add a competitive benchmark for 2-3 comparable sports/media channels.
3. Store normalized metrics in SQLite with SQLAlchemy models for long-term history.
4. Add deployed demo hosting and authentication for team usage.

Generated JSON reports are local exports and are ignored by Git by default.
