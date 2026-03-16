from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "audio-to-diagram-backend"
    debug: bool = False

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str = Field(
        default="sqlite+aiosqlite:///./audio_to_diagram.db",
        alias="DATABASE_URL",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_stt_model: str = Field(default="gpt-4o-mini-transcribe", alias="OPENAI_STT_MODEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
