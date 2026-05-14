"""Analytics and scoring utilities for YouTube performance data."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from services.models import ChannelReport, VideoMetric


def enrich_videos(videos: list[VideoMetric]) -> list[VideoMetric]:
    """Add engagement, velocity, score, and rating fields to each video."""
    now = datetime.now(UTC)
    by_channel: dict[str, list[VideoMetric]] = defaultdict(list)
    for video in videos:
        by_channel[video.channel_name].append(video)

    enriched: list[VideoMetric] = []
    for channel_videos in by_channel.values():
        avg_views = _safe_avg([video.views for video in channel_videos])
        engagement_rates = [_engagement_rate(video) for video in channel_videos]
        avg_engagement = _safe_avg(engagement_rates)

        for video, engagement_rate in zip(channel_videos, engagement_rates, strict=True):
            age_seconds = (now - _parse_published_at(video.published_at)).total_seconds()
            age_days = max(age_seconds / 86400, 1)
            views_per_day = video.views / age_days
            view_index = video.views / avg_views if avg_views else 0
            engagement_index = engagement_rate / avg_engagement if avg_engagement else 0
            score = round((view_index * 0.65 + engagement_index * 0.35) * 100, 1)
            rating = _rating_from_score(score)
            rounded_engagement_rate = round(engagement_rate, 4)
            reason = _rating_reason(video, rounded_engagement_rate, view_index, engagement_index)
            enriched.append(
                video.model_copy(
                    update={
                        "engagement_rate": rounded_engagement_rate,
                        "views_per_day": round(views_per_day, 1),
                        "score": score,
                        "rating": rating,
                        "rating_reason": reason,
                    }
                )
            )

    return sorted(
        enriched,
        key=lambda video: (video.channel_name, video.published_at),
        reverse=True,
    )


def summarize_channels(videos: list[VideoMetric]) -> list[ChannelReport]:
    """Build channel-level summaries from enriched videos."""
    by_channel: dict[str, list[VideoMetric]] = defaultdict(list)
    for video in videos:
        by_channel[video.channel_name].append(video)

    reports: list[ChannelReport] = []
    for channel_name, channel_videos in sorted(by_channel.items()):
        ordered = sorted(channel_videos, key=lambda video: video.score, reverse=True)
        top_video = ordered[0] if ordered else None
        bottom_video = ordered[-1] if ordered else None
        avg_engagement = _safe_avg([video.engagement_rate for video in channel_videos])
        recommendation = _channel_recommendation(channel_name, ordered, avg_engagement)
        reports.append(
            ChannelReport(
                channel_name=channel_name,
                channel_handle=channel_videos[0].channel_handle,
                video_count=len(channel_videos),
                total_views=sum(video.views for video in channel_videos),
                avg_views=round(_safe_avg([video.views for video in channel_videos]), 1),
                avg_engagement_rate=round(avg_engagement, 4),
                top_video_title=top_video.title if top_video else None,
                bottom_video_title=bottom_video.title if bottom_video else None,
                recommendation=recommendation,
            )
        )
    return reports


def top_videos(videos: list[VideoMetric], count: int = 3) -> list[VideoMetric]:
    """Return top videos by score."""
    return sorted(videos, key=lambda video: video.score, reverse=True)[:count]


def bottom_videos(videos: list[VideoMetric], count: int = 3) -> list[VideoMetric]:
    """Return lowest-performing videos by score."""
    return sorted(videos, key=lambda video: video.score)[:count]


def _engagement_rate(video: VideoMetric) -> float:
    if video.views <= 0:
        return 0.0
    return (video.likes + video.comments) / video.views


def _safe_avg(values: list[float] | list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _parse_published_at(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _rating_from_score(score: float) -> str:
    if score >= 120:
        return "strong"
    if score < 80:
        return "underperforming"
    return "average"


def _rating_reason(
    video: VideoMetric,
    engagement_rate: float,
    view_index: float,
    engagement_index: float,
) -> str:
    view_note = "above" if view_index >= 1 else "below"
    engagement_note = "above" if engagement_index >= 1 else "below"
    return (
        f"{video.views:,} views and {engagement_rate:.2%} engagement; "
        f"views are {view_note} this channel's average and engagement is {engagement_note} average."
    )


def _channel_recommendation(
    channel_name: str,
    ordered_videos: list[VideoMetric],
    avg_engagement: float,
) -> str:
    if not ordered_videos:
        return "Collect more data before making programming decisions."

    top = ordered_videos[0]
    bottom = ordered_videos[-1]
    if avg_engagement < 0.035:
        return (
            f"For {channel_name}, prioritize stronger calls to comment and subscribe, then reuse "
            f"the topic framing from '{top.title}' to lift engagement."
        )
    return (
        f"For {channel_name}, package more videos around the audience promise in '{top.title}' "
        f"and rework formats similar to '{bottom.title}' with a clearer hook in the "
        "first 30 seconds."
    )
