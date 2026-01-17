# Polymarket AutoTrader - Security & Deployment Guide

This document provides comprehensive instructions for secure deployment of the Polymarket AutoTrader.

## Table of Contents

1. [Security Best Practices](#security-best-practices)
2. [Configuration](#configuration)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Security Best Practices

### 🔐 Private Key Management

**CRITICAL:** Your private key controls your funds. Follow these rules:

1. **Never commit `.env` files to git** - `.env` is in `.gitignore` but verify before commits
2. **Use environment variables** - Don't hardcode keys in source code
3. **Limit key permissions** - The wallet should only have funds needed for trading
4. **Use a dedicated trading wallet** - Never use your main wallet
5. **Regular audits** - Check wallet transactions periodically

**For production environments, consider:**
- HashiCorp Vault for secrets management
- AWS Secrets Manager / GCP Secret Manager
- Hardware security modules (HSM) for large funds

### 🛡️ API Key Security

```bash
# Correct - keys from environment
export POLYMARKET_API_KEY="your-api-key"
export POLYMARKET_API_SECRET="your-api-secret"

# WRONG - hardcoded keys
# API_KEY = "ak-1234..."  # Never do this!
```

### 📝 Log Sanitization

The system automatically sanitizes logs to prevent key exposure:

```python
# Instead of logging raw data:
log.info(f"Using wallet: {wallet}")  # ❌ Exposes full address

# Use sanitized logging:
from utils.security import mask_address
log.info(f"Using wallet: {mask_address(wallet)}")  # ✅ Shows: 0x1234...5678
```

---

## Configuration

### Option 1: Interactive Setup (Recommended)

Run the configuration wizard:

```bash
cd /path/to/polymarket
python scripts/setup.py
```

The wizard will:
1. Prompt for all required credentials
2. Validate wallet address format
3. Validate private key format
4. Test API connectivity
5. Create a secure `.env` file

### Option 2: Manual Configuration

Create `.env` file from template:

```bash
cp .env.example .env
nano .env
```

Required environment variables:

```env
# === CORE CREDENTIALS (Required) ===
POLYMARKET_WALLET=0xYourWalletAddressHere
POLYMARKET_PRIVATE_KEY=your-private-key-without-0x-prefix
POLYMARKET_API_KEY=your-api-key
POLYMARKET_API_SECRET=your-api-secret
POLYMARKET_PASSPHRASE=your-passphrase

# === TELEGRAM NOTIFICATIONS (Optional) ===
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# === TRADING CONFIGURATION (Optional) ===
USE_ML_BOT=true
LIVE_TRADING=true
MIN_CONFLUENCE=0.60

# === API RATE LIMITS (Optional) ===
# Requests per second per API
BINANCE_RATE_LIMIT=10
POLYMARKET_RATE_LIMIT=10
```

### Validate Configuration

```bash
python scripts/setup.py --validate
```

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 1GB RAM minimum
- Linux/macOS (recommended) or Windows with WSL2

### Quick Start (One Command)

```bash
./scripts/deploy-docker.sh
```

This will:
1. Check Docker installation
2. Validate configuration
3. Build the Docker image
4. Start the trading bot

### Manual Docker Commands

```bash
# Build image
docker build -t polymarket-bot:latest -f docker/Dockerfile .

# Start services
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f bot

# Stop services
docker compose -f docker/docker-compose.yml down
```

### Docker Services

| Service | Description | Profile |
|---------|-------------|---------|
| `bot` | Main trading bot | default |
| `telegram` | Telegram notification bot | `--profile telegram` |
| `dashboard` | Web dashboard | `--profile dashboard` |

Start with Telegram:
```bash
docker compose -f docker/docker-compose.yml --profile telegram up -d
```

### Data Persistence

Docker volumes store persistent data:

| Volume | Contents |
|--------|----------|
| `bot-state` | Trading state (`trading_state.json`) |
| `bot-logs` | Log files |
| `bot-simulation` | Trade journal database |

Backup volumes:
```bash
./scripts/deploy-docker.sh --backup
```

---

## Manual Deployment (VPS)

### Server Requirements

- Ubuntu 22.04 LTS (recommended)
- 1GB RAM minimum
- 10GB disk space
- Python 3.11+

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/polymarket-autotrader.git
cd polymarket-autotrader

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
python scripts/setup.py

# Test
python scripts/setup.py --test
```

### Systemd Service

Create service file:

```bash
sudo nano /etc/systemd/system/polymarket-bot.service
```

```ini
[Unit]
Description=Polymarket AutoTrader Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/polymarket-autotrader
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/polymarket-autotrader/.env
ExecStart=/opt/polymarket-autotrader/venv/bin/python -m bot.momentum_bot_v12
Restart=always
RestartSec=30

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/polymarket-autotrader/state
ReadWritePaths=/opt/polymarket-autotrader/simulation
ReadWritePaths=/opt/polymarket-autotrader/logs

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
```

---

## Monitoring

### Health Checks

```bash
# Docker status
docker compose -f docker/docker-compose.yml ps

# Bot logs
docker compose -f docker/docker-compose.yml logs --tail=100 bot

# System status
python utils/quick_status.py
```

### Telegram Alerts

The bot sends notifications for:
- Trade executions
- Position updates
- Errors and warnings
- Daily performance summaries

Configure in `.env`:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234...
TELEGRAM_CHAT_ID=123456789
```

### Log Files

| File | Contents |
|------|----------|
| `logs/trading.log` | Main trading activity |
| `logs/errors.log` | Error-only log |
| `simulation/trade_journal.db` | SQLite trade database |

View logs:
```bash
# Recent activity
tail -f logs/trading.log

# Errors only
grep -i error logs/trading.log
```

---

## Troubleshooting

### Common Issues

#### "POLYMARKET_WALLET not set"

```bash
# Check .env exists
ls -la .env

# Validate configuration
python scripts/setup.py --validate

# Re-run setup
python scripts/setup.py
```

#### Rate Limiting (429 errors)

The bot includes automatic rate limiting. If you see 429 errors:

```python
# Check rate limits in .env
BINANCE_RATE_LIMIT=5  # Reduce from default 10
POLYMARKET_RATE_LIMIT=5
```

#### Docker Permission Errors

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker ps
```

#### Private Key Invalid

Ensure your private key:
- Does NOT have `0x` prefix
- Is exactly 64 hexadecimal characters
- Has no spaces or newlines

```bash
# Check key length
echo -n "your-key-here" | wc -c
# Should output: 64
```

### Recovery Procedures

#### Reset State

```bash
# Backup first
./scripts/deploy-docker.sh --backup

# Reset state file
rm state/trading_state.json
docker compose -f docker/docker-compose.yml restart bot
```

#### Rollback Deployment

```bash
# Git rollback
git log --oneline -5  # Find previous commit
git reset --hard HEAD~1

# Redeploy
./scripts/deploy-docker.sh --update
```

---

## Security Checklist

Before going live, verify:

- [ ] `.env` file has correct permissions (`chmod 600 .env`)
- [ ] `.env` is in `.gitignore`
- [ ] Private key is for dedicated trading wallet
- [ ] Trading wallet has limited funds
- [ ] Telegram notifications are working
- [ ] Rate limits are configured
- [ ] Logs do not contain sensitive data
- [ ] Docker is running as non-root user

---

## Support

- **Documentation:** See `docs/` folder
- **Issues:** GitHub Issues
- **Knowledge Base:** [AGENTS.md](AGENTS.md)

---

*Last Updated: January 2025*
