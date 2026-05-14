"""Streamlit dashboard entrypoint for MoveUp Content Ops Bot."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.content_ops_agent import answer_question  # noqa: E402
from services.settings import MOVEUP_CHANNELS, ChannelConfig  # noqa: E402
from services.workflow import get_or_create_report  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

APP_ENV = os.getenv("APP_ENV", "local")

st.set_page_config(
    page_title="MoveUp Content Ops Bot",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f6f7f9;
        color: #182230;
    }
    .block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
    h1, h2, h3, h4, h5, h6, p, li, label, span {
        color: #182230;
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d7dde7;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    div[data-testid="stMetric"] label { color: #64748b; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #101828; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] div {
        font-size: 1.8rem;
        line-height: 1.2;
        white-space: normal;
    }
    section[data-testid="stSidebar"] > div {
        background: #eef2f7;
        border-right: 1px solid #d7dde7;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {
        color: #182230;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #475467;
    }
    section[data-testid="stSidebar"] button {
        border-radius: 8px;
    }
    div[data-baseweb="input"],
    div[data-baseweb="select"],
    div[data-baseweb="base-input"] {
        background: #ffffff;
        color: #182230;
    }
    .hero-band {
        background: #ffffff;
        border: 1px solid #d7dde7;
        border-left: 5px solid #246b5a;
        border-radius: 8px;
        color: #182230;
        padding: 20px 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    .hero-band h1 {
        color: #182230;
        font-size: 2rem;
        margin: 0 0 6px;
    }
    .hero-band p {
        color: #475467;
        margin: 0;
    }
    .source-band {
        background: #ffffff;
        border: 1px solid #d7dde7;
        border-left: 5px solid #246b5a;
        border-radius: 8px;
        color: #182230;
        padding: 12px 14px;
        margin: 8px 0 18px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    .source-band strong { color: #182230; }
    .section-card {
        background: #ffffff;
        border: 1px solid #d7dde7;
        border-radius: 8px;
        padding: 14px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    .empty-state {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 8px;
        color: #7c2d12;
        padding: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def parse_channel_input(raw_value: str) -> list[ChannelConfig]:
    """Parse newline-separated YouTube channel handles or URLs into channel configs."""
    channels: list[ChannelConfig] = []
    seen: set[str] = set()
    for raw_line in raw_value.splitlines():
        identifier = normalize_channel_identifier(raw_line)
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        channels.append(
            ChannelConfig(name=display_name_from_identifier(identifier), handle=identifier)
        )
    return channels


def normalize_channel_identifier(raw_value: str) -> str:
    """Return a YouTube handle, channel id, or search string from user input."""
    value = raw_value.strip()
    if not value:
        return ""

    if "youtube.com" not in value and "youtu.be" not in value:
        return value if value.startswith("@") or value.startswith("UC") else f"@{value}"

    parsed = urlparse(value if "://" in value else f"https://{value}")
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""

    first_part = path_parts[0]
    if first_part.startswith("@"):
        return first_part
    if first_part == "channel" and len(path_parts) > 1:
        return path_parts[1]
    if first_part in {"c", "user"} and len(path_parts) > 1:
        return path_parts[1]
    return first_part


def display_name_from_identifier(identifier: str) -> str:
    """Create a compact display name before YouTube returns official channel metadata."""
    return identifier.lstrip("@").replace("-", " ").replace("_", " ").strip() or identifier


with st.sidebar:
    st.header("Controls")
    refresh = st.button("Refresh data", type="primary", width="stretch")
    st.divider()
    st.subheader("Channels")
    channel_input = st.text_area(
        "Paste channel links or handles",
        value="\n".join(channel.handle for channel in MOVEUP_CHANNELS),
        height=130,
        help="One per line. Supports @handles and youtube.com/@handle or /channel/UC... links.",
    )
    selected_source_channels = parse_channel_input(channel_input)
    if len(selected_source_channels) > 6:
        st.warning("Using the first 6 channels to keep the dashboard responsive.")
        selected_source_channels = selected_source_channels[:6]
    if not selected_source_channels:
        st.error("Add at least one valid YouTube channel handle or link.")
        st.stop()
    st.caption(f"{len(selected_source_channels)} channel(s) selected")
    st.divider()
    st.subheader("Report Window")
    window_mode = st.selectbox(
        "Timeframe",
        ["Latest uploads", "Last 7 days", "Last 30 days", "Custom range"],
    )
    now_utc = datetime.now(UTC)
    start_at = None
    end_at = None

    if window_mode == "Last 7 days":
        start_at = now_utc - timedelta(days=7)
        end_at = now_utc
    elif window_mode == "Last 30 days":
        start_at = now_utc - timedelta(days=30)
        end_at = now_utc
    elif window_mode == "Custom range":
        default_start_date = (now_utc - timedelta(days=30)).date()
        default_end_date = now_utc.date()
        start_date = st.date_input("From date", value=default_start_date)
        start_time = st.time_input("From time", value=time(0, 0))
        end_date = st.date_input("To date", value=default_end_date)
        end_time = st.time_input("To time", value=time(23, 59))
        start_at = datetime.combine(start_date, start_time, tzinfo=UTC)
        end_at = datetime.combine(end_date, end_time, tzinfo=UTC)

    if start_at and end_at and start_at > end_at:
        st.error("Start date/time must be before end date/time.")
        st.stop()
    st.divider()
    st.caption(f"Environment: `{APP_ENV}`")
    st.caption("Source rules")
    st.write("Facts come directly from YouTube Data API v3. AI text is separated from raw data.")

report = get_or_create_report(
    refresh=refresh,
    start_at=start_at,
    end_at=end_at,
    channels=tuple(selected_source_channels),
)
videos = report.videos
channels = report.channels

video_df = pd.DataFrame([video.model_dump() for video in videos])
channel_df = pd.DataFrame([channel.model_dump() for channel in channels])
display_df = video_df.copy()

if not video_df.empty:
    if "collected_at" not in video_df.columns:
        video_df["collected_at"] = report.generated_at
    video_df["collected_at"] = video_df["collected_at"].replace("", report.generated_at)
    video_df["published_at_display"] = pd.to_datetime(video_df["published_at"]).dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    video_df["collected_at_display"] = pd.to_datetime(video_df["collected_at"]).dt.strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    video_df["duration"] = video_df["duration_seconds"].apply(
        lambda seconds: f"{seconds // 60}:{seconds % 60:02d}"
    )
    video_df["engagement_pct"] = video_df["engagement_rate"] * 100
    video_df["watch"] = video_df["url"]
    video_df["channel"] = video_df["channel_url"]
    display_df = video_df.copy()

with st.sidebar:
    st.divider()
    st.subheader("Dashboard Filters")
    available_channels = sorted(video_df["channel_name"].unique()) if not video_df.empty else []
    selected_channels = st.multiselect(
        "Channels",
        available_channels,
        default=available_channels,
        disabled=not available_channels,
    )
    if selected_channels:
        display_df = video_df[video_df["channel_name"].isin(selected_channels)].copy()
    elif not video_df.empty:
        display_df = video_df.iloc[0:0].copy()
    st.caption(f"Showing {len(display_df)} of {len(video_df)} videos")

timeframe_label = "Latest available uploads"
if report.timeframe_start and report.timeframe_end:
    timeframe_label = f"{report.timeframe_start} to {report.timeframe_end}"
elif report.timeframe_start:
    timeframe_label = f"From {report.timeframe_start}"
elif report.timeframe_end:
    timeframe_label = f"Until {report.timeframe_end}"

st.markdown(
    """
    <div class="hero-band">
        <h1>MoveUp Content Ops Bot</h1>
        <p>
            Live YouTube performance facts, AI analysis, and a date-aware content
            operations dashboard.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

source_label = "YouTube Data API v3" if report.source == "youtube_api" else "Sample demo data"
collected_at = video_df["collected_at_display"].max() if not video_df.empty else report.generated_at
st.markdown(
    f"""
    <div class="source-band">
    <strong>Source of truth:</strong> {source_label}<br>
    <strong>Channels:</strong> {", ".join(channel.name for channel in selected_source_channels)}<br>
    <strong>Report window:</strong> {timeframe_label}<br>
    <strong>Scope:</strong> public playable uploads matching the selected window<br>
    <strong>Collected:</strong> {collected_at}<br>
    <strong>Accuracy note:</strong> titles, IDs, URLs, publish dates, views, likes, comments,
    and durations are displayed exactly from the YouTube API response.
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(5)
display_channel_count = display_df["channel_name"].nunique() if not display_df.empty else 0
display_total_views = int(display_df["views"].sum()) if not display_df.empty else 0
metric_cols[0].metric("Channels", display_channel_count)
metric_cols[1].metric("Videos", len(display_df))
metric_cols[2].metric("Total Views", f"{display_total_views:,}")
avg_engagement = display_df["engagement_rate"].mean() if not display_df.empty else 0
metric_cols[3].metric("Avg Engagement", f"{avg_engagement:.2%}")
metric_cols[4].metric("Data Source", source_label)

tab_overview, tab_videos, tab_report, tab_agent = st.tabs(
    ["Overview", "Source Data", "AI Report", "Ask Agent"]
)

with tab_overview:
    if display_df.empty:
        st.markdown(
            (
                '<div class="empty-state">No videos match the current filters. '
                "Adjust the sidebar controls or refresh the data.</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        left, right = st.columns([1.1, 0.9])
        with left:
            st.subheader("Channel Performance")
            display_channel_df = (
                display_df.groupby("channel_name", as_index=False)
                .agg(total_views=("views", "sum"), avg_engagement_rate=("engagement_rate", "mean"))
                .sort_values("total_views", ascending=False)
            )
            fig = px.bar(
                display_channel_df,
                x="channel_name",
                y="total_views",
                color="avg_engagement_rate",
                text="total_views",
                color_continuous_scale="Teal",
                labels={
                    "channel_name": "Channel",
                    "total_views": "Total views",
                    "avg_engagement_rate": "Avg engagement",
                },
            )
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#182230",
                xaxis_title="",
                yaxis_title="Views",
                coloraxis_colorbar_title="Engagement",
                margin={"l": 10, "r": 10, "t": 30, "b": 10},
            )
            st.plotly_chart(fig, width="stretch")

        with right:
            st.subheader("Top Ranked Videos")
            top_rows = display_df.sort_values("score", ascending=False).head(5)
            top_rows = top_rows.assign(
                engagement_display=top_rows["engagement_pct"].map(lambda value: f"{value:.2f}%")
            )
            st.dataframe(
                top_rows[
                    [
                        "thumbnail_url",
                        "channel_name",
                        "title",
                        "views",
                        "engagement_display",
                        "rating",
                        "watch",
                    ]
                ],
                hide_index=True,
                width="stretch",
                column_config={
                    "thumbnail_url": st.column_config.ImageColumn("Preview"),
                    "channel_name": "Channel",
                    "title": "Exact YouTube Title",
                    "views": st.column_config.NumberColumn("Views", format="%d"),
                    "engagement_display": "Engagement",
                    "rating": "Rating",
                    "watch": st.column_config.LinkColumn("Watch"),
                },
            )

        st.subheader("Executive Summary")
        st.write(report.summary)

with tab_videos:
    st.subheader("Source Data From YouTube")
    if display_df.empty:
        st.markdown(
            '<div class="empty-state">No source rows match the sidebar filters.</div>',
            unsafe_allow_html=True,
        )
    else:
        filtered_df = display_df.sort_values(
            ["channel_name", "published_at"], ascending=[True, False]
        )
        st.dataframe(
            filtered_df[
                [
                    "thumbnail_url",
                    "channel_name",
                    "video_id",
                    "title",
                    "published_at_display",
                    "duration",
                    "views",
                    "likes",
                    "comments",
                    "engagement_pct",
                    "content_type",
                    "watch",
                    "channel",
                ]
            ],
            hide_index=True,
            width="stretch",
            height=560,
            column_config={
                "thumbnail_url": st.column_config.ImageColumn("Preview"),
                "channel_name": "Channel",
                "video_id": "Video ID",
                "title": "Exact YouTube Title",
                "published_at_display": "Published",
                "duration": "Duration",
                "views": st.column_config.NumberColumn("Views", format="%d"),
                "likes": st.column_config.NumberColumn("Likes", format="%d"),
                "comments": st.column_config.NumberColumn("Comments", format="%d"),
                "engagement_pct": st.column_config.NumberColumn("Engagement %", format="%.2f"),
                "content_type": "Type",
                "watch": st.column_config.LinkColumn("Watch"),
                "channel": st.column_config.LinkColumn("Channel"),
            },
        )
        st.download_button(
            "Download exact source CSV",
            filtered_df.to_csv(index=False).encode("utf-8"),
            "moveup_youtube_source_data.csv",
            "text/csv",
            width="stretch",
        )

with tab_report:
    st.subheader("AI-Generated Performance Report")
    st.info(
        "The table in Source Data is the source of truth. This section is generated analysis "
        "grounded in that table."
    )
    st.markdown(report.markdown)

with tab_agent:
    st.subheader("Ask The Content Ops Agent")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask which video dropped most, what to focus on this week, or compare channels"
    )
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        response = answer_question(question, report)
        with st.chat_message("assistant"):
            st.markdown(response.answer)
        st.session_state.messages.append({"role": "assistant", "content": response.answer})
