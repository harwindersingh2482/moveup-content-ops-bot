"""Shared domain models for YouTube analytics and reporting."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VideoMetric(BaseModel):
    """A normalized YouTube video metric record."""

    video_id: str
    channel_name: str
    channel_handle: str
    channel_id: str = ""
    channel_url: str = ""
    title: str
    published_at: str
    url: str
    thumbnail_url: str = ""
    content_type: str = "video"
    views: int = 0
    likes: int = 0
    comments: int = 0
    duration_seconds: int = 0
    collected_at: str = ""
    engagement_rate: float = 0.0
    views_per_day: float = 0.0
    score: float = 0.0
    rating: str = "average"
    rating_reason: str = ""


class ChannelReport(BaseModel):
    """Aggregated channel-level performance context."""

    channel_name: str
    channel_handle: str
    video_count: int
    total_views: int
    avg_views: float
    avg_engagement_rate: float
    top_video_title: str | None = None
    bottom_video_title: str | None = None
    recommendation: str


class PerformanceReport(BaseModel):
    """Full report payload returned by the backend and displayed by the UI."""

    source: str = Field(description="youtube_api or sample_data")
    generated_at: str
    timeframe_start: str | None = None
    timeframe_end: str | None = None
    summary: str
    markdown: str
    videos: list[VideoMetric]
    channels: list[ChannelReport]


class ChatRequest(BaseModel):
    """Natural-language question sent by the management interface."""

    question: str


class ChatResponse(BaseModel):
    """Conversational answer grounded in the current performance report."""

    answer: str
    tools_used: list[str]
    source: str
