"""
Configuration management for TaxFix Multi-Agent System.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # LangSmith Tracing
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field(default="TaxFix-MultiAgent", env="LANGCHAIN_PROJECT")
    langchain_endpoint: Optional[str] = Field(default=None, env="LANGCHAIN_ENDPOINT")
    
    # LLM Configuration
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", env="GROQ_MODEL")
    google_model: str = Field(default="gemini-1.5-pro", env="GOOGLE_MODEL")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    max_tokens: int = Field(default=2048, env="MAX_TOKENS")
    
    # Database Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    
    # Security
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    jwt_secret: str = Field(default="your-jwt-secret-here", env="JWT_SECRET")
    
    # Memory Configuration
    short_term_memory_ttl: int = Field(default=3600, env="SHORT_TERM_MEMORY_TTL")  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def setup_langsmith_tracing():
    """Setup LangSmith tracing if configured."""
    if settings.langchain_api_key and settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        if settings.langchain_endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
