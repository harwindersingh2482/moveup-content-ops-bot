"""Conversational agent for answering questions about the current report."""

from __future__ import annotations

from openai import OpenAI

from services.models import ChatResponse, PerformanceReport, VideoMetric
from services.settings import get_llm_api_key, get_llm_base_url, get_llm_model

AGENT_SYSTEM_PROMPT = """You are a senior content operations analyst for a digital media agency.

You have access to YouTube performance data for the channels in the current report.
Your job is to answer operator questions with sharp, actionable intelligence, not raw data dumps.

CONTEXT YOU RECEIVE:
- Structured video metrics: title, views, likes, comments, engagement rate, views_per_day,
  publish date, channel name
- The selected channels and report window

ANSWER RULES:
1. Every answer must end with one actionable insight or recommendation.
2. Never repeat the same answer to two different questions. Read the question carefully.
3. If the question asks for a recommendation, give a specific recommendation, not a metric summary.
4. If the data cannot fully answer the question, such as historical drop tracking, CTR, or
   retention, say so in one sentence, then answer with what you do have.
5. Keep answers under 120 words unless the question requires a detailed breakdown.
6. Use plain English. No bullet soup. Write like a smart analyst talking to a busy manager.

QUESTION HANDLING:

If asked to COMPARE channels:
- Lead with the strategic insight, not the numbers.
- Mention total views and engagement rate together because they tell different stories.
- End with which channel has more growth leverage and why.

If asked which video DROPPED or UNDERPERFORMED:
- Identify the video with the lowest score or furthest below channel average.
- Acknowledge if you cannot track historical decline over time.
- Explain briefly why it likely underperformed based on available signals.

If asked for RECOMMENDATIONS per channel:
- Give one distinct, specific recommendation per channel.
- Each recommendation must be different and tied to that channel's data pattern.
- Format: "Channel name -> recommendation."
- Do not repeat the channel comparison. The user already knows the numbers.

If asked what to FOCUS ON this week:
- Pick the single highest-leverage action across all channels.
- Be specific: content type, format, or pattern, not "post more content."

If asked about BEST PERFORMING content:
- Identify top videos by views and engagement rate separately.
- Note if the top video by views has low engagement because that is a signal worth flagging.

TONE:
- Professional, direct, and concise.
- Think: senior analyst briefing, not chatbot response.
- No filler phrases like "Great question" or "Based on the data provided."
"""


def answer_question(question: str, report: PerformanceReport) -> ChatResponse:
    """Answer a natural-language question against a generated report."""
    tools_used = ["current_performance_report"]
    api_key = get_llm_api_key()
    if not api_key:
        return ChatResponse(
            answer="LLM chat is not configured. Add an OpenAI or Groq API key to enable answers.",
            tools_used=tools_used,
            source=report.source,
        )

    client = OpenAI(api_key=api_key, base_url=get_llm_base_url())
    prompt = build_agent_prompt(question, report)
    try:
        response = client.chat.completions.create(
            model=get_llm_model(),
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        return ChatResponse(
            answer=f"LLM chat request failed: {exc}",
            tools_used=tools_used,
            source=report.source,
        )
    answer = response.choices[0].message.content or ""
    return ChatResponse(
        answer=answer,
        tools_used=tools_used + ["llm_reasoning"],
        source=report.source,
    )


def build_agent_prompt(question: str, report: PerformanceReport) -> str:
    """Build the agent prompt from the latest report and compact metrics."""
    rows = "\n".join(format_video_metric(video) for video in top_videos(report.videos))
    timeframe = format_report_timeframe(report)
    return f"""Structured video metrics{timeframe}:
{rows}

Question: {question}
"""


def top_videos(videos: list[VideoMetric], limit: int = 20) -> list[VideoMetric]:
    """Return the highest-view videos for compact LLM context."""
    return sorted(videos, key=lambda video: video.views, reverse=True)[:limit]


def format_video_metric(video: VideoMetric) -> str:
    """Format one video record for compact LLM context."""
    return (
        f"- {video.channel_name}: {video.title}; published={video.published_at}; "
        f"views={video.views}; likes={video.likes}; comments={video.comments}; "
        f"engagement={video.engagement_rate:.2%}; views_per_day={video.views_per_day:.1f}; "
        f"rating={video.rating}; score={video.score}; reason={video.rating_reason}"
    )


def format_report_timeframe(report: PerformanceReport) -> str:
    """Format selected timeframe when available."""
    if report.timeframe_start and report.timeframe_end:
        return f" ({report.timeframe_start} to {report.timeframe_end})"
    if report.timeframe_start:
        return f" (from {report.timeframe_start})"
    if report.timeframe_end:
        return f" (through {report.timeframe_end})"
    return ""
