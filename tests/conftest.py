import os

os.environ.setdefault("BINANCE_API_KEY", "test-api-key")
os.environ.setdefault("BINANCE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("FLASK_DEBUG", "False")
os.environ.setdefault("LOG_LEVEL", "ERROR")


from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_binance(monkeypatch):
    mock_client = MagicMock()
    mock_client.calculate_buy_quantity.return_value = 0.001
    mock_client.get_balance.return_value = 1000.0
    mock_client.get_asset_balance.return_value = 1.0
    mock_client.get_current_price.return_value = 50000.0
    mock_client.get_account_info.return_value = {
        "accountType": "SPOT",
        "canTrade": True,
        "balances": [{"asset": "BTC", "free": "1", "locked": "0"}],
    }
    mock_client.test_connectivity.return_value = True
    mock_client.test_credentials.return_value = True
    mock_client.place_market_order.return_value = {
        "orderId": 1,
        "clientOrderId": "test",
        "executedQty": "0.001",
        "cummulativeQuoteQty": "50",
    }
    monkeypatch.setattr("trading_webhook.webhook.binance_client", mock_client)
    return mock_client
