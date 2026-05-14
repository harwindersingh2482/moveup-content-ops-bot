"""Application settings for channels, API keys, and runtime behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class ChannelConfig:
    """YouTube channel configured for analysis."""

    name: str
    handle: str
    category: str = "owned"


MOVEUP_CHANNELS: tuple[ChannelConfig, ...] = (
    ChannelConfig(name="Netflu", handle="@Netflu"),
    ChannelConfig(name="ThePlayoffsTV", handle="@ThePlayoffsTV"),
)


def get_youtube_api_key() -> str | None:
    """Return the configured YouTube API key, if present."""
    return os.getenv("YOUTUBE_API_KEY") or None


def get_openai_api_key() -> str | None:
    """Return the configured OpenAI API key, if present."""
    return os.getenv("OPENAI_API_KEY") or None


def get_openai_model() -> str:
    """Return the OpenAI model used for report and chat generation."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_llm_provider() -> str:
    """Return the configured LLM provider."""
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def get_llm_api_key() -> str | None:
    """Return the API key for the configured LLM provider."""
    provider = get_llm_provider()
    if provider == "groq":
        return os.getenv("GROQ_API_KEY") or None
    return get_openai_api_key()


def get_llm_model() -> str:
    """Return the model name for the configured LLM provider."""
    provider = get_llm_provider()
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    return get_openai_model()


def get_llm_base_url() -> str | None:
    """Return an OpenAI-compatible base URL for non-OpenAI providers."""
    provider = get_llm_provider()
    if provider == "groq":
        return "https://api.groq.com/openai/v1"
    return None


def use_sample_data() -> bool:
    """Return whether local sample data should be used when no YouTube key exists."""
    value = os.getenv("USE_SAMPLE_DATA", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}
