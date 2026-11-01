"""Configuration settings for the trading webhook."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def find_project_root(start_path: Path = None) -> Path:
    """Find project root by locating pyproject.toml file."""
    if start_path is None:
        start_path = Path(__file__).resolve()

    # If file path was passed, get its parent directory
    if start_path.is_file():
        start_path = start_path.parent

    # Traverse up the directory tree
    for parent in [start_path, *start_path.parents]:
        if (parent / "pyproject.toml").exists():
            return parent

    # If no pyproject.toml found
    raise FileNotFoundError("pyproject.toml not Found!")


class Config:
    """Configuration class for the trading webhook."""

    # Binance API Configuration
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
    BINANCE_BASE_URL = "https://api.binance.com"

    # Webhook Security
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

    # Flask Configuration
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = find_project_root() / "logs"
    LOG_DIR.mkdir(exist_ok=True, parents=True)

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        missing = []

        if not cls.BINANCE_API_KEY:
            missing.append("BINANCE_API_KEY")
        if not cls.BINANCE_SECRET_KEY:
            missing.append("BINANCE_SECRET_KEY")
        if not cls.WEBHOOK_SECRET:
            missing.append("WEBHOOK_SECRET")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return True
