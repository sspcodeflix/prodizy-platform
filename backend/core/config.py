"""
Configuration settings for the application.
Loads settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required settings
    # -----------------

    # OpenAI API key
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    LLAMA_API_ENDPOINT: str = os.getenv(
        "LLAMA_API_ENDPOINT", "http://localhost:11434/v1"
    )

    # MLflow tracking server URL
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")

    # FastAPI service port
    API_PORT: int = int(os.getenv("API_PORT", "5003"))

    # Backend API URL for frontend to connect to
    BACKEND_API_URL: str = os.getenv(
        "BACKEND_API_URL", f"http://127.0.0.1:{os.getenv('API_PORT', '5003')}/"
    )

    # Default LLM configuration
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")

    # Optional settings with defaults
    # ------------------------------
    MAX_REQUESTS_PER_SESSION: int = int(os.getenv("MAX_REQUESTS_PER_SESSION", "10"))
    INVITATION_EXPIRY_SECONDS: int = int(os.getenv("INVITATION_EXPIRY_SECONDS", "3600"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


# Create a global settings instance
settings = Settings()
