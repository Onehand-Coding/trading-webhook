# TradingView to Binance Webhook

Automated trading webhook server that receives signals from TradingView and executes trades on Binance.

## 🚀 Quick Start

### 1. Setup Project

```bash
# Clone or create the project directory
mkdir trading-webhook
cd trading-webhook

# Create the project structure (copy the files from the artifacts)
# Make sure you have uv installed: https://github.com/astral-sh/uv
```

### 2. Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials
nano .env
```

**Required Environment Variables:**
```bash
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
WEBHOOK_SECRET=your_secure_webhook_password_here
FLASK_ENV=development
FLASK_DEBUG=True
LOG_LEVEL=INFO
```

### 3. Install Dependencies

```bash
# Install dependencies using uv
uv sync
```

### 4. Run the Server

```bash
# Option 1: Using the project script (recommended)
uv run run-webhook

# Option 2: Using Flask directly
uv run flask --app src/trading_webhook/webhook run --host=0.0.0.0 --port=5000

# Option 3: Using the main module
uv run python -m src.trading_webhook.main
```

## 🔧 Development

### Testing the Webhook

1. **Check Status:**
```bash
curl http://localhost:5000/status
```

2. **Test Webhook (without placing orders):**
```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your_webhook_secret",
    "ticker": "BTCUSDT",
    "action": "buy",
    "usdt_amount": 10
  }'
```

3. **Check Balances:**
```bash
curl http://localhost:5000/balances
```

### Available Endpoints

- `GET /` - Home/info endpoint
- `GET /status` - Health check and Binance connectivity
- `GET /balances` - Get account balances
- `POST /webhook` - Main webhook endpoint for TradingView
- `POST /test` - Test webhook without placing orders

## 📡 TradingView Alert Setup

### Alert Message Format

For buying with USDT amount:
```json
{
  "secret": "your_webhook_secret",
  "ticker": "BTCUSDT",
  "action": "buy",
  "usdt_amount": 50
}
```

For selling all holdings:
```json
{
  "secret": "your_webhook_secret",
  "ticker": "BTCUSDT",
  "action": "sell"
}
```

For selling percentage:
```json
{
  "secret": "your_webhook_secret",
  "ticker": "BTCUSDT",
  "action": "sell",
  "percentage": 50
}
```

### TradingView Alert Configuration

1. **Create Alert in TradingView:**
   - Right-click on your chart → "Add Alert"
   - Select your strategy as the condition
   - Go to "Notifications" tab
   - Enable "Webhook URL"
   - Enter your webhook URL: `http://your-server.com:5000/webhook`
   - Paste the JSON message in the "Message" field
   - Set frequency to "Once Per Bar Close"

2. **For Testing with ngrok:**
   ```bash
   # Install ngrok: https://ngrok.com/
   ngrok http 5000
   # Use the https URL provided by ngrok in TradingView
   ```

## 🏗️ Project Structure

```
trading-webhook/
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── .env.example               # Environment template
├── .env                       # Your actual environment variables
├── .gitignore                # Git ignore file
├── src/
│   └── trading_webhook/
│       ├── __init__.py       # Package init
│       ├── main.py           # Entry point for uv run
│       ├── webhook.py        # Main Flask application
│       ├── binance_client.py # Binance API client
│       └── config.py         # Configuration management
└── tests/
    ├── __init__.py
    └── test_webhook.py       # Tests (to be implemented)
```

## 🔒 Security Best Practices

1. **API Keys:**
   - Use Binance sub-account with limited permissions
   - Enable IP whitelist for your server
   - Never commit API keys to version control

2. **Webhook Security:**
   - Use strong, unique webhook secret
   - Monitor logs for unauthorized attempts
   - Use HTTPS in production

3. **Server Security:**
   - Keep dependencies updated
   - Use firewall rules
   - Monitor server resources

## 🚀 Production Deployment

### Using Gunicorn (Recommended)

```bash
# Add gunicorn to dependencies
uv add gunicorn

# Run with gunicorn
uv run gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 30 "trading_webhook.webhook:app"
```

### Environment Variables for Production

```bash
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
```

### Using Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 5000

# Run the application
CMD ["uv", "run", "run-webhook"]
```

## 🧪 Testing

### Manual Testing Commands

```bash
# Test buy order (test mode)
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your_webhook_secret",
    "ticker": "BTCUSDT",
    "action": "buy",
    "usdt_amount": 10
  }'

# Test sell order (test mode)
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your_webhook_secret",
    "ticker": "BTCUSDT",
    "action": "sell",
    "percentage": 25
  }'
```

### Running Tests

```bash
# Run tests (when implemented)
uv run pytest

# Run with coverage
uv run pytest --cov=src/trading_webhook
```

## 📊 Monitoring and Logging

- Logs are written to `trading_webhook.log`
- All webhook requests are logged with IP addresses
- Successful trades include full order details
- Errors are logged with stack traces

### Log Levels

- `INFO`: Normal operations, successful trades
- `WARNING`: Failed trades due to insufficient balance
- `ERROR`: API errors, configuration issues
- `DEBUG`: Detailed request/response data (development only)

## 🐛 Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Check your `.env` file exists and has all required variables
   - Ensure no trailing spaces in environment variable values

2. **"API request failed"**
   - Verify Binance API keys are correct
   - Check if IP whitelist is properly configured
   - Ensure sub-account has trading permissions

3. **"Insufficient balance"**
   - Check account balances with `/balances` endpoint
   - Verify you're using the correct sub-account

4. **"Unauthorized"**
   - Verify webhook secret matches between TradingView and `.env`
   - Check for typos in the JSON message

### Debug Mode

```bash
# Run in debug mode for detailed logging
LOG_LEVEL=DEBUG uv run run-webhook
```

## 📈 Advanced Configuration

### Position Sizing Options

The webhook supports multiple position sizing methods:

1. **Fixed USDT Amount:** `"usdt_amount": 50`
2. **Percentage of Balance:** `"percentage": 25`
3. **Fixed Quantity:** `"quantity": 0.001`
4. **All Available:** Leave quantity/amount empty

### Symbol Support

- Currently optimized for USDT pairs (BTCUSDT, ETHUSDT, etc.)
- Can be extended for other quote currencies
- Automatic lot size calculation based on Binance trading rules

## 🔄 Updates and Maintenance

```bash
# Update dependencies
uv lock --upgrade

# Check for security vulnerabilities (if available)
uv audit

# Format code
uv run ruff format src/
uv run ruff check src/
```

## 📞 Support

- Check logs in `trading_webhook.log` for detailed error information
- Use `/status` endpoint to verify Binance connectivity
- Test with `/test` endpoint before live trading
- Start with small amounts when going live

## ⚠️ Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk. Always test thoroughly with small amounts before deploying significant capital. The authors are not responsible for any financial losses.

For selling percentage:
```json
{
  "secret": "your_webhook_secret",
  "ticker": "BTCUSDT",
  "action": "sell",
  "percentage": 50
}
```

### TradingView Alert Configuration

1. **Create Alert in TradingView:**
   - Right-click on your chart → "Add Alert"
   - Select your strategy as the condition
   - Go to "Notifications" tab
   - Enable "Webhook URL"
   - Enter your webhook URL: `http://your-server.com:5000/webhook`
   - Paste the JSON message in the "Message" field
   - Set frequency to "Once Per Bar Close"

2. **For Testing with ngrok:**
   ```bash
   # Install ngrok: https://ngrok.com/
   ngrok http 5000
   # Use the https URL provided by ngrok in TradingView
   ```

## 🏗️ Project Structure

```
tradingview-binance-webhook/
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── .env.example               # Environment template
├── .env                       # Your actual environment variables
├── .gitignore                # Git ignore file
├── src/
│   └── tradingview_webhook/
│       ├── __init__.py       # Package init
│       ├── webhook.py        # Main Flask application
│       ├── binance_client.py # Binance API client
│       └── config.py         # Configuration management
└── tests/
    ├── __init__.py
    └── test_webhook.py       # Tests (to be implemented)
```

## 🔒 Security Best Practices

1. **API Keys:**
   - Use Binance sub-account with limited permissions
   - Enable IP whitelist for your server
   - Never commit API keys to version control

2. **Webhook Security:**
   - Use strong, unique webhook secret
   - Monitor logs for unauthorized attempts
   - Use HTTPS in production

3. **Server Security:**
   - Keep dependencies updated
   - Use firewall rules
   - Monitor server resources

## 🚀 Production Deployment

### Using Gunicorn (Recommended)

```bash
# Install gunicorn
uv add gunicorn

# Run with gunicorn
uv run gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 30 "src.tradingview_webhook.webhook:app"
```

### Environment Variables for Production

```bash
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
```

### Using Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 5000

# Run the application
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "30", "src.tradingview_webhook.webhook:app"]
```

## 🧪 Testing

### Manual Testing Commands

```bash
# Test buy order (test mode)
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your_webhook_secret",
    "ticker": "BTCUSDT",
    "action": "buy",
    "usdt_amount": 10
  }'

# Test sell order (test mode)
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your_webhook_secret",
    "ticker": "BTCUSDT",
    "action": "sell",
    "percentage": 25
  }'
```

### Running Tests

```bash
# Run tests (when implemented)
uv run pytest

# Run with coverage
uv run pytest --cov=src/tradingview_webhook
```

## 📊 Monitoring and Logging

- Logs are written to `trading_webhook.log`
- All webhook requests are logged with IP addresses
- Successful trades include full order details
- Errors are logged with stack traces

### Log Levels

- `INFO`: Normal operations, successful trades
- `WARNING`: Failed trades due to insufficient balance
- `ERROR`: API errors, configuration issues
- `DEBUG`: Detailed request/response data (development only)

## 🐛 Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Check your `.env` file exists and has all required variables
   - Ensure no trailing spaces in environment variable values

2. **"API request failed"**
   - Verify Binance API keys are correct
   - Check if IP whitelist is properly configured
   - Ensure sub-account has trading permissions

3. **"Insufficient balance"**
   - Check account balances with `/balances` endpoint
   - Verify you're using the correct sub-account

4. **"Unauthorized"**
   - Verify webhook secret matches between TradingView and `.env`
   - Check for typos in the JSON message

### Debug Mode

```bash
# Run in debug mode for detailed logging
LOG_LEVEL=DEBUG uv run flask --app src/tradingview_webhook/webhook run --debug
```

## 📈 Advanced Configuration

### Position Sizing Options

The webhook supports multiple position sizing methods:

1. **Fixed USDT Amount:** `"usdt_amount": 50`
2. **Percentage of Balance:** `"percentage": 25`
3. **Fixed Quantity:** `"quantity": 0.001`
4. **All Available:** Leave quantity/amount empty

### Symbol Support

- Currently optimized for USDT pairs (BTCUSDT, ETHUSDT, etc.)
- Can be extended for other quote currencies
- Automatic lot size calculation based on Binance trading rules

## 🔄 Updates and Maintenance

```bash
# Update dependencies
uv lock --upgrade

# Check for security vulnerabilities
uv audit

# Format code
uv run black src/
uv run ruff check src/
```

## 📞 Support

- Check logs in `trading_webhook.log` for detailed error information
- Use `/status` endpoint to verify Binance connectivity
- Test with `/test` endpoint before live trading
- Start with small amounts when going live

## ⚠️ Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk. Always test thoroughly with small amounts before deploying significant capital. The authors are not responsible for any financial losses.
