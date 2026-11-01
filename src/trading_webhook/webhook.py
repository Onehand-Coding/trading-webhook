"""Flask webhook server for TradingView to Binance automation."""

import hmac
import logging
import math
import re
from datetime import datetime
from typing import Any, Dict, Tuple

from flask import Flask, jsonify, request

from .binance_client import BinanceClient
from .config import Config

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure file and console logging for the server."""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(Config.LOG_DIR / "trading_webhook.log"),
            logging.StreamHandler(),
        ],
        force=True,
    )


# Validate configuration
try:
    Config.validate()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Binance client
binance_client = BinanceClient()

TICKER_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


def _is_authorized(provided: object) -> bool:
    """Compare a provided secret with the configured webhook secret."""
    if not provided or not Config.WEBHOOK_SECRET:
        return False
    return hmac.compare_digest(str(provided), str(Config.WEBHOOK_SECRET))


def _positive_float(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return number


def _percentage(value: object) -> float:
    if value is None:
        return 100.0
    number = _positive_float(value, "percentage")
    if number > 100:
        raise ValueError("percentage must be between 1 and 100")
    return number


@app.route("/", methods=["GET"])
def home() -> Tuple[Dict[str, Any], int]:
    """Home endpoint."""
    return jsonify(
        {
            "status": "online",
            "service": "TradingView Binance Webhook",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


@app.route("/webhook", methods=["POST"])
def webhook() -> Tuple[Dict[str, Any], int]:
    """Handle TradingView webhook."""
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400
        if not isinstance(data, dict) or not data:
            logger.error("No data received in webhook request")
            return jsonify({"status": "error", "message": "No data received"}), 400

        if not _is_authorized(data.get("secret")):
            logger.warning("Unauthorized webhook attempt from %s", request.remote_addr)
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        ticker = str(data.get("ticker", "")).upper().strip()
        action = str(data.get("action", "")).lower().strip()
        if not ticker or not action:
            return (
                jsonify({"status": "error", "message": "Missing ticker or action"}),
                400,
            )
        if not TICKER_PATTERN.fullmatch(ticker):
            return (
                jsonify({"status": "error", "message": "Invalid ticker format"}),
                400,
            )
        if action not in ("buy", "sell"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Invalid action. Use 'buy' or 'sell'",
                    }
                ),
                400,
            )

        try:
            percentage = _percentage(data.get("percentage", 100))
            usdt_amount = data.get("usdt_amount")
            if usdt_amount is not None:
                usdt_amount = _positive_float(usdt_amount, "usdt_amount")
            quantity = data.get("quantity")
            if quantity not in (None, "all"):
                quantity = _positive_float(quantity, "quantity")
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        logger.info(
            "Authorized webhook: %s %s from %s", action, ticker, request.remote_addr
        )

        calculated_qty = 0.0
        if action == "buy":
            if usdt_amount is not None:
                calculated_qty = binance_client.calculate_buy_quantity(
                    ticker, usdt_amount
                )
            elif percentage < 100:
                usdt_balance = binance_client.get_balance("USDT")
                calculated_qty = binance_client.calculate_buy_quantity(
                    ticker, usdt_balance * (percentage / 100)
                )
            elif quantity is not None and quantity != "all":
                calculated_qty = quantity
            else:
                usdt_balance = binance_client.get_balance("USDT")
                calculated_qty = binance_client.calculate_buy_quantity(
                    ticker, usdt_balance
                )
            if calculated_qty <= 0:
                return (
                    jsonify(
                        {"status": "error", "message": "Insufficient USDT balance"}
                    ),
                    400,
                )
        else:
            if quantity is not None and quantity != "all":
                calculated_qty = quantity
            elif percentage < 100:
                asset_balance = binance_client.get_asset_balance(ticker)
                calculated_qty = asset_balance * (percentage / 100)
            else:
                calculated_qty = binance_client.get_asset_balance(ticker)
            if calculated_qty <= 0:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"No {ticker} balance to sell",
                        }
                    ),
                    400,
                )

        order_result = binance_client.place_market_order(ticker, action, calculated_qty)
        if not order_result:
            logger.error("Failed to place order on Binance")
            return (
                jsonify({"status": "error", "message": "Failed to place order"}),
                500,
            )

        response_data = {
            "status": "success",
            "action": action,
            "symbol": ticker,
            "quantity": calculated_qty,
            "order_id": order_result.get("orderId"),
            "client_order_id": order_result.get("clientOrderId"),
            "executed_qty": order_result.get("executedQty"),
            "cummulative_quote_qty": order_result.get("cummulativeQuoteQty"),
            "timestamp": datetime.now().isoformat(),
        }
        logger.info("Trade executed: %s %s", action, ticker)
        return jsonify(response_data), 200

    except Exception:
        logger.exception("Webhook processing error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/status", methods=["GET"])
def status() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint."""
    try:
        # Test Binance connection
        connectivity_ok = binance_client.test_connectivity()
        credentials_ok = binance_client.test_credentials()

        if connectivity_ok and credentials_ok:
            account_info = binance_client.get_account_info()

            return jsonify(
                {
                    "status": "online",
                    "binance_connectivity": connectivity_ok,
                    "binance_credentials": credentials_ok,
                    "account_type": account_info.get("accountType", "Unknown"),
                    "can_trade": account_info.get("canTrade", False),
                    "timestamp": datetime.now().isoformat(),
                }
            ), 200
        else:
            return jsonify(
                {
                    "status": "degraded",
                    "binance_connectivity": connectivity_ok,
                    "binance_credentials": credentials_ok,
                    "timestamp": datetime.now().isoformat(),
                }
            ), 500

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify(
            {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
        ), 500


@app.route("/balances", methods=["GET"])
def get_balances() -> Tuple[Dict[str, Any], int]:
    """Get account balances."""
    if not _is_authorized(request.headers.get("X-Webhook-Secret")):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    try:
        account_info = binance_client.get_account_info()
        balances = []

        for balance in account_info["balances"]:
            free = float(balance["free"])
            locked = float(balance["locked"])

            if free > 0 or locked > 0:  # Only show non-zero balances
                balances.append(
                    {
                        "asset": balance["asset"],
                        "free": free,
                        "locked": locked,
                        "total": free + locked,
                    }
                )

        # Sort by total balance (descending)
        balances.sort(key=lambda x: x["total"], reverse=True)

        return jsonify(
            {
                "status": "success",
                "balances": balances,
                "timestamp": datetime.now().isoformat(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/test", methods=["POST"])
def test_webhook() -> Tuple[Dict[str, Any], int]:
    """Test endpoint for webhook without placing actual orders."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    if not isinstance(data, dict) or not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    if not _is_authorized(data.get("secret")):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    ticker = str(data.get("ticker", "")).upper().strip()
    action = str(data.get("action", "")).lower().strip()
    if not ticker or not action:
        return jsonify({"status": "error", "message": "Missing ticker or action"}), 400
    if not TICKER_PATTERN.fullmatch(ticker):
        return jsonify({"status": "error", "message": "Invalid ticker format"}), 400
    if action not in ("buy", "sell"):
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    try:
        sanitized = {"ticker": ticker, "action": action}
        for key in ("usdt_amount", "quantity", "percentage"):
            if key in data:
                sanitized[key] = data[key]
        usdt_balance = binance_client.get_balance("USDT")
        asset_balance = (
            binance_client.get_asset_balance(ticker) if action == "sell" else 0
        )
        current_price = binance_client.get_current_price(ticker)
    except Exception:
        logger.exception("Test webhook error")
        return jsonify({"status": "error", "message": "Test failed"}), 500

    return (
        jsonify(
            {
                "status": "test_success",
                "message": "Webhook test successful - no orders placed",
                "data": sanitized,
                "current_price": current_price,
                "usdt_balance": usdt_balance,
                "asset_balance": asset_balance,
                "timestamp": datetime.now().isoformat(),
            }
        ),
        200,
    )


@app.errorhandler(404)
def not_found(error) -> Tuple[Dict[str, Any], int]:
    """Handle 404 errors."""
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error) -> Tuple[Dict[str, Any], int]:
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    configure_logging()
    logger.info("Starting TradingView Webhook Server...")
    logger.info(f"Flask Environment: {Config.FLASK_ENV}")
    logger.info(f"Debug Mode: {Config.FLASK_DEBUG}")

    app.run(host="0.0.0.0", port=5000, debug=Config.FLASK_DEBUG)
