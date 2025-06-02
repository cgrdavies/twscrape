"""Configuration management for twscrape."""

import os
from pathlib import Path


def load_env_if_exists():
    """Load environment variables from .env file if it exists and we're in development."""
    try:
        from dotenv import load_dotenv

        # Try to load .env from current directory
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            return True

        # Try to load from project root
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            return True

    except ImportError:
        # python-dotenv not installed, continue without it
        pass

    return False


def is_development():
    """Detect if we're running in development mode."""
    return any(
        [
            os.getenv("ENVIRONMENT", "").lower() in ("development", "dev"),
            os.getenv("DEBUG", "").lower() in ("true", "1", "on"),
            os.getenv("TWSCRAPE_ENV", "").lower() == "development",
            Path(".env").exists(),
        ]
    )


def get_database_url():
    """Get database URL with fallback to default PostgreSQL."""
    return os.getenv(
        "TWSCRAPE_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape"
    )


def init_env():
    """Initialize environment - call this explicitly for CLI usage."""
    if is_development():
        env_loaded = load_env_if_exists()
        if env_loaded:
            print("📁 Loaded environment variables from .env file")
        return env_loaded
    return False
