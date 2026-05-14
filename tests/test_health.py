"""Smoke tests for the FastAPI backend."""

from fastapi.testclient import TestClient

from backend.main import app
from services.analytics import enrich_videos
from services.sample_data import load_sample_videos
from services.youtube import parse_iso8601_duration

client = TestClient(app)


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
    assert "MoveUp Content Performance Report" in payload["markdown"]


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


def test_chat_endpoint_answers_from_current_report(monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("USE_SAMPLE_DATA", "true")
    client.get("/api/report?refresh=true")

    response = client.post("/api/chat", json={"question": "Which video dropped the most?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "sample_data"
    assert "improvement opportunity" in payload["answer"]


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
