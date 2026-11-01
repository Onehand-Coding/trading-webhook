# Trading Webhook Hardening Implementation Plan

1. Add `tests/conftest.py` with dummy Binance and webhook secrets set before
   imports. Add a CI workflow and pytest/Ruff config.
2. Update `webhook.py`:
   - constant-time secret comparison helper
   - redacted logging
   - sanitized `/test` response
   - `X-Webhook-Secret` auth for `/balances`
   - ticker/action/numeric validation returning 400
   - safe JSON parsing
3. Add `tests/test_security_hardening.py`:
   - secret not logged
   - secret not in `/test` response
   - `/balances` 401/200
   - invalid `usdt_amount`, `quantity`, `percentage`
   - invalid ticker/action
4. Update existing balance tests to send the header.
5. Add `.github/workflows/ci.yml`.
6. Rewrite README security/usage/testing sections and add `CONTEXT.md`.
7. Run `ruff check`, `ruff format --check`, `pytest`, `pytest -W error`, and
   `uv build`.

No commit or push unless the user explicitly asks.
