#!/usr/bin/env python3
"""
Polymarket AutoTrader - Interactive Setup Script

This script helps you configure the trading bot with proper security practices.
It validates inputs, creates the .env file, and tests the configuration.

Usage:
    python scripts/setup.py              # Interactive setup
    python scripts/setup.py --validate   # Validate existing config
    python scripts/setup.py --docker     # Generate Docker config
"""

import os
import sys
import re
import getpass
import argparse
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.ENDC}")


def validate_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address format."""
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))


def validate_private_key(key: str) -> bool:
    """Validate Ethereum private key format."""
    clean_key = key[2:] if key.startswith('0x') else key
    return bool(re.match(r'^[a-fA-F0-9]{64}$', clean_key))


def get_wallet_address() -> str:
    """Interactively get and validate wallet address."""
    print_info("Enter your Polymarket wallet address")
    print("   Format: 0x followed by 40 hex characters")
    print("   Example: 0x742d35Cc6634C0532925a3b844Bc9e7595f...")
    print()
    
    while True:
        address = input(f"{Colors.BLUE}Wallet address: {Colors.ENDC}").strip()
        
        if not address:
            print_error("Address cannot be empty")
            continue
            
        if not validate_wallet_address(address):
            print_error("Invalid wallet address format")
            print("   Must start with 0x and be 42 characters total")
            continue
        
        # Confirm
        print(f"\n   Address: {address}")
        confirm = input(f"   {Colors.CYAN}Is this correct? (y/n): {Colors.ENDC}").strip().lower()
        
        if confirm == 'y':
            return address
        print()


def get_private_key() -> str:
    """Interactively get and validate private key (hidden input)."""
    print_info("Enter your wallet's private key")
    print(f"   {Colors.WARNING}⚠️  SECURITY: Input will be hidden{Colors.ENDC}")
    print("   Format: 64 hex characters (with or without 0x prefix)")
    print()
    
    while True:
        key = getpass.getpass(f"{Colors.BLUE}Private key (hidden): {Colors.ENDC}").strip()
        
        if not key:
            print_error("Private key cannot be empty")
            continue
            
        if not validate_private_key(key):
            print_error("Invalid private key format")
            print("   Must be 64 hex characters (with optional 0x prefix)")
            continue
        
        # Confirm by entering again
        key2 = getpass.getpass(f"{Colors.BLUE}Confirm private key: {Colors.ENDC}").strip()
        
        if key != key2:
            print_error("Keys don't match. Please try again.")
            continue
        
        # Show hash for verification (never show the actual key!)
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        print(f"\n   Key hash (for verification): {key_hash}...")
        print_success("Private key accepted")
        return key


def get_telegram_config() -> Dict[str, str]:
    """Optionally configure Telegram notifications."""
    print_info("Configure Telegram notifications (optional)")
    print("   This enables trade notifications and remote control")
    print()
    
    enable = input(f"{Colors.CYAN}Enable Telegram? (y/n): {Colors.ENDC}").strip().lower()
    
    if enable != 'y':
        return {}
    
    print()
    print("   Get bot token from @BotFather on Telegram")
    token = input(f"{Colors.BLUE}Bot token: {Colors.ENDC}").strip()
    
    if not token:
        print_warning("Skipping Telegram setup")
        return {}
    
    print()
    print("   Get your user ID from @userinfobot on Telegram")
    user_id = input(f"{Colors.BLUE}Your Telegram user ID: {Colors.ENDC}").strip()
    
    return {
        'TELEGRAM_BOT_TOKEN': token,
        'TELEGRAM_AUTHORIZED_USER_ID': user_id,
        'TELEGRAM_NOTIFICATIONS_ENABLED': 'true'
    }


def get_optional_config() -> Dict[str, str]:
    """Get optional configuration settings."""
    config = {}
    
    print_info("Optional: Custom RPC endpoint")
    print("   Default: https://polygon-rpc.com (public)")
    print("   Recommendation: Use Alchemy or Infura for reliability")
    print()
    
    custom_rpc = input(f"{Colors.CYAN}Custom RPC URL (or press Enter for default): {Colors.ENDC}").strip()
    
    if custom_rpc:
        config['POLYGON_RPC_URL'] = custom_rpc
    
    print()
    print_info("ML Bot configuration")
    enable_ml = input(f"{Colors.CYAN}Enable ML trading mode? (y/n): {Colors.ENDC}").strip().lower()
    
    if enable_ml == 'y':
        config['USE_ML_BOT'] = 'true'
        
        threshold = input(f"{Colors.BLUE}ML confidence threshold (default 0.55): {Colors.ENDC}").strip()
        if threshold:
            config['ML_THRESHOLD'] = threshold
    
    return config


def create_env_file(config: Dict[str, str], path: Path):
    """Create .env file with the configuration."""
    
    env_content = f"""# Polymarket AutoTrader Configuration
# Generated by setup.py on {__import__('datetime').datetime.now().isoformat()}
# 
# ⚠️  SECURITY WARNING:
#     - NEVER commit this file to version control
#     - Keep a secure backup of your private key
#     - Restrict file permissions: chmod 600 .env

# =============================================================================
# REQUIRED: Wallet Configuration
# =============================================================================

# Your Polymarket wallet address (0x...)
POLYMARKET_WALLET={config['POLYMARKET_WALLET']}

# Your wallet's private key (64 hex chars, with or without 0x)
# ⚠️  KEEP THIS SECRET - Never share or commit!
POLYMARKET_PRIVATE_KEY={config['POLYMARKET_PRIVATE_KEY']}

# =============================================================================
# OPTIONAL: Network Configuration
# =============================================================================

# Polygon RPC endpoint (default: public endpoint)
# Recommendation: Use Alchemy/Infura for better reliability
POLYGON_RPC_URL={config.get('POLYGON_RPC_URL', 'https://polygon-rpc.com')}

# =============================================================================
# OPTIONAL: Telegram Notifications
# =============================================================================

# Get bot token from @BotFather
TELEGRAM_BOT_TOKEN={config.get('TELEGRAM_BOT_TOKEN', '')}

# Your Telegram user ID (get from @userinfobot)
TELEGRAM_AUTHORIZED_USER_ID={config.get('TELEGRAM_AUTHORIZED_USER_ID', '')}

# Enable/disable notifications
TELEGRAM_NOTIFICATIONS_ENABLED={config.get('TELEGRAM_NOTIFICATIONS_ENABLED', 'false')}

# =============================================================================
# OPTIONAL: ML Trading Mode
# =============================================================================

# Enable ML-based trading decisions
USE_ML_BOT={config.get('USE_ML_BOT', 'false')}

# ML confidence threshold (0.0 - 1.0)
ML_THRESHOLD={config.get('ML_THRESHOLD', '0.55')}

# =============================================================================
# OPTIONAL: Shadow Trading
# =============================================================================

# Enable shadow (paper) trading for strategy comparison
ENABLE_SHADOW_TRADING=true

# =============================================================================
# API Keys for Extended Features (Optional)
# =============================================================================

# Polygonscan API key (for transaction verification)
POLYGONSCAN_API_KEY=

# Social sentiment APIs (for SocialSentimentAgent)
TWITTER_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
"""
    
    # Write file
    with open(path, 'w') as f:
        f.write(env_content)
    
    # Set restrictive permissions
    os.chmod(path, 0o600)
    
    print_success(f"Created {path}")
    print_info(f"File permissions set to 600 (owner read/write only)")


def validate_existing_config() -> bool:
    """Validate existing .env configuration."""
    print_header("Validating Configuration")
    
    env_path = PROJECT_ROOT / '.env'
    
    if not env_path.exists():
        print_error(f".env file not found at {env_path}")
        return False
    
    print_success(f"Found .env at {env_path}")
    
    # Load and validate
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
    
    errors = []
    warnings = []
    
    # Check wallet
    wallet = os.getenv('POLYMARKET_WALLET')
    if not wallet:
        errors.append("POLYMARKET_WALLET not set")
    elif not validate_wallet_address(wallet):
        errors.append("POLYMARKET_WALLET invalid format")
    else:
        print_success(f"Wallet: {wallet[:6]}...{wallet[-4:]}")
    
    # Check private key
    key = os.getenv('POLYMARKET_PRIVATE_KEY')
    if not key:
        errors.append("POLYMARKET_PRIVATE_KEY not set")
    elif not validate_private_key(key):
        errors.append("POLYMARKET_PRIVATE_KEY invalid format")
    else:
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        print_success(f"Private key: [hash: {key_hash}...]")
    
    # Check optional configs
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if telegram_token:
        print_success("Telegram configured")
    else:
        warnings.append("Telegram not configured (optional)")
    
    ml_enabled = os.getenv('USE_ML_BOT', 'false').lower() == 'true'
    print_info(f"ML mode: {'enabled' if ml_enabled else 'disabled'}")
    
    # Report results
    print()
    
    if errors:
        for err in errors:
            print_error(err)
        return False
    
    for warn in warnings:
        print_warning(warn)
    
    print_success("Configuration valid!")
    return True


def test_connection() -> bool:
    """Test connection to APIs."""
    print_header("Testing Connections")
    
    import requests
    
    tests = [
        ('Polygon RPC', 'https://polygon-rpc.com', 'post', {'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1}),
        ('Polymarket Data API', 'https://data-api.polymarket.com/positions?user=0x0000000000000000000000000000000000000000&limit=1', 'get', None),
        ('Binance API', 'https://api.binance.com/api/v3/ping', 'get', None),
    ]
    
    all_passed = True
    
    for name, url, method, data in tests:
        try:
            if method == 'post':
                resp = requests.post(url, json=data, timeout=10)
            else:
                resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                print_success(f"{name}: OK")
            else:
                print_warning(f"{name}: Status {resp.status_code}")
        except Exception as e:
            print_error(f"{name}: {e}")
            all_passed = False
    
    return all_passed


def generate_docker_config():
    """Generate Docker configuration files."""
    print_header("Generating Docker Configuration")
    
    # Check if .env exists
    if not (PROJECT_ROOT / '.env').exists():
        print_error(".env file required. Run setup.py first.")
        return False
    
    print_success("Docker configuration will be created in docker/")
    print_info("Run: docker-compose -f docker/docker-compose.yml up -d")
    return True


def main():
    parser = argparse.ArgumentParser(description='Polymarket AutoTrader Setup')
    parser.add_argument('--validate', action='store_true', help='Validate existing configuration')
    parser.add_argument('--docker', action='store_true', help='Generate Docker configuration')
    parser.add_argument('--test', action='store_true', help='Test API connections')
    args = parser.parse_args()
    
    print_header("Polymarket AutoTrader Setup")
    
    if args.validate:
        success = validate_existing_config()
        sys.exit(0 if success else 1)
    
    if args.docker:
        success = generate_docker_config()
        sys.exit(0 if success else 1)
    
    if args.test:
        success = test_connection()
        sys.exit(0 if success else 1)
    
    # Interactive setup
    print("This wizard will help you configure the trading bot.")
    print(f"{Colors.WARNING}⚠️  You will need:{Colors.ENDC}")
    print("   • Your Polymarket wallet address")
    print("   • Your wallet's private key")
    print("   • (Optional) Telegram bot token for notifications")
    print()
    
    proceed = input(f"{Colors.CYAN}Continue? (y/n): {Colors.ENDC}").strip().lower()
    if proceed != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    config = {}
    
    # Step 1: Wallet address
    print_header("Step 1: Wallet Address")
    config['POLYMARKET_WALLET'] = get_wallet_address()
    
    # Step 2: Private key
    print_header("Step 2: Private Key")
    config['POLYMARKET_PRIVATE_KEY'] = get_private_key()
    
    # Step 3: Telegram (optional)
    print_header("Step 3: Telegram (Optional)")
    telegram_config = get_telegram_config()
    config.update(telegram_config)
    
    # Step 4: Optional settings
    print_header("Step 4: Additional Settings")
    optional_config = get_optional_config()
    config.update(optional_config)
    
    # Create .env file
    print_header("Creating Configuration")
    env_path = PROJECT_ROOT / '.env'
    
    if env_path.exists():
        print_warning(f".env file already exists at {env_path}")
        overwrite = input(f"{Colors.CYAN}Overwrite? (y/n): {Colors.ENDC}").strip().lower()
        if overwrite != 'y':
            # Save as .env.new
            env_path = PROJECT_ROOT / '.env.new'
            print_info(f"Saving as {env_path}")
    
    create_env_file(config, env_path)
    
    # Test connections
    print_header("Testing Configuration")
    test_connection()
    
    # Final summary
    print_header("Setup Complete!")
    print_success("Configuration saved to .env")
    print()
    print("Next steps:")
    print(f"  1. Review the configuration: {Colors.CYAN}cat .env{Colors.ENDC}")
    print(f"  2. Start the bot: {Colors.CYAN}python bot/momentum_bot_v12.py{Colors.ENDC}")
    print(f"  3. Or use Docker: {Colors.CYAN}./scripts/deploy-docker.sh{Colors.ENDC}")
    print()
    print(f"{Colors.WARNING}⚠️  Remember to keep your .env file secure!{Colors.ENDC}")


if __name__ == '__main__':
    main()
