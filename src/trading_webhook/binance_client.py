"""Binance API client for automated trading."""

import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Optional, Any

import requests

from .config import Config

logger = logging.getLogger(__name__)


class BinanceClient:
    """Binance API client for trading operations."""

    def __init__(self):
        self.api_key = Config.BINANCE_API_KEY
        self.secret_key = Config.BINANCE_SECRET_KEY
        self.base_url = Config.BINANCE_BASE_URL

        if not self.api_key or not self.secret_key:
            raise ValueError("Binance API credentials not configured")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for Binance API."""
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """Make authenticated request to Binance API."""
        if params is None:
            params = {}

        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._generate_signature(params)

        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, data=params, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        return self._make_request("/api/v3/account")

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol trading rules."""
        try:
            response = requests.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=10)
            response.raise_for_status()
            data = response.json()

            for symbol_info in data["symbols"]:
                if symbol_info["symbol"] == symbol:
                    return symbol_info
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")

        return None

    def get_balance(self, asset: str) -> float:
        """Get free balance for specific asset."""
        try:
            account_info = self.get_account_info()
            for balance in account_info["balances"]:
                if balance["asset"] == asset:
                    return float(balance["free"])
        except Exception as e:
            logger.error(f"Error getting balance for {asset}: {e}")

        return 0.0

    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v3/ticker/price?symbol={symbol}",
                timeout=10
            )
            response.raise_for_status()
            return float(response.json()["price"])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            raise

    def calculate_buy_quantity(self, symbol: str, usdt_amount: float) -> float:
        """Calculate buy quantity based on USDT amount."""
        try:
            price = self.get_current_price(symbol)
            quantity = usdt_amount / price

            # Apply symbol filters
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                for filter_info in symbol_info["filters"]:
                    if filter_info["filterType"] == "LOT_SIZE":
                        step_size = float(filter_info["stepSize"])
                        min_qty = float(filter_info["minQty"])

                        # Round to proper step size
                        quantity = round(quantity / step_size) * step_size
                        quantity = max(quantity, min_qty)
                        break

            return quantity
        except Exception as e:
            logger.error(f"Error calculating buy quantity: {e}")
            return 0.0

    def get_asset_balance(self, symbol: str) -> float:
        """Get balance of base asset from trading pair."""
        # Extract base asset from symbol (assuming USDT pairs)
        base_asset = symbol.replace("USDT", "").replace("BUSD", "")
        return self.get_balance(base_asset)

    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict[str, Any]]:
        """Place a market order."""
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": str(quantity)
        }

        try:
            result = self._make_request("/api/v3/order", params, method="POST")
            logger.info(f"Order placed successfully: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"Error placing {side} order for {symbol}: {e}")
            return None

    def test_connectivity(self) -> bool:
        """Test connection to Binance API."""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            response.raise_for_status()
            logger.info("Binance API connectivity test successful")
            return True
        except Exception as e:
            logger.error(f"Binance API connectivity test failed: {e}")
            return False

    def test_credentials(self) -> bool:
        """Test API credentials."""
        try:
            account_info = self.get_account_info()
            logger.info(f"API credentials valid - Account Type: {account_info.get('accountType')}")
            return True
        except Exception as e:
            logger.error(f"API credentials test failed: {e}")
            return False
