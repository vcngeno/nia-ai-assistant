from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Nia"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://devuser:devpass@postgres:5432/nia_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    
    # OpenAI/AI Settings (set via environment variables)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1000
    
    # US-First Settings
    DEFAULT_TIMEZONE: str = "America/New_York"
    DEFAULT_LOCALE: str = "en-US"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env

settings = Settings()
