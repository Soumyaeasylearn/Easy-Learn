"""
Shared configuration — reads from environment variables / .env
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""          # anon/service key

    # Hugging Face
    hf_token: str = ""

    # Whisper
    whisper_model: str = "tiny"

    # Kokoro
    kokoro_lang: str = "a"

    # App
    debug: bool = False
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
