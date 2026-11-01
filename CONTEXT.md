# Project Context

## Purpose

A Flask webhook server that receives TradingView alerts and places Binance market
orders. It is a local/self-hosted automation service, not a public SaaS.

## Architecture

- `src/trading_webhook/webhook.py` owns the Flask routes, authentication, and
  input validation.
- `src/trading_webhook/binance_client.py` owns signed Binance API requests and
  order placement.
- `src/trading_webhook/config.py` reads environment variables and validates
  required secrets.
- `tests/` uses Flask's test client and mocks the Binance client; no real orders
  or network calls are used in tests.

## Security

- `WEBHOOK_SECRET` is required for `/webhook` and `/test` via the JSON `secret`
  field.
- `/balances` requires `X-Webhook-Secret`.
- Secrets use `hmac.compare_digest`.
- Webhook bodies and secrets are not logged. Only ticker/action metadata is
  logged after authentication.
- Numeric fields are validated before Binance calls.
- `.env` is supported for local secrets and is git-ignored.

## Commands

```bash
uv sync --extra dev
uv run run-webhook
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI sets dummy Binance and webhook secrets and runs the same checks plus a wheel
build.

## Gotchas

- `config.py` calls `Config.validate()` at import time; tests set dummy env vars
  in `tests/conftest.py` before importing the app.
- `binance_client` is a module-level instance in `webhook.py`; tests patch that
  instance rather than the class.
- `/status` is intentionally public for health checks and does not return
  balances.
- Invalid JSON returns a distinct `"Invalid JSON"` message; empty JSON objects
  return `"No data received"`.

## Known Limitations

- No rate limiting or request replay protection beyond the shared secret.
- Binance filters are applied only to buy quantity calculation.
- Tests mock order placement; they do not verify live exchange behavior.
