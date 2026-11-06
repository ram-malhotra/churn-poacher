"""
Application Configuration Module using Pydantic Settings.
Loads environment variables from .env with fallback defaults.
"""

from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "The Churn Poacher"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DEMO_MODE: bool = True

    # Security & Auth
    SECRET_KEY: str = "churn-poacher-secret-key-change-in-production-env-7a8b9c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ENABLE_AUTH: bool = False  # Set to True in production to enforce bearer token on API v1

    # Database & Connection Pooling
    DATABASE_URL: str = "sqlite+aiosqlite:///./churn_poacher.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # Redis & Background Workers
    REDIS_URL: str = "redis://localhost:6379/0"
    WORKER_CONCURRENCY: int = 4
    WORKER_POLL_INTERVAL: float = 1.0
    WORKER_LOCK_TIMEOUT: int = 300
    WORKER_HEARTBEAT_INTERVAL: int = 15

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # LLM Multi-Provider Settings
    LLM_PROVIDER: str = "auto"  # 'auto', 'gemini', 'openai', 'claude', 'fallback'
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Social & Status integrations
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "ChurnPoacherBot/1.0.0"

    HACKER_NEWS_API_BASE: str = "https://hn.algolia.com/api/v1"
    DATADOG_STATUS_PAGE_URL: str = "https://status.datadoghq.com/api/v2/summary.json"
    TWITTER_BEARER_TOKEN: Optional[str] = None
    G2_API_KEY: Optional[str] = None

    # Enrichment integrations
    CLEARBIT_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None

    # Crustdata Intelligence Integration
    CRUSTDATA_API_KEY: Optional[str] = None
    CRUSTDATA_API_BASE: str = "https://api.crustdata.com"
    CRUSTDATA_API_VERSION: str = "2025-11-01"
    CRUSTDATA_MIN_CREDIT_THRESHOLD: int = 5
    CRUSTDATA_CACHE_TTL_DAYS: int = 7
    CRUSTDATA_ENABLE_MOCK: bool = True  # Fallback when key is missing or for synthetic testing
    CRUSTDATA_INITIAL_BUDGET: float = 1200.0  # Application spending budget (credits)
    CRUSTDATA_NEAR_LIMIT_PERCENT: float = 80.0  # Threshold % for Near Limit status

    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parent.parent.parent / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
