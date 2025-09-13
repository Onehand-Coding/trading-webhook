# Dockerfile for production trading webhook server
FROM python:3.11-slim

# Set labels
LABEL maintainer="onehand-coding"
LABEL description="TradingView to Binance Webhook Server"
LABEL version="0.1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies using uv (production only)
RUN uv sync --no-dev

# Create logs directory and set permissions
RUN mkdir -p logs && \
    touch trading_webhook.log && \
    chown -R 1000:1000 /app

# Create non-root user for security
RUN groupadd -g 1000 appgroup && \
    useradd --uid 1000 --gid 1000 -m -s /bin/bash appuser

# Switch to non-root user
USER 1000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/status || exit 1

# Set environment variables
ENV FLASK_ENV=production
ENV FLASK_DEBUG=False
ENV LOG_LEVEL=INFO

# Run the application
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "30", "--access-logfile", "logs/gunicorn_access.log", "--error-logfile", "logs/gunicorn_error.log", "--log-level", "info", "--capture-output", "trading_webhook.webhook:app"]