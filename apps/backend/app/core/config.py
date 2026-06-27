# apps/backend/app/core/config.py
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

# Build the path to the .env file.
# This assumes the .env file is in the apps/backend/ directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    # Application Config
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Lumenly"
    VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Application secret key",
    )

    # Infrastructure URLs
    MONGODB_URL: str
    REDIS_URL: str
    QDRANT_URL: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None

    # LLM & Voice Providers
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Gemini model used for generateContent
    # Example: "gemini-2.5-flash", "gemini-3.5-flash"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_VERSION: str = "v1beta"

    ELEVENLABS_API_KEY: Optional[str] = None

    # Auth Config
    JWT_SECRET: str = Field(
        default="dev-jwt-secret-change-in-production",
        description="Secret used to sign JWT access tokens",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def ENVIRONMENT(self) -> str:
        return self.APP_ENV

    # RS256 Keys
    JWT_SECRET_RS256_PRIVATE: str
    JWT_SECRET_RS256_PUBLIC: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,  # <--- Use the explicit path here
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
