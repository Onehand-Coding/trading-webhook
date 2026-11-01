import logging

import pytest

from trading_webhook.config import Config
from trading_webhook.webhook import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def webhook_data():
    return {
        "secret": Config.WEBHOOK_SECRET,
        "ticker": "BTCUSDT",
        "action": "buy",
        "usdt_amount": 10,
    }


def test_balances_requires_secret(client):
    response = client.get("/balances")
    assert response.status_code == 401


def test_balances_with_secret(client, mock_binance):
    mock_binance.get_account_info.return_value = {
        "balances": [{"asset": "BTC", "free": "1", "locked": "0"}]
    }
    response = client.get(
        "/balances", headers={"X-Webhook-Secret": Config.WEBHOOK_SECRET}
    )
    assert response.status_code == 200
    assert response.json["balances"][0]["asset"] == "BTC"


def test_test_response_does_not_include_secret(client, webhook_data, mock_binance):
    response = client.post("/test", json=webhook_data)
    assert response.status_code == 200
    assert "secret" not in response.json["data"]
    assert webhook_data["secret"] not in response.get_data(as_text=True)


def test_webhook_secret_not_logged(client, webhook_data, mock_binance, caplog):
    caplog.set_level(logging.DEBUG)
    response = client.post("/webhook", json=webhook_data)
    assert response.status_code == 200
    assert webhook_data["secret"] not in caplog.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("usdt_amount", "not-a-number"),
        ("quantity", "not-a-number"),
        ("percentage", 0),
        ("percentage", 101),
        ("ticker", "bad!"),
        ("action", "hold"),
    ],
)
def test_invalid_inputs_return_400(client, webhook_data, mock_binance, field, value):
    payload = dict(webhook_data)
    payload[field] = value
    response = client.post("/webhook", json=payload)
    assert response.status_code == 400


def test_wrong_secret_returns_401(client, webhook_data, mock_binance):
    payload = dict(webhook_data)
    payload["secret"] = "wrong"
    response = client.post("/webhook", json=payload)
    assert response.status_code == 401


def test_malformed_json_returns_400(client):
    response = client.post("/webhook", data="{invalid", content_type="application/json")
    assert response.status_code == 400
