from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Server settings
    APP_NAME: str = "Smart Management AI Agent System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Google Gemini AI settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # MCP Server settings
    MCP_SERVER_NAME: str = "SmartManagerMCP"
    MCP_TRANSPORT: str = "stdio"
    MCP_PORT: int = 8001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_supabase_configured(self) -> bool:
        """Check whether Supabase credentials have been configured with real values."""
        return bool(
            self.SUPABASE_URL
            and self.SUPABASE_KEY
            and "your-project-id" not in self.SUPABASE_URL
            and "your-supabase" not in self.SUPABASE_KEY
        )

    @property
    def is_gemini_configured(self) -> bool:
        """Check whether Gemini API key has been configured."""
        return bool(
            self.GEMINI_API_KEY
            and "your-gemini" not in self.GEMINI_API_KEY
        )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
