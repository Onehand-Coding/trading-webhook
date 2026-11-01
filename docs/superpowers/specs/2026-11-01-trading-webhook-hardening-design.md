# Trading Webhook Security Hardening Design

Date: 2026-11-01
Status: Approved for implementation

## Context

The Flask webhook server accepts TradingView alerts and places Binance market
orders. It has two test files but no CI. Several security and validation issues
are present:

- Incoming webhook data is logged in full, including the webhook secret.
- The `/test` endpoint returns the full request data, including the secret.
- `/balances` is unauthenticated and returns account balances.
- Secrets are compared with `!=` rather than a constant-time comparison.
- Numeric fields (`usdt_amount`, `quantity`, `percentage`) are coerced without
  validation and can produce a 500.
- `Config.validate()` runs at import time, so tests and CI need environment
  variables before importing the app.

## Goals

1. Never log or return the webhook secret.
2. Require authentication for account balances.
3. Use constant-time secret comparison.
4. Validate ticker and numeric inputs with 400 responses.
5. Add deterministic tests that do not need real Binance credentials or network.
6. Add CI, README updates, and `CONTEXT.md`.

## Non-goals

- Replacing Flask or BinanceClient.
- Adding a database, users, or a hosted deployment.
- Removing `.env`; this server intentionally reads secrets from the environment.
- Real order placement in tests.

## Design

### Secrets

- Add `_is_authorized(provided)` using `hmac.compare_digest` and
  `Config.WEBHOOK_SECRET`.
- `/webhook` and `/test` keep the JSON `secret` field for TradingView
  compatibility.
- `/balances` requires `X-Webhook-Secret: <secret>`. Keep it out of query
  strings so it is not logged by proxies.
- Log only `ticker`, `action`, and sizing fields; never the secret or the full
  request body.
- `/test` returns sanitized sizing fields, not the raw data.

### Validation

- `ticker`: uppercase, matches `^[A-Z0-9]{5,20}$`.
- `action`: `buy` or `sell`.
- `usdt_amount`: positive finite number when present.
- `quantity`: positive finite number or the string `all` when present.
- `percentage`: number from 1 to 100 when present.
- Invalid values return 400 with a clear message; they never reach Binance.
- Use `request.get_json(silent=True)` and return 400 on malformed JSON.

### Config and tests

- Add `tests/conftest.py` that sets dummy `BINANCE_API_KEY`,
  `BINANCE_SECRET_KEY`, and `WEBHOOK_SECRET` before the app imports.
- Mock `BinanceClient` methods in tests; no network.
- Add `tests/test_security_hardening.py` for secret redaction, balance auth,
  constant-time comparison behavior, and input validation.
- Keep the existing tests green after updating them for the new balance auth.

### CI and docs

- Add `.github/workflows/ci.yml` with uv, ruff, pytest, and a wheel build.
- Update README: security notes, `/balances` header auth, input formats, test
  commands, and no secret logging.
- Add `CONTEXT.md`.

## Acceptance criteria

1. The webhook secret never appears in logs or `/test` responses.
2. `/balances` returns 401 without the header and 200 with it.
3. `hmac.compare_digest` is used for secret comparison.
4. Invalid numeric inputs return 400, not 500.
5. `pytest`, `ruff check`, and `ruff format --check` pass locally and in CI.
6. README and CONTEXT match the implementation.

## Risks

- Changing `/balances` auth is a breaking change. Document the header.
- Secret comparison timing tests are not practical; test behavior and code path.
- Tests must not import the app before conftest sets environment variables.
