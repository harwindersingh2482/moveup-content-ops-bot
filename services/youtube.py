"""YouTube Data API ingestion for channel and video metrics."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from googleapiclient.discovery import build

from services.models import VideoMetric
from services.sample_data import load_sample_videos
from services.settings import MOVEUP_CHANNELS, ChannelConfig, get_youtube_api_key, use_sample_data


class YouTubeDataError(RuntimeError):
    """Raised when YouTube data cannot be collected."""


class YouTubeMetricsClient:
    """Fetch public YouTube channel and video metrics."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_youtube_api_key()
        self._service = None

    @property
    def service(self) -> Any:
        """Build the YouTube service lazily."""
        if not self.api_key:
            raise YouTubeDataError("YOUTUBE_API_KEY is required when sample data is disabled.")
        if self._service is None:
            self._service = build("youtube", "v3", developerKey=self.api_key)
        return self._service

    def fetch_moveup_videos(
        self,
        limit_per_channel: int = 10,
        channels: tuple[ChannelConfig, ...] = MOVEUP_CHANNELS,
    ) -> tuple[list[VideoMetric], str]:
        """Fetch videos for the selected YouTube channels, or sample data if configured."""
        if not self.api_key:
            if use_sample_data():
                sample_limit = limit_per_channel * len(MOVEUP_CHANNELS)
                return load_sample_videos()[:sample_limit], "sample_data"
            raise YouTubeDataError("Set YOUTUBE_API_KEY or USE_SAMPLE_DATA=true.")

        videos: list[VideoMetric] = []
        for channel in channels:
            channel_id = self.resolve_channel_id(channel)
            upload_playlist_id = self.fetch_upload_playlist_id(channel_id)
            video_ids = self.fetch_recent_video_ids(upload_playlist_id, 50)
            channel_videos = self.fetch_video_metrics(channel, channel_id, video_ids)
            videos.extend(channel_videos[:limit_per_channel])
        return videos, "youtube_api"

    def resolve_channel_id(self, channel: ChannelConfig) -> str:
        """Resolve a channel handle such as @Netflu to a YouTube channel id."""
        if channel.handle.startswith("UC"):
            return channel.handle

        response = (
            self.service.channels()
            .list(part="id", forHandle=channel.handle.lstrip("@"))
            .execute()
        )
        items = response.get("items", [])
        if items:
            return items[0]["id"]

        search_response = (
            self.service.search()
            .list(part="snippet", q=channel.handle, type="channel", maxResults=1)
            .execute()
        )
        search_items = search_response.get("items", [])
        if not search_items:
            raise YouTubeDataError(f"Could not resolve YouTube channel {channel.handle}.")
        return search_items[0]["snippet"]["channelId"]

    def fetch_upload_playlist_id(self, channel_id: str) -> str:
        """Return the uploads playlist id for a channel."""
        response = (
            self.service.channels()
            .list(part="contentDetails", id=channel_id, maxResults=1)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise YouTubeDataError(f"Could not load uploads playlist for channel {channel_id}.")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def fetch_recent_video_ids(self, upload_playlist_id: str, limit: int) -> list[str]:
        """Return recent public video ids from a channel's uploads playlist."""
        response = (
            self.service.playlistItems()
            .list(part="contentDetails", playlistId=upload_playlist_id, maxResults=limit)
            .execute()
        )
        return [
            item["contentDetails"]["videoId"]
            for item in response.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]

    def fetch_video_metrics(
        self,
        channel: ChannelConfig,
        channel_id: str,
        video_ids: list[str],
    ) -> list[VideoMetric]:
        """Fetch snippet, statistics, and duration for a list of video ids."""
        if not video_ids:
            return []

        response = (
            self.service.videos()
            .list(
                part="snippet,statistics,contentDetails,status",
                id=",".join(video_ids),
                maxResults=50,
            )
            .execute()
        )
        videos_by_id: dict[str, VideoMetric] = {}
        collected_at = datetime.now(UTC).isoformat()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})
            status = item.get("status", {})
            duration_seconds = parse_iso8601_duration(details.get("duration", "PT0S"))
            if status.get("privacyStatus") != "public" or duration_seconds <= 0:
                continue
            video_id = item["id"]
            videos_by_id[video_id] = (
                VideoMetric(
                    video_id=video_id,
                    channel_name=channel.name,
                    channel_handle=channel.handle,
                    channel_id=channel_id,
                    channel_url=f"https://www.youtube.com/channel/{channel_id}",
                    title=snippet.get("title", "Untitled video"),
                    published_at=snippet.get("publishedAt", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    thumbnail_url=_best_thumbnail_url(snippet.get("thumbnails", {})),
                    content_type=_content_type(duration_seconds),
                    views=_to_int(stats.get("viewCount")),
                    likes=_to_int(stats.get("likeCount")),
                    comments=_to_int(stats.get("commentCount")),
                    duration_seconds=duration_seconds,
                    collected_at=collected_at,
                )
            )
        return [videos_by_id[video_id] for video_id in video_ids if video_id in videos_by_id]


def parse_iso8601_duration(value: str) -> int:
    """Parse a YouTube ISO 8601 duration into seconds."""
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T?"
        r"(?:(?P<hours>\d+)H)?"
        r"(?:(?P<minutes>\d+)M)?"
        r"(?:(?P<seconds>\d+)S)?",
        value,
    )
    if not match:
        return 0
    parts = {key: int(raw or 0) for key, raw in match.groupdict().items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _best_thumbnail_url(thumbnails: dict[str, Any]) -> str:
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbnails and thumbnails[key].get("url"):
            return thumbnails[key]["url"]
    return ""


def _content_type(duration_seconds: int) -> str:
    if duration_seconds <= 180:
        return "short-form"
    return "long-form"
