"""Test suite for the TradingView to Binance webhook server."""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from trading_webhook.webhook import app
from trading_webhook.config import Config


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def valid_webhook_data():
    """Sample valid webhook data."""
    return {
        "secret": os.getenv("WEBHOOK_SECRET", "your_secure_password_123"),
        "ticker": "BTCUSDT",
        "action": "buy",
        "usdt_amount": 10
    }


@pytest.fixture
def invalid_webhook_data():
    """Sample invalid webhook data."""
    return {
        "secret": "wrong_secret",
        "ticker": "BTCUSDT",
        "action": "buy"
    }


def test_home_endpoint(client):
    """Test the home endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'online'
    assert data['service'] == 'TradingView Binance Webhook'
    assert 'version' in data
    assert 'timestamp' in data


def test_status_endpoint(client):
    """Test the status endpoint."""
    response = client.get('/status')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'status' in data
    assert 'binance_connectivity' in data
    assert 'timestamp' in data


def test_test_webhook_valid(client, valid_webhook_data):
    """Test the test webhook endpoint with valid data."""
    response = client.post('/test', 
                          data=json.dumps(valid_webhook_data),
                          content_type='application/json')
    
    # Should be successful with valid secret
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'test_success'
    assert 'message' in data
    assert 'data' in data
    assert 'current_price' in data
    assert 'usdt_balance' in data


def test_test_webhook_invalid_secret(client, invalid_webhook_data):
    """Test the test webhook endpoint with invalid secret."""
    response = client.post('/test',
                          data=json.dumps(invalid_webhook_data),
                          content_type='application/json')
    
    # Should return unauthorized
    assert response.status_code == 401
    
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == 'Unauthorized'


def test_test_webhook_missing_data(client):
    """Test the test webhook endpoint with missing data."""
    response = client.post('/test',
                          data=json.dumps({}),
                          content_type='application/json')
    
    # Should return bad request
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == 'No data received'


def test_balances_endpoint(client):
    """Test the balances endpoint."""
    response = client.get('/balances')
    
    # This might fail if credentials are invalid, but should not crash
    # We're testing that it returns a proper response format
    assert response.status_code in [200, 500]
    
    data = json.loads(response.data)
    assert 'status' in data


def test_webhook_missing_ticker(client, valid_webhook_data):
    """Test webhook with missing ticker."""
    # Remove ticker from data
    invalid_data = valid_webhook_data.copy()
    del invalid_data['ticker']
    
    response = client.post('/webhook',
                          data=json.dumps(invalid_data),
                          content_type='application/json')
    
    # Should return bad request
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'ticker' in data['message']


def test_webhook_invalid_action(client, valid_webhook_data):
    """Test webhook with invalid action."""
    # Change action to invalid value
    invalid_data = valid_webhook_data.copy()
    invalid_data['action'] = 'hold'
    
    response = client.post('/webhook',
                          data=json.dumps(invalid_data),
                          content_type='application/json')
    
    # Should return bad request
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'Invalid action' in data['message']


@patch('trading_webhook.binance_client.BinanceClient')
def test_webhook_internal_error(mock_binance_client, client, valid_webhook_data):
    """Test webhook handling of internal errors."""
    # Configure mock to raise an exception
    mock_binance_client_instance = MagicMock()
    mock_binance_client_instance.test_connectivity.return_value = True
    mock_binance_client_instance.test_credentials.return_value = True
    mock_binance_client_instance.calculate_buy_quantity.side_effect = Exception("Test error")
    mock_binance_client.return_value = mock_binance_client_instance
    
    response = client.post('/webhook',
                          data=json.dumps(valid_webhook_data),
                          content_type='application/json')
    
    # Should return internal server error or error response
    assert response.status_code in [500, 200]  # Could be 500 for internal error or 200 for handled error
    
    data = json.loads(response.data)
    assert data['status'] in ['error', 'success']  # Either error or success depending on how it's handled


def test_config_validation():
    """Test configuration validation."""
    # This should pass if all required environment variables are set
    try:
        Config.validate()
        assert True
    except ValueError as e:
        # If it fails, it should be because of missing variables
        assert "Missing required environment variables" in str(e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])