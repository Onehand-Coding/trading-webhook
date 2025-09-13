"""Flask webhook server for TradingView to Binance automation."""

import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify

from .config import Config
from .binance_client import BinanceClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_DIR / "trading_webhook.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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


@app.route("/", methods=["GET"])
def home() -> Tuple[Dict[str, Any], int]:
    """Home endpoint."""
    return jsonify({
        "status": "online",
        "service": "TradingView Binance Webhook",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/webhook", methods=["POST"])
def webhook() -> Tuple[Dict[str, Any], int]:
    """Handle TradingView webhook."""
    try:
        # Log the incoming request
        logger.info(f"Webhook received from IP: {request.remote_addr}")

        # Parse JSON data
        try:
            data = request.get_json()
        except Exception as e:
            logger.error(f"Invalid JSON in webhook request: {e}")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        if not data:
            logger.error("No data received in webhook request")
            return jsonify({"status": "error", "message": "No data received"}), 400

        logger.info(f"Webhook data: {json.dumps(data, indent=2)}")

        # Security check
        webhook_secret = data.get("secret")
        if not webhook_secret or webhook_secret != Config.WEBHOOK_SECRET:
            logger.warning(f"Unauthorized webhook attempt from {request.remote_addr}")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        # Extract trading parameters
        ticker = data.get("ticker", "").upper()
        action = data.get("action", "").lower()
        quantity = data.get("quantity")
        usdt_amount = data.get("usdt_amount")  # Alternative to fixed quantity
        percentage = data.get("percentage", 100)  # Percentage of balance to use

        # Validation
        if not ticker or not action:
            logger.error("Missing ticker or action in webhook data")
            return jsonify({"status": "error", "message": "Missing ticker or action"}), 400

        if action not in ["buy", "sell"]:
            logger.error(f"Invalid action: {action}")
            return jsonify({"status": "error", "message": "Invalid action. Use 'buy' or 'sell'"}), 400

        # Calculate quantity based on different methods
        calculated_qty = 0.0

        if action == "buy":
            if usdt_amount:
                # Use specified USDT amount
                calculated_qty = binance_client.calculate_buy_quantity(ticker, float(usdt_amount))
            elif percentage < 100:
                # Use percentage of USDT balance
                usdt_balance = binance_client.get_balance("USDT")
                usdt_to_use = usdt_balance * (percentage / 100)
                calculated_qty = binance_client.calculate_buy_quantity(ticker, usdt_to_use)
            elif quantity:
                # Use fixed quantity
                calculated_qty = float(quantity)
            else:
                # Use all available USDT
                usdt_balance = binance_client.get_balance("USDT")
                calculated_qty = binance_client.calculate_buy_quantity(ticker, usdt_balance)

            if calculated_qty <= 0:
                logger.warning(f"Insufficient USDT balance for buying {ticker}")
                return jsonify({"status": "error", "message": "Insufficient USDT balance"}), 400

        elif action == "sell":
            if quantity and quantity != "all":
                # Use specified quantity
                calculated_qty = float(quantity)
            elif percentage < 100:
                # Use percentage of asset balance
                asset_balance = binance_client.get_asset_balance(ticker)
                calculated_qty = asset_balance * (percentage / 100)
            else:
                # Sell all available balance
                calculated_qty = binance_client.get_asset_balance(ticker)

            if calculated_qty <= 0:
                logger.warning(f"No {ticker} balance to sell")
                return jsonify({"status": "error", "message": f"No {ticker} balance to sell"}), 400

        # Place the order
        logger.info(f"Placing {action.upper()} order: {calculated_qty} {ticker}")

        order_result = binance_client.place_market_order(ticker, action, calculated_qty)

        if order_result:
            response_data = {
                "status": "success",
                "action": action,
                "symbol": ticker,
                "quantity": calculated_qty,
                "order_id": order_result.get("orderId"),
                "client_order_id": order_result.get("clientOrderId"),
                "executed_qty": order_result.get("executedQty"),
                "cummulative_quote_qty": order_result.get("cummulativeQuoteQty"),
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Trade executed successfully: {json.dumps(response_data, indent=2)}")
            return jsonify(response_data), 200
        else:
            logger.error("Failed to place order on Binance")
            return jsonify({"status": "error", "message": "Failed to place order"}), 500

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
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

            return jsonify({
                "status": "online",
                "binance_connectivity": connectivity_ok,
                "binance_credentials": credentials_ok,
                "account_type": account_info.get("accountType", "Unknown"),
                "can_trade": account_info.get("canTrade", False),
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "degraded",
                "binance_connectivity": connectivity_ok,
                "binance_credentials": credentials_ok,
                "timestamp": datetime.now().isoformat()
            }), 500

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500


@app.route("/balances", methods=["GET"])
def get_balances() -> Tuple[Dict[str, Any], int]:
    """Get account balances."""
    try:
        account_info = binance_client.get_account_info()
        balances = []

        for balance in account_info["balances"]:
            free = float(balance["free"])
            locked = float(balance["locked"])

            if free > 0 or locked > 0:  # Only show non-zero balances
                balances.append({
                    "asset": balance["asset"],
                    "free": free,
                    "locked": locked,
                    "total": free + locked
                })

        # Sort by total balance (descending)
        balances.sort(key=lambda x: x["total"], reverse=True)

        return jsonify({
            "status": "success",
            "balances": balances,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/test", methods=["POST"])
def test_webhook() -> Tuple[Dict[str, Any], int]:
    """Test endpoint for webhook without placing actual orders."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Security check
        webhook_secret = data.get("secret")
        if not webhook_secret or webhook_secret != Config.WEBHOOK_SECRET:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        ticker = data.get("ticker", "").upper()
        action = data.get("action", "").lower()

        if not ticker or not action:
            return jsonify({"status": "error", "message": "Missing ticker or action"}), 400

        if action not in ["buy", "sell"]:
            return jsonify({"status": "error", "message": "Invalid action"}), 400

        # Get current balances for testing
        usdt_balance = binance_client.get_balance("USDT")
        asset_balance = binance_client.get_asset_balance(ticker) if action == "sell" else 0
        current_price = binance_client.get_current_price(ticker)

        return jsonify({
            "status": "test_success",
            "message": "Webhook test successful - no orders placed",
            "data": data,
            "current_price": current_price,
            "usdt_balance": usdt_balance,
            "asset_balance": asset_balance,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Test webhook error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


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
    logger.info("Starting TradingView Webhook Server...")
    logger.info(f"Flask Environment: {Config.FLASK_ENV}")
    logger.info(f"Debug Mode: {Config.FLASK_DEBUG}")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.FLASK_DEBUG
    )
