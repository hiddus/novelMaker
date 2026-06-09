from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NovelMaker API"
    app_version: str = "0.1.0"
    data_dir: Path = Path("data")
    use_mock_writer: bool = True
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_provider: str = "openai"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 60
    openai_max_retries: int = 2
    openai_retry_backoff_seconds: float = 1.5
    writer_max_prompt_chars: int = 12000
    context_total_budget_tokens: int = 12000
    context_output_reserve_tokens: int = 2500
    context_max_events: int = 8
    context_max_character_states: int = 6
    context_max_snapshots: int = 4
    context_max_patches: int = 3
    context_max_characters: int = 6
    context_max_memories: int = 8
    memory_trace_limit: int = 40
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NOVELMAKER_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
