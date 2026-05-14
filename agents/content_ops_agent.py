"""Conversational agent for answering questions about the current report."""

from __future__ import annotations

from openai import OpenAI

from services.analytics import bottom_videos, top_videos
from services.models import ChatResponse, PerformanceReport, VideoMetric
from services.settings import get_llm_api_key, get_llm_base_url, get_llm_model

AGENT_SYSTEM_PROMPT = (
    "You are MoveUp Media's content operations analyst.\n"
    "Answer questions using only the provided YouTube performance report and video metrics.\n"
    "Be concise, cite concrete videos or channels, and recommend next actions when useful.\n"
    "If a requested metric is not available from public YouTube data, say so and use the "
    "closest available proxy.\n"
)


def answer_question(question: str, report: PerformanceReport) -> ChatResponse:
    """Answer a natural-language question against a generated report."""
    tools_used = ["current_performance_report"]
    local_answer = answer_with_local_tools(question, report.videos)

    api_key = get_llm_api_key()
    if not api_key:
        return ChatResponse(answer=local_answer, tools_used=tools_used, source=report.source)

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
    except Exception:
        return ChatResponse(answer=local_answer, tools_used=tools_used, source=report.source)
    answer = response.choices[0].message.content or local_answer
    return ChatResponse(
        answer=answer,
        tools_used=tools_used + ["llm_reasoning"],
        source=report.source,
    )


def answer_with_local_tools(question: str, videos: list[VideoMetric]) -> str:
    """Deterministic tool-style answers for common operator questions."""
    normalized = question.lower()
    if not videos:
        return "No video data is currently available. Generate a report first."

    underperforming_terms = ["dropped", "drop", "worst", "lowest", "bottom", "underperform"]
    if any(term in normalized for term in underperforming_terms):
        video = bottom_videos(videos, 1)[0]
        return (
            f"The biggest improvement opportunity is '{video.title}' on {video.channel_name}. "
            f"It scored {video.score:.1f}, with {video.views:,} views and "
            f"{video.engagement_rate:.2%} engagement. {video.rating_reason}"
        )

    if any(term in normalized for term in ["compare", "channel", "channels", "stronger"]):
        return _compare_channels(videos)

    if any(term in normalized for term in ["best", "top", "strong", "worked"]):
        video = top_videos(videos, 1)[0]
        return (
            f"The strongest recent video is '{video.title}' on {video.channel_name}. It scored "
            f"{video.score:.1f}, driven by {video.views:,} views and "
            f"{video.engagement_rate:.2%} engagement."
        )

    if any(term in normalized for term in ["focus", "recommend", "next", "week", "action"]):
        recommendations = []
        seen = set()
        for video in top_videos(videos, 4):
            if video.channel_name in seen:
                continue
            seen.add(video.channel_name)
            recommendations.append(
                f"{video.channel_name}: build next week's packaging around the promise of "
                f"'{video.title}' and strengthen the opening hook for lower-scoring formats."
            )
        return " ".join(recommendations)

    return (
        "The current report shows the strongest opportunities are to repeat high-scoring topics, "
        "tighten the first 30 seconds of underperforming formats, and track engagement rate as the "
        "best public proxy for audience resonance."
    )


def _compare_channels(videos: list[VideoMetric]) -> str:
    """Compare selected channels on public performance metrics."""
    by_channel: dict[str, list[VideoMetric]] = {}
    for video in videos:
        by_channel.setdefault(video.channel_name, []).append(video)

    rows = []
    for channel_name, channel_videos in by_channel.items():
        total_views = sum(video.views for video in channel_videos)
        avg_views = total_views / len(channel_videos)
        avg_engagement = sum(video.engagement_rate for video in channel_videos) / len(
            channel_videos
        )
        avg_score = sum(video.score for video in channel_videos) / len(channel_videos)
        top_video = max(channel_videos, key=lambda video: video.score)
        rows.append((channel_name, total_views, avg_views, avg_engagement, avg_score, top_video))

    ordered = sorted(rows, key=lambda row: (row[1], row[4]), reverse=True)
    leader = ordered[0]
    comparison = "; ".join(
        (
            f"{channel}: {total_views:,} views, {avg_views:,.0f} avg views/video, "
            f"{avg_engagement:.2%} avg engagement"
        )
        for channel, total_views, avg_views, avg_engagement, _, _ in ordered
    )
    return (
        f"{leader[0]} is strongest on recent public performance, led by {leader[1]:,} total "
        f"views and {leader[2]:,.0f} average views per video. Channel comparison: {comparison}. "
        f"Best topic signal: '{leader[5].title}'."
    )


def build_agent_prompt(question: str, report: PerformanceReport) -> str:
    """Build the agent prompt from the latest report and compact metrics."""
    rows = "\n".join(
        (
            f"- {video.channel_name}: {video.title}; rating={video.rating}; score={video.score}; "
            f"views={video.views}; engagement={video.engagement_rate:.2%}; "
            f"reason={video.rating_reason}"
        )
        for video in report.videos
    )
    return f"""Question: {question}

Latest generated report:
{report.markdown}

Structured video metrics:
{rows}
"""
