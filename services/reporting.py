"""LLM report generation with a deterministic fallback."""

from __future__ import annotations

from datetime import UTC, datetime

from openai import OpenAI

from services.analytics import bottom_videos, enrich_videos, summarize_channels, top_videos
from services.models import PerformanceReport, VideoMetric
from services.settings import get_llm_api_key, get_llm_base_url, get_llm_model

REPORT_SYSTEM_PROMPT = """You are a senior media analyst for MoveUp Media, a digital agency.
Analyze YouTube performance for weekly content operations. Be concrete, business-focused,
and useful to channel managers. Public YouTube data does not expose CTR or audience retention,
so never invent those metrics; instead use views, engagement rate, comments, likes, recency,
and relative channel benchmarks.
"""


def generate_performance_report(
    videos: list[VideoMetric],
    source: str,
    timeframe_start: str | None = None,
    timeframe_end: str | None = None,
) -> PerformanceReport:
    """Create a structured performance report from video metrics."""
    enriched = enrich_videos(videos)
    channels = summarize_channels(enriched)
    timeframe_label = build_timeframe_label(timeframe_start, timeframe_end)
    source_fact_sheet = build_source_fact_sheet(enriched, timeframe_label)
    fallback_markdown = build_fallback_markdown(enriched, channels, timeframe_label)
    ai_markdown = generate_llm_markdown(enriched, fallback_markdown)
    summary = build_summary(enriched)
    return PerformanceReport(
        source=source,
        generated_at=datetime.now(UTC).isoformat(),
        timeframe_start=timeframe_start,
        timeframe_end=timeframe_end,
        summary=summary,
        markdown=f"{source_fact_sheet}\n\n{ai_markdown}",
        videos=enriched,
        channels=channels,
    )


def generate_llm_markdown(videos: list[VideoMetric], fallback_markdown: str) -> str:
    """Generate report markdown with OpenAI when configured."""
    api_key = get_llm_api_key()
    if not api_key:
        return fallback_markdown

    client = OpenAI(api_key=api_key, base_url=get_llm_base_url())
    prompt = build_report_prompt(videos)
    try:
        response = client.chat.completions.create(
            model=get_llm_model(),
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception:
        return fallback_markdown
    return response.choices[0].message.content or fallback_markdown


def build_report_prompt(videos: list[VideoMetric]) -> str:
    """Build the prompt used for report generation."""
    rows = "\n".join(
        (
            f"- {video.channel_name} | {video.title} | views={video.views} | "
            f"likes={video.likes} | comments={video.comments} | "
            f"engagement={video.engagement_rate:.2%} | score={video.score} | "
            f"rating={video.rating} | published={video.published_at} | "
            f"video_id={video.video_id} | url={video.url}"
        )
        for video in videos
    )
    return f"""Create a Markdown performance report for MoveUp Media's last 10 videos per channel.

Required sections:
1. Executive summary across both channels.
2. Per-channel analysis.
3. Per-video rating table with rating strong / average / underperforming and one brief reason.
4. Top 2-3 videos and bottom 2-3 videos with reasoning.
5. At least one concrete, actionable recommendation per channel for next week.

Tone: professional, direct, actionable. Avoid generic advice.
Accuracy rules:
- Copy video titles exactly as provided.
- Use only the provided video ids and URLs.
- Do not invent metrics, titles, videos, links, CTR, or retention.
Important: CTR and retention are not available from public YouTube Data API responses;
mention this limitation only if relevant and do not fabricate unavailable metrics.

Data:
{rows}
"""


def build_source_fact_sheet(videos: list[VideoMetric], timeframe_label: str) -> str:
    """Build a deterministic source-of-truth table before AI commentary."""
    lines = [
        "# Source Data From YouTube API",
        "",
        "The table below is generated directly from YouTube Data API v3. "
        "It is the source of truth for titles, links, dates, and metrics.",
        "",
        f"**Report timeframe:** {timeframe_label}",
        "",
        "| Channel | Published | Exact Title | Views | Likes | Comments | Duration | Link |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for video in sorted(videos, key=lambda item: (item.channel_name, item.published_at)):
        lines.append(
            f"| {video.channel_name} | {video.published_at} | {_escape_table(video.title)} | "
            f"{video.views:,} | {video.likes:,} | {video.comments:,} | "
            f"{video.duration_seconds}s | [Watch]({video.url}) |"
        )
    return "\n".join(lines)


def build_fallback_markdown(
    videos: list[VideoMetric],
    channels: list,
    timeframe_label: str,
) -> str:
    """Create a deterministic report when no LLM key is present."""
    top = top_videos(videos)
    bottom = bottom_videos(videos)
    lines = [
        "# MoveUp Content Performance Report",
        "",
        "## Executive Summary",
        f"Timeframe: {timeframe_label}",
        "",
        build_summary(videos),
        "",
        "Public YouTube metrics do not include CTR or audience retention, so this analysis "
        "uses views, likes, comments, engagement rate, recency velocity, and relative "
        "channel benchmarks.",
        "",
        "## Channel Recommendations",
    ]
    for channel in channels:
        lines.extend(
            [
                f"### {channel.channel_name}",
                f"- Videos analyzed: {channel.video_count}",
                f"- Total views: {channel.total_views:,}",
                f"- Average views: {channel.avg_views:,.0f}",
                f"- Average engagement rate: {channel.avg_engagement_rate:.2%}",
                f"- Recommendation: {channel.recommendation}",
                "",
            ]
        )

    lines.extend(["## Top Videos", ""])
    lines.extend(_video_bullets(top))
    lines.extend(["", "## Bottom Videos", ""])
    lines.extend(_video_bullets(bottom))
    lines.extend(["", "## Per-Video Ratings", ""])
    lines.append("| Channel | Video | Rating | Score | Reason |")
    lines.append("| --- | --- | --- | ---: | --- |")
    for video in sorted(videos, key=lambda item: (item.channel_name, -item.score)):
        lines.append(
            f"| {video.channel_name} | [{video.title}]({video.url}) | {video.rating} | "
            f"{video.score:.1f} | {video.rating_reason} |"
        )
    return "\n".join(lines)


def build_summary(videos: list[VideoMetric]) -> str:
    """Build a compact summary sentence for the current dataset."""
    if not videos:
        return "No videos were available for analysis."
    total_views = sum(video.views for video in videos)
    avg_engagement = sum(video.engagement_rate for video in videos) / len(videos)
    strongest = max(videos, key=lambda video: video.score)
    weakest = min(videos, key=lambda video: video.score)
    channel_count = len({video.channel_name for video in videos})
    return (
        f"Analyzed {len(videos)} recent videos across {channel_count} "
        f"MoveUp channels. The set generated {total_views:,} views with an average engagement rate "
        f"of {avg_engagement:.2%}. Strongest performer: '{strongest.title}'. Biggest improvement "
        f"opportunity: '{weakest.title}'."
    )


def build_timeframe_label(timeframe_start: str | None, timeframe_end: str | None) -> str:
    """Build a human-readable label for the selected report window."""
    if timeframe_start and timeframe_end:
        return f"{timeframe_start} to {timeframe_end}"
    if timeframe_start:
        return f"From {timeframe_start}"
    if timeframe_end:
        return f"Until {timeframe_end}"
    return "Latest available uploads"


def _video_bullets(videos: list[VideoMetric]) -> list[str]:
    return [
        f"- **{video.channel_name}: [{video.title}]({video.url})** - {video.views:,} views, "
        f"{video.engagement_rate:.2%} engagement, score {video.score:.1f}. {video.rating_reason}"
        for video in videos
    ]


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")
