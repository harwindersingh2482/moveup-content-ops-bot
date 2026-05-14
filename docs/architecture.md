# Architecture

`moveup-content-ops-bot` is organized as a small, testable content operations platform.

## Runtime Flow

1. `services.youtube.YouTubeMetricsClient` resolves selected public YouTube channel handles or channel IDs, fetches recent public uploads for each channel, and normalizes snippet, statistics, and duration data.
2. `services.analytics` calculates engagement rate, views per day, relative score, rating, top/bottom videos, and channel recommendations.
3. `services.reporting` sends the structured context to an LLM when `OPENAI_API_KEY` is configured. Without an LLM key, it builds the same report shape deterministically.
4. `agents.content_ops_agent` answers natural-language questions from the latest selected-channel report and metrics.
5. `backend.main` exposes the workflow over FastAPI.
6. `frontend.dashboard` presents the management interface in Streamlit with channel input, publish-time filters, source data, reports, and chat.

## Components

- `backend/`: FastAPI health, report, video, and chat endpoints.
- `frontend/`: Streamlit management dashboard for operators and analysts.
- `agents/`: Conversational AI workflow grounded in the current report.
- `services/`: YouTube integration, scoring logic, report generation, app settings, and sample data.
- `prompts/`: Prompt documentation and future prompt versions.
- `database/`: Placeholder for persistence, migrations, and scheduled report state.
- `reports/`: Placeholder for generated report exports.
- `tests/`: Automated tests for API, service, and workflow behavior.

## Data Limits

The YouTube Data API exposes public metrics such as views, likes, comments, publish date, and duration. It does not expose CTR or retention for public channels without owner analytics access. The scoring model therefore uses public-data proxies and calls this limitation out in the report.

## Development Principles

- Keep API boundaries explicit and testable.
- Keep prompts concrete, versioned, and reviewable.
- Keep secrets in environment variables, never in source control.
- Provide a no-key demo path without hiding the live API implementation.
