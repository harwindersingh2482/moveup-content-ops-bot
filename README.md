# MoveUp Content Ops Bot

AI-powered YouTube content operations platform for MoveUp Media. Fetches public video metrics, scores performance, generates a structured analyst report, and lets operators ask natural-language questions through a conversational content ops agent.

**Live demo:** https://moveup-content-ops-bot.streamlit.app/

---

## What It Does

- Fetches the latest public uploads from any YouTube channel handle or URL
- Filters by publish-time window: latest uploads, last 7 days, last 30 days, or a custom date range
- Scores each video on views, engagement rate, likes, comments, recency velocity, and relative channel benchmarks
- Generates a structured Markdown performance report: executive summary, per-video ratings, top/bottom videos, and actionable recommendations per channel
- Exposes a conversational agent so operators can ask questions in natural language and get analyst-quality answers when an LLM key is configured
- Supports up to 6 channels simultaneously for competitive benchmarking
- Runs a sample-data demo with no YouTube API key required

**Default channels:** `@Netflu` and `@ThePlayoffsTV` — the two official MoveUp Media YouTube channels specified in the brief.

---

## Extensions Completed

### Competitive Benchmark (Bonus)

The platform supports adding any public YouTube channel for competitive comparison. For the MoveUp Media test case, `@SidhuMooseWalaOfficial` and `@KaranAujlaOfficial` were used as benchmark channels.

**Justification:** Both are dominant Punjabi music channels on YouTube with large, active audiences and consistent upload cadences. They represent a meaningful benchmark for content velocity, engagement rate, and production format — the same dimensions MoveUp Media tracks for its own channels. Their public metrics are available via the YouTube Data API v3 with no special access required.

---

## Quick Start (under 10 minutes)

### Prerequisites

- Python 3.14
- A YouTube Data API v3 key (free — setup takes under 5 minutes at [Google Cloud Console](https://console.cloud.google.com/))
- A Groq API key (free at [console.groq.com](https://console.groq.com/)) — or run in demo mode without any keys

### 1. Clone the repository

```bash
git clone https://github.com/harwindersingh2482/moveup-content-ops-bot.git
cd moveup-content-ops-bot
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS / WSL
# .venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your keys:

```env
YOUTUBE_API_KEY=your-youtube-data-api-v3-key
USE_SAMPLE_DATA=false

LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

To run without a YouTube API key, set `USE_SAMPLE_DATA=true`. Report generation has a
deterministic fallback without an LLM key; conversational agent answers require either
`GROQ_API_KEY` or `OPENAI_API_KEY`.

### 5. Start the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start the management platform (new terminal)

```bash
source .venv/bin/activate
streamlit run frontend/dashboard.py \
  --server.headless true \
  --browser.gatherUsageStats false
```

### 7. Open the app

Go to [http://localhost:8501](http://localhost:8501).

Paste one channel handle or URL per line in the sidebar. Supported formats:

```
@Netflu
https://www.youtube.com/@ThePlayoffsTV
https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx
```

---

## API Keys

| Variable | Purpose | Required |
|---|---|---|
| `YOUTUBE_API_KEY` | Live YouTube data | No (sample data available) |
| `GROQ_API_KEY` | LLM-generated report and agent answers | No (report fallback available) |
| `OPENAI_API_KEY` | Alternative LLM provider | No |

The app can load sample data and generate deterministic reports without any keys using
`USE_SAMPLE_DATA=true`. The Ask Agent tab needs an LLM key for live answers.

---

## LLM and Prompt Strategy

The report prompt is designed for a specific role and output — not a generic "analyze this data" instruction.

**Role:** Senior media analyst for a digital agency

**Context:** Weekly YouTube content operations review

**Output format:** Structured Markdown with executive summary, per-channel analysis, per-video ratings (strong / average / underperforming), top and bottom videos with reasoning, and one concrete actionable recommendation per channel

**Priority metrics:** Views, engagement rate, likes, comments, recency velocity, relative channel benchmarks

**Constraint:** The prompt explicitly instructs the LLM not to fabricate CTR or audience retention — these are not available from the public YouTube Data API v3. Engagement rate and views-per-day are used as public-data proxies.

The conversational agent receives the system prompt, up to 20 structured video metrics sorted by views, and the user's question. It does not receive the generated report markdown. It is prompted as a senior content operations analyst and instructed to give distinct, actionable answers — not metric summaries — for every question type.

---

## Conversational Agent

Users type natural-language questions into the Ask Agent tab. The system routes every question through the LLM with the system prompt and structured video metrics as context. No local string overrides.

Example questions the agent handles:

- "Compare the selected channels and tell me which is stronger."
- "Which video dropped the most?"
- "Give me one recommendation per channel."
- "What type of content works best for us?"
- "What would you tell a new client about these two channels in one sentence?"

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Service health check |
| `GET /api/report?refresh=true` | Fetch default channel metrics and generate report |
| `GET /api/report?start_at=2026-04-01T00:00:00Z&end_at=2026-05-01T23:59:00Z` | Report for a custom publish-time window |
| `GET /api/videos` | Normalized video metrics with optional date filters |
| `POST /api/chat` | Ask the conversational agent a question |

Example chat request:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What should we focus on this week?"}'
```

---

## Deployment (Streamlit Cloud)

Main file path:

```
frontend/dashboard.py
```

Recommended secrets for a live demo:

```toml
YOUTUBE_API_KEY = "your-youtube-data-api-v3-key"
USE_SAMPLE_DATA = "false"

LLM_PROVIDER = "groq"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "llama-3.3-70b-versatile"

APP_ENV = "production"
```

For a no-YouTube-key reviewer demo, set `USE_SAMPLE_DATA = "true"`. Add `GROQ_API_KEY`
or `OPENAI_API_KEY` if reviewers should test the Ask Agent tab.

---

## Tests

```bash
pytest
ruff check .
```

---

## Architecture

```
backend/    FastAPI application and API routes
frontend/   Streamlit management dashboard
agents/     Conversational content operations agent
services/   YouTube ingestion, analytics, reporting, workflow orchestration
prompts/    Prompt notes and future prompt variants
database/   Placeholder for persistence and scheduling state
reports/    Placeholder for generated exports
tests/      Automated tests for API and analysis behavior
docs/       Architecture and engineering documentation
scripts/    Developer and operations scripts
```

---

## Tech Stack

- **Backend:** FastAPI, Python
- **Frontend:** Streamlit
- **Data:** YouTube Data API v3
- **LLM:** Groq (`llama-3.3-70b-versatile` by default) or OpenAI-compatible chat completions
- **Deployment:** Streamlit Community Cloud

---

## Next Extensions

- Weekly scheduling for automatic report generation
- Saved channel benchmark presets for recurring competitor sets
- SQLite with SQLAlchemy models for long-term metric history
- Authentication for team usage
