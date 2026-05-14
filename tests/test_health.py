"""Smoke tests for the FastAPI backend."""

from fastapi.testclient import TestClient

from agents import content_ops_agent
from agents.content_ops_agent import AGENT_SYSTEM_PROMPT, answer_question, build_agent_prompt
from backend.main import app
from services.analytics import enrich_videos
from services.models import PerformanceReport, VideoMetric
from services.reporting import generate_performance_report
from services.sample_data import load_sample_videos
from services.youtube import parse_iso8601_duration

client = TestClient(app)


class FakeOpenAI:
    """Small test double for OpenAI chat completions."""

    captured_messages = []

    def __init__(self, *args, **kwargs) -> None:
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.__class__.captured_messages = kwargs["messages"]
        message = type("Message", (), {"content": "RAW LLM ANSWER"})
        choice = type("Choice", (), {"message": message})
        return type("Response", (), {"choices": [choice]})


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "moveup-content-ops-bot"


def test_report_endpoint_uses_sample_data_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("USE_SAMPLE_DATA", "true")

    response = client.get("/api/report?refresh=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "sample_data"
    assert len(payload["videos"]) == 20
    assert "YouTube Content Performance Report" in payload["markdown"]


def test_report_endpoint_filters_by_publish_timeframe(monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("USE_SAMPLE_DATA", "true")

    response = client.get(
        "/api/report",
        params={
            "refresh": "true",
            "start_at": "2026-05-01T00:00:00Z",
            "end_at": "2026-05-10T23:59:00Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["timeframe_start"] == "2026-05-01T00:00:00+00:00"
    assert payload["timeframe_end"] == "2026-05-10T23:59:00+00:00"
    assert {video["video_id"] for video in payload["videos"]} == {
        "netflu-01",
        "netflu-02",
        "playoffs-01",
        "playoffs-02",
        "playoffs-03",
    }
    assert "Report timeframe" in payload["markdown"]


def test_chat_endpoint_returns_raw_llm_answer(monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("USE_SAMPLE_DATA", "true")
    monkeypatch.setattr(content_ops_agent, "OpenAI", FakeOpenAI)
    client.get("/api/report?refresh=true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    response = client.post("/api/chat", json={"question": "Which video dropped the most?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "sample_data"
    assert payload["answer"] == "RAW LLM ANSWER"
    assert payload["tools_used"] == ["current_performance_report", "llm_reasoning"]
    assert FakeOpenAI.captured_messages[0]["content"] == AGENT_SYSTEM_PROMPT
    assert "Which video dropped the most?" in FakeOpenAI.captured_messages[1]["content"]
    assert "Latest generated report:" not in FakeOpenAI.captured_messages[1]["content"]
    assert "Structured video metrics:" in FakeOpenAI.captured_messages[1]["content"]


def test_agent_returns_raw_llm_response_without_local_override(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    report = generate_performance_report(load_sample_videos(), "sample_data")

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(content_ops_agent, "OpenAI", FakeOpenAI)

    response = answer_question("Compare the channels and tell me which is stronger", report)

    assert response.answer == "RAW LLM ANSWER"


def test_agent_prompt_includes_top_video_metrics_and_question(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    report = generate_performance_report(load_sample_videos(), "sample_data")
    prompt = build_agent_prompt("What should we focus on this week?", report)

    assert "Question: What should we focus on this week?" in prompt
    assert "Latest generated report:" not in prompt
    assert report.markdown not in prompt
    assert "Structured video metrics:" in prompt
    assert "views=" in prompt
    assert "engagement=" in prompt
    assert "likes=" in prompt
    assert "comments=" in prompt
    assert "views_per_day=" in prompt


def test_agent_prompt_truncates_to_20_videos_by_views() -> None:
    videos = [
        VideoMetric(
            video_id=f"alpha-{index}",
            channel_name="Alpha",
            channel_handle="@Alpha",
            title=f"Alpha video {index}",
            published_at="2026-05-01T00:00:00Z",
            url=f"https://example.com/alpha-{index}",
            views=index,
        )
        for index in range(12)
    ] + [
        VideoMetric(
            video_id=f"beta-{index}",
            channel_name="Beta",
            channel_handle="@Beta",
            title=f"Beta video {index}",
            published_at="2026-05-01T00:00:00Z",
            url=f"https://example.com/beta-{index}",
            views=index,
        )
        for index in range(12)
    ]
    report = PerformanceReport(
        source="sample_data",
        generated_at="2026-05-14T00:00:00Z",
        summary="summary",
        markdown="FULL REPORT MARKDOWN",
        videos=videos,
        channels=[],
    )

    prompt = build_agent_prompt("Which videos matter?", report)

    assert prompt.count("- ") == 20
    assert "Alpha video 0;" not in prompt
    assert "Alpha video 1;" not in prompt
    assert "Beta video 0;" not in prompt
    assert "Beta video 1;" not in prompt


def test_enrich_videos_assigns_ratings() -> None:
    enriched = enrich_videos(load_sample_videos())

    assert len(enriched) == 20
    assert {video.rating for video in enriched}.issubset({"strong", "average", "underperforming"})
    assert all(video.rating_reason for video in enriched)


def test_enrich_videos_rating_reason_uses_calculated_engagement() -> None:
    enriched = enrich_videos(load_sample_videos())
    first = enriched[0]

    assert f"{first.engagement_rate:.2%} engagement" in first.rating_reason


def test_parse_iso8601_duration() -> None:
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT12M") == 720
    assert parse_iso8601_duration("P1DT1H") == 90000
