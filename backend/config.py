"""
Configuration management using pydantic-settings.
All settings are loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Predictive Maintenance Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # MongoDB
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string (Atlas or local)",
    )
    MONGODB_DATABASE: str = Field(
        default="fathom",
        description="MongoDB database name",
    )

    # JWT Authentication
    JWT_SECRET: str = Field(
        default="your-super-secret-jwt-key-change-in-production-min-32-chars",
        description="Secret key for signing JWT tokens (min 32 chars)",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10080,  # 7 days
        description="Access token expiration in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="Refresh token expiration in days",
    )

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,https://predictive-maintenance-agent-fronte.vercel.app",
        description="Allowed CORS origins (comma-separated)",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # External APIs
    GRADIO_API_URL: str = Field(
        default="https://vvsgyuv123-predictive-maintenance-demo.hf.space/gradio_api",
        description="Gradio API base URL for fallback predictions",
    )

    # First Admin Bootstrap
    BOOTSTRAP_ADMIN_EMAIL: Optional[str] = Field(
        default=None,
        description="Email for initial admin user (auto-created on first run)",
    )
    BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        description="Password for initial admin user",
    )

    # Rate Limiting (future use)
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()