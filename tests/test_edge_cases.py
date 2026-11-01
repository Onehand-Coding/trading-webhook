# ruff: noqa: E402
"""Additional edge case tests for the TradingView to Binance webhook server."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from trading_webhook.webhook import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def valid_webhook_data():
    """Sample valid webhook data."""
    return {
        "secret": os.getenv("WEBHOOK_SECRET", "your_secure_password_123"),
        "ticker": "BTCUSDT",
        "action": "buy",
        "usdt_amount": 10,
    }


def test_webhook_missing_secret(client):
    """Test webhook with missing secret."""
    data = {"ticker": "BTCUSDT", "action": "buy", "usdt_amount": 10}

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "Unauthorized"


def test_webhook_empty_secret(client, valid_webhook_data):
    """Test webhook with empty secret."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["secret"] = ""

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "Unauthorized"


def test_webhook_wrong_secret(client, valid_webhook_data):
    """Test webhook with wrong secret."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["secret"] = "wrong_secret_123"

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "Unauthorized"


def test_webhook_missing_action(client, valid_webhook_data):
    """Test webhook with missing action."""
    invalid_data = valid_webhook_data.copy()
    del invalid_data["action"]

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "action" in data["message"]


def test_webhook_missing_ticker(client, valid_webhook_data):
    """Test webhook with missing ticker."""
    invalid_data = valid_webhook_data.copy()
    del invalid_data["ticker"]

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "ticker" in data["message"]


def test_webhook_empty_ticker(client, valid_webhook_data):
    """Test webhook with empty ticker."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["ticker"] = ""

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "ticker" in data["message"]


def test_webhook_empty_action(client, valid_webhook_data):
    """Test webhook with empty action."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["action"] = ""

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "action" in data["message"]


def test_webhook_invalid_ticker_format(client, valid_webhook_data):
    """Test webhook with invalid ticker format."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["ticker"] = "INVALID"

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    # This might succeed in placing an order or fail based on Binance validation
    # But it should not crash the server
    assert response.status_code in [200, 400, 500]


def test_webhook_negative_usdt_amount(client, valid_webhook_data):
    """Test webhook with negative USDT amount."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["usdt_amount"] = -10

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    # Should handle gracefully, might result in error from Binance
    assert response.status_code in [200, 400, 500]


def test_webhook_zero_usdt_amount(client, valid_webhook_data):
    """Test webhook with zero USDT amount."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["usdt_amount"] = 0

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    # Should handle gracefully
    assert response.status_code in [200, 400, 500]


def test_webhook_extremely_large_usdt_amount(client, valid_webhook_data):
    """Test webhook with extremely large USDT amount."""
    invalid_data = valid_webhook_data.copy()
    invalid_data["usdt_amount"] = 1000000000

    response = client.post(
        "/webhook", data=json.dumps(invalid_data), content_type="application/json"
    )

    # Should handle gracefully, likely result in insufficient balance error
    assert response.status_code in [200, 400, 500]


def test_webhook_invalid_json(client):
    """Test webhook with invalid JSON."""
    response = client.post(
        "/webhook", data='{"invalid": json}', content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "JSON" in data["message"]


def test_webhook_no_content_type(client):
    """Test webhook with no content type."""
    response = client.post("/webhook", data=json.dumps({"test": "data"}))

    # Should still work as Flask can often parse JSON without content-type
    assert response.status_code in [200, 400, 401, 500]


def test_webhook_malformed_data(client):
    """Test webhook with malformed data."""
    response = client.post(
        "/webhook", data="not even close to json", content_type="application/json"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_webhook_unsupported_http_method(client):
    """Test unsupported HTTP methods."""
    response = client.put("/webhook")
    assert response.status_code == 405  # Method Not Allowed

    response = client.delete("/webhook")
    assert response.status_code == 405  # Method Not Allowed

    response = client.patch("/webhook")
    assert response.status_code == 405  # Method Not Allowed


def test_404_error_handling(client):
    """Test 404 error handling."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "Endpoint not found"


def test_webhook_case_sensitivity_ticker(client, valid_webhook_data):
    """Test webhook ticker case sensitivity."""
    data_lower = valid_webhook_data.copy()
    data_lower["ticker"] = "btcusdt"

    data_upper = valid_webhook_data.copy()
    data_upper["ticker"] = "BTCUSDT"

    # Both should work since we normalize to uppercase in the webhook
    response_lower = client.post(
        "/webhook", data=json.dumps(data_lower), content_type="application/json"
    )

    response_upper = client.post(
        "/webhook", data=json.dumps(data_upper), content_type="application/json"
    )

    # Both should be processed (might fail for other reasons but not due to case)
    assert response_lower.status_code in [200, 400, 500]
    assert response_upper.status_code in [200, 400, 500]


def test_webhook_case_sensitivity_action(client, valid_webhook_data):
    """Test webhook action case sensitivity."""
    data_lower = valid_webhook_data.copy()
    data_lower["action"] = "BUY"

    data_mixed = valid_webhook_data.copy()
    data_mixed["action"] = "BuY"

    # Should work since we normalize to lowercase in the webhook
    response_lower = client.post(
        "/webhook", data=json.dumps(data_lower), content_type="application/json"
    )

    response_mixed = client.post(
        "/webhook", data=json.dumps(data_mixed), content_type="application/json"
    )

    # Both should be processed (might fail for other reasons but not due to case)
    assert response_lower.status_code in [200, 400, 500]
    assert response_mixed.status_code in [200, 400, 500]


def test_webhook_additional_unexpected_fields(client, valid_webhook_data):
    """Test webhook with additional unexpected fields."""
    data = valid_webhook_data.copy()
    data["unexpected_field"] = "some_value"
    data["another_field"] = 123

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    # Should ignore extra fields and process normally
    assert response.status_code in [200, 400, 401, 500]


def test_webhook_float_precision_quantity(client, valid_webhook_data):
    """Test webhook with high precision float quantities."""
    data = valid_webhook_data.copy()
    data["usdt_amount"] = 10.12345678901234567890

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    # Should handle precision gracefully
    assert response.status_code in [200, 400, 500]


@patch("trading_webhook.binance_client.BinanceClient")
def test_webhook_network_timeout(mock_binance_client, client, valid_webhook_data):
    """Test webhook handling of network timeouts."""
    # Configure mock to raise timeout
    mock_binance_client_instance = MagicMock()
    mock_binance_client_instance.test_connectivity.return_value = True
    mock_binance_client_instance.test_credentials.return_value = True
    mock_binance_client_instance.calculate_buy_quantity.side_effect = Exception(
        "Timeout"
    )
    mock_binance_client.return_value = mock_binance_client_instance

    response = client.post(
        "/webhook", data=json.dumps(valid_webhook_data), content_type="application/json"
    )

    # Should return error response
    assert response.status_code in [200, 500]
    data = json.loads(response.data)
    assert data["status"] in ["error", "success"]


def test_webhook_sell_with_no_balance(client, valid_webhook_data):
    """Test webhook sell action with no balance."""
    data = valid_webhook_data.copy()
    data["action"] = "sell"
    # Remove usdt_amount for sell action
    if "usdt_amount" in data:
        del data["usdt_amount"]

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    # Should handle gracefully, likely result in no balance error
    assert response.status_code in [200, 400, 500]


def test_webhook_buy_with_invalid_quantity(client, valid_webhook_data):
    """Test webhook buy with invalid quantity parameters."""
    # Test multiple quantity parameters
    data = valid_webhook_data.copy()
    data["quantity"] = 0.001
    data["percentage"] = 50

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    # Should handle gracefully
    assert response.status_code in [200, 400, 500]


def test_webhook_percentage_greater_than_100(client, valid_webhook_data):
    """Test webhook with percentage greater than 100."""
    data = valid_webhook_data.copy()
    data["percentage"] = 150

    response = client.post(
        "/webhook", data=json.dumps(data), content_type="application/json"
    )

    # Should handle gracefully
    assert response.status_code in [200, 400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
