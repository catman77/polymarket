#!/usr/bin/env python3
"""
Security Utilities Module

Provides secure handling of secrets, log sanitization, and configuration validation.
Prevents accidental exposure of private keys, wallet addresses, and API tokens.

Usage:
    from utils.security import SecureConfig, sanitize_log, validate_wallet_address
    
    # Load configuration securely
    config = SecureConfig()
    wallet = config.get_wallet()
    
    # Sanitize logs before output
    safe_message = sanitize_log(f"Processing wallet {wallet}")
"""

import os
import re
import sys
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from functools import wraps

# Patterns to detect and redact sensitive data
SENSITIVE_PATTERNS = {
    'private_key': re.compile(r'(0x)?[a-fA-F0-9]{64}'),  # Ethereum private key
    'wallet_address': re.compile(r'0x[a-fA-F0-9]{40}'),   # Ethereum address
    'api_key': re.compile(r'[a-zA-Z0-9_-]{20,}'),        # Generic API key
    'bearer_token': re.compile(r'Bearer\s+[a-zA-Z0-9_.-]+'),  # Bearer tokens
}

# Environment variable names that contain secrets
SECRET_ENV_VARS = {
    'POLYMARKET_PRIVATE_KEY',
    'TELEGRAM_BOT_TOKEN',
    'POLYGONSCAN_API_KEY',
    'TWITTER_API_KEY',
    'REDDIT_CLIENT_SECRET',
}


class SecureConfigError(Exception):
    """Raised when secure configuration fails."""
    pass


class SecureConfig:
    """
    Secure configuration loader with validation and protection.
    
    Features:
    - Validates required secrets exist
    - Prevents logging of sensitive values
    - Validates wallet address format
    - Masks secrets in string representations
    """
    
    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize secure configuration.
        
        Args:
            env_path: Path to .env file. If None, searches standard locations.
        """
        self._secrets_loaded = False
        self._wallet = None
        self._private_key = None
        
        # Load environment
        self._load_env(env_path)
        
    def _load_env(self, env_path: Optional[str] = None):
        """Load environment variables from .env file."""
        from dotenv import load_dotenv
        
        # Search paths for .env file
        search_paths = []
        if env_path:
            search_paths.append(Path(env_path))
        
        # Add standard locations
        search_paths.extend([
            Path(__file__).parent.parent / '.env',  # Project root
            Path.cwd() / '.env',                    # Current directory
            Path.home() / '.polymarket' / '.env',   # User home
        ])
        
        for path in search_paths:
            if path.exists():
                load_dotenv(dotenv_path=path)
                self._secrets_loaded = True
                return
        
        # No .env found, rely on environment variables
        self._secrets_loaded = bool(os.getenv('POLYMARKET_WALLET'))
        
    def get_wallet(self) -> str:
        """
        Get wallet address securely.
        
        Returns:
            Validated wallet address
            
        Raises:
            SecureConfigError: If wallet not configured or invalid
        """
        if self._wallet:
            return self._wallet
            
        wallet = os.getenv('POLYMARKET_WALLET')
        
        if not wallet:
            raise SecureConfigError(
                "POLYMARKET_WALLET not configured. "
                "Set it in .env file or environment variable."
            )
        
        if not validate_wallet_address(wallet):
            raise SecureConfigError(
                f"Invalid wallet address format. "
                f"Expected 0x followed by 40 hex characters."
            )
            
        self._wallet = wallet
        return self._wallet
    
    def get_private_key(self) -> str:
        """
        Get private key securely.
        
        Returns:
            Private key (NEVER log this!)
            
        Raises:
            SecureConfigError: If private key not configured or invalid
        """
        if self._private_key:
            return self._private_key
            
        key = os.getenv('POLYMARKET_PRIVATE_KEY')
        
        if not key:
            raise SecureConfigError(
                "POLYMARKET_PRIVATE_KEY not configured. "
                "Set it in .env file or environment variable."
            )
        
        # Validate format (64 hex characters, optionally with 0x prefix)
        clean_key = key[2:] if key.startswith('0x') else key
        if not re.match(r'^[a-fA-F0-9]{64}$', clean_key):
            raise SecureConfigError(
                "Invalid private key format. "
                "Expected 64 hex characters (with optional 0x prefix)."
            )
            
        self._private_key = key
        return self._private_key
    
    def get_telegram_token(self) -> Optional[str]:
        """Get Telegram bot token if configured."""
        return os.getenv('TELEGRAM_BOT_TOKEN')
    
    def get_telegram_user_id(self) -> Optional[int]:
        """Get authorized Telegram user ID if configured."""
        user_id = os.getenv('TELEGRAM_AUTHORIZED_USER_ID')
        return int(user_id) if user_id else None
    
    def get_rpc_url(self) -> str:
        """Get Polygon RPC URL with fallback."""
        return os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary (safe to log).
        
        Returns:
            Dict with masked configuration values
        """
        wallet = os.getenv('POLYMARKET_WALLET', '')
        key = os.getenv('POLYMARKET_PRIVATE_KEY', '')
        
        return {
            'wallet_configured': bool(wallet),
            'wallet_masked': mask_address(wallet) if wallet else None,
            'private_key_configured': bool(key),
            'private_key_hash': hashlib.sha256(key.encode()).hexdigest()[:8] if key else None,
            'telegram_configured': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
            'rpc_url': self.get_rpc_url(),
        }
    
    def validate_all(self) -> bool:
        """
        Validate all required configuration.
        
        Returns:
            True if all required config is valid
            
        Raises:
            SecureConfigError: If any required config is missing/invalid
        """
        self.get_wallet()
        self.get_private_key()
        return True
    
    def __repr__(self) -> str:
        """Safe string representation (no secrets)."""
        return f"SecureConfig(wallet={mask_address(self._wallet or '')})"


def validate_wallet_address(address: str) -> bool:
    """
    Validate Ethereum wallet address format.
    
    Args:
        address: Address to validate
        
    Returns:
        True if valid format
    """
    if not address:
        return False
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))


def validate_private_key(key: str) -> bool:
    """
    Validate Ethereum private key format.
    
    Args:
        key: Private key to validate
        
    Returns:
        True if valid format
    """
    if not key:
        return False
    clean_key = key[2:] if key.startswith('0x') else key
    return bool(re.match(r'^[a-fA-F0-9]{64}$', clean_key))


def mask_address(address: str) -> str:
    """
    Mask wallet address for safe logging.
    
    Example: 0x52dF6Dc5DE31DD844d9E432A0821BC86924C2237 -> 0x52dF...2237
    """
    if not address or len(address) < 10:
        return '[INVALID_ADDRESS]'
    return f"{address[:6]}...{address[-4:]}"


def mask_private_key(key: str) -> str:
    """
    Mask private key for safe logging.
    
    Example: 0xabc123...xyz789 -> [PRIVATE_KEY:abc1...z789]
    """
    if not key or len(key) < 10:
        return '[PRIVATE_KEY:INVALID]'
    clean_key = key[2:] if key.startswith('0x') else key
    return f"[PRIVATE_KEY:{clean_key[:4]}...{clean_key[-4:]}]"


def sanitize_log(message: str) -> str:
    """
    Sanitize log message by redacting sensitive data.
    
    Args:
        message: Log message that may contain sensitive data
        
    Returns:
        Sanitized message safe for logging
    """
    result = message
    
    # Redact private keys (64 hex chars)
    result = re.sub(
        r'(0x)?[a-fA-F0-9]{64}',
        '[REDACTED_KEY]',
        result
    )
    
    # Mask wallet addresses (keep first/last 4 chars)
    def mask_match(match):
        addr = match.group(0)
        return f"{addr[:6]}...{addr[-4:]}"
    
    result = re.sub(
        r'0x[a-fA-F0-9]{40}',
        mask_match,
        result
    )
    
    # Redact bearer tokens
    result = re.sub(
        r'Bearer\s+[a-zA-Z0-9_.-]+',
        'Bearer [REDACTED]',
        result
    )
    
    # Redact API keys in common formats
    result = re.sub(
        r'(api[_-]?key|token|secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        r'\1=[REDACTED]',
        result,
        flags=re.IGNORECASE
    )
    
    return result


class SecureLogger(logging.Logger):
    """
    Logger that automatically sanitizes all log messages.
    
    Usage:
        log = SecureLogger(__name__)
        log.info(f"Processing {private_key}")  # Will be sanitized
    """
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        """Override to sanitize messages."""
        # Sanitize message
        if isinstance(msg, str):
            msg = sanitize_log(msg)
        
        # Sanitize args
        if args:
            args = tuple(
                sanitize_log(str(arg)) if isinstance(arg, str) else arg
                for arg in args
            )
        
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel + 1)


def get_secure_logger(name: str) -> logging.Logger:
    """
    Get a logger that automatically sanitizes sensitive data.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        SecureLogger instance
    """
    # Register our custom logger class
    old_class = logging.getLoggerClass()
    logging.setLoggerClass(SecureLogger)
    logger = logging.getLogger(name)
    logging.setLoggerClass(old_class)
    return logger


def secure_function(func):
    """
    Decorator to ensure function doesn't leak secrets in exceptions.
    
    Usage:
        @secure_function
        def process_transaction(private_key):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Sanitize exception message
            sanitized_msg = sanitize_log(str(e))
            raise type(e)(sanitized_msg) from None
    return wrapper


# Contract addresses (read-only, safe to expose)
POLYGON_CONTRACTS = {
    'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'CTF': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045',
}


def get_contract_address(name: str) -> str:
    """
    Get contract address by name.
    
    Args:
        name: Contract name (USDC, CTF)
        
    Returns:
        Contract address
        
    Raises:
        KeyError: If contract not found
    """
    return POLYGON_CONTRACTS[name.upper()]


# Module-level secure config instance
_config: Optional[SecureConfig] = None


def get_config() -> SecureConfig:
    """Get or create global secure config instance."""
    global _config
    if _config is None:
        _config = SecureConfig()
    return _config


if __name__ == '__main__':
    # Self-test
    print("Security module self-test")
    print("-" * 40)
    
    # Test sanitization
    test_messages = [
        "Private key: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "Wallet: 0x52dF6Dc5DE31DD844d9E432A0821BC86924C2237",
        "API key: api_key=sk_test_1234567890abcdefghij",
        "Bearer token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    ]
    
    for msg in test_messages:
        print(f"Original: {msg[:50]}...")
        print(f"Sanitized: {sanitize_log(msg)}")
        print()
    
    # Test config
    try:
        config = SecureConfig()
        print(f"Config summary: {config.get_config_summary()}")
    except SecureConfigError as e:
        print(f"Config not fully loaded (expected in test): {e}")
