"""High-level workflow orchestration for collection, analysis, and reporting."""

from __future__ import annotations

from datetime import UTC, datetime

from services.models import PerformanceReport, VideoMetric
from services.reporting import generate_performance_report
from services.settings import PROJECT_ROOT
from services.youtube import YouTubeMetricsClient

_cached_reports: dict[tuple[str | None, str | None], PerformanceReport] = {}


def get_or_create_report(
    refresh: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> PerformanceReport:
    """Return the latest report, refreshing data when requested."""
    normalized_start = _normalize_datetime(start_at)
    normalized_end = _normalize_datetime(end_at)
    cache_key = (
        normalized_start.isoformat() if normalized_start else None,
        normalized_end.isoformat() if normalized_end else None,
    )
    if cache_key not in _cached_reports or refresh:
        limit_per_channel = 50 if normalized_start or normalized_end else 10
        raw_videos, source = YouTubeMetricsClient().fetch_moveup_videos(
            limit_per_channel=limit_per_channel
        )
        filtered_videos = filter_videos_by_timeframe(raw_videos, normalized_start, normalized_end)
        report = generate_performance_report(
            filtered_videos,
            source,
            timeframe_start=cache_key[0],
            timeframe_end=cache_key[1],
        )
        _cached_reports[cache_key] = report
        _save_report(report)
    return _cached_reports[cache_key]


def filter_videos_by_timeframe(
    videos: list[VideoMetric],
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[VideoMetric]:
    """Return videos published inside the inclusive UTC timeframe."""
    if not start_at and not end_at:
        return videos

    filtered = []
    for video in videos:
        published_at = _parse_datetime(video.published_at)
        if start_at and published_at < start_at:
            continue
        if end_at and published_at > end_at:
            continue
        filtered.append(video)
    return filtered


def _save_report(report: PerformanceReport) -> None:
    """Save the report payload to the reports directory as JSON."""
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filepath = reports_dir / f"report_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _normalize_datetime(parsed) or datetime.now(UTC)
