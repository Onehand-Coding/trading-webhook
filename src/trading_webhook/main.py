"""Main entry point for the trading webhook server."""

import logging
import sys
from .config import Config
from .webhook import app

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the trading webhook server."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")

        logger.info("Starting TradingView Webhook Server...")
        logger.info(f"Flask Environment: {Config.FLASK_ENV}")
        logger.info(f"Debug Mode: {Config.FLASK_DEBUG}")

        # Run the Flask app
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=Config.FLASK_DEBUG
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
