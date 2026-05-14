# Prompts

The production prompt currently lives in `services/reporting.py` so it can be tested alongside the report workflow.

Prompt requirements used for the MoveUp technical test:

- Role: senior media analyst for a digital agency.
- Context: weekly YouTube content operations.
- Output: structured Markdown report.
- Required sections: executive summary, per-channel analysis, per-video ratings, top/bottom videos, and channel-level recommendations.
- Priority metrics: views, likes, comments, engagement rate, views per day, and relative channel score.
- Guardrail: do not fabricate CTR or retention because public YouTube Data API data does not include those metrics.

Future versions can be copied here as separate prompt files once the report format stabilizes.
