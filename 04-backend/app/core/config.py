from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, AnyHttpUrl
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "FinanceIntel Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://financeintel:secret_password@localhost:5432/financeintel"
    DATABASE_URL_MIGRATIONS: str = "postgresql+asyncpg://financeintel:secret_password@localhost:5432/financeintel"
    APP_USER_DATABASE_URL: Optional[str] = None
    ECHO_SQL: bool = False
    DB_POOLER_MODE: bool = False
    DB_SSLMODE: str = "require"
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    
    # Auth
    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI
    AI_PROVIDER: str
    AI_MODEL: str
    AI_API_KEY: str
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
