"""Application entrypoint for the MoveUp Content Ops Bot API."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.content_ops_agent import answer_question
from services.models import ChatRequest, ChatResponse, PerformanceReport, VideoMetric
from services.workflow import get_or_create_report

SERVICE_NAME = "moveup-content-ops-bot"
APP_ENV = os.getenv("APP_ENV", "local")

app = FastAPI(
    title="MoveUp Content Ops Bot API",
    description="Backend API for AI-powered content operations analytics.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic service metadata."""
    return {
        "service": SERVICE_NAME,
        "message": "MoveUp Content Ops Bot API is running.",
        "environment": APP_ENV,
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Return a lightweight health check payload for local and CI checks."""
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "environment": APP_ENV,
    }


@app.get("/api/report", response_model=PerformanceReport)
def get_report(
    refresh: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> PerformanceReport:
    """Collect YouTube data and return the latest performance report."""
    return get_or_create_report(refresh=refresh, start_at=start_at, end_at=end_at)


@app.get("/api/videos", response_model=list[VideoMetric])
def get_videos(
    refresh: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[VideoMetric]:
    """Return normalized video metrics used by the report."""
    return get_or_create_report(refresh=refresh, start_at=start_at, end_at=end_at).videos


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_agent(payload: ChatRequest) -> ChatResponse:
    """Answer natural-language questions against the latest report."""
    report = get_or_create_report(refresh=False)
    return answer_question(payload.question, report)
