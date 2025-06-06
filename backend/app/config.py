"""
Configuration settings for Pulseway Backend
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""

    # Pulseway API Configuration
    pulseway_token_id: str
    pulseway_token_secret: str
    pulseway_base_url: str = "https://api.pulseway.com/v3/"

    # Database Configuration
    database_url: str = "sqlite:///./data/pulseway.db"

    # Application Configuration
    log_level: str = "INFO"
    debug: bool = False

    # Sync Configuration
    sync_interval_minutes: int = 10
    min_request_interval: float = 0.1

    # API Configuration
    api_title: str = "Pulseway Backend API"
    api_description: str = "Robust backend for interfacing with Pulseway instances"
    api_version: str = "1.0.0-alpha.1"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
