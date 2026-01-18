#!/usr/bin/env python3
"""
Test balance detection from Polymarket proxy wallet.
Run this to verify balance is correctly detected before trading.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Constants
EOA = os.getenv('POLYMARKET_WALLET', '')
PROXY_WALLET = os.getenv('POLYMARKET_PROXY_WALLET', '')
RPC_URL = 'https://polygon-rpc.com'
USDC_ADDRESS = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'  # USDC.e bridged
NATIVE_USDC = '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'  # Native USDC


def get_balance_for_address(addr: str, token: str, token_name: str) -> float:
    """Get token balance for an address."""
    try:
        resp = requests.post(RPC_URL, json={
            'jsonrpc': '2.0',
            'method': 'eth_call',
            'params': [{
                'to': token,
                'data': f'0x70a08231000000000000000000000000{addr[2:].lower()}'
            }, 'latest'],
            'id': 1
        }, timeout=10)
        balance_hex = resp.json().get('result', '0x0')
        balance = int(balance_hex, 16) / 1e6
        return balance
    except Exception as e:
        print(f"  Error getting {token_name} for {addr[:10]}...: {e}")
        return 0.0


def get_proxy_from_api(eoa: str) -> str:
    """Try to get proxy wallet from Polymarket API."""
    try:
        # Try Gamma API
        resp = requests.get(
            f"https://gamma-api.polymarket.com/users/{eoa.lower()}",
            timeout=10
        )
        print(f"  Gamma API status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            proxy = data.get('proxyWallet') or data.get('proxy_wallet')
            if proxy:
                return proxy
        
        # Try CLOB API
        resp = requests.get(
            f"https://clob.polymarket.com/auth/proxy-wallet-address",
            params={"user": eoa},
            timeout=10
        )
        print(f"  CLOB API status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get('proxyWalletAddress', '')
            
    except Exception as e:
        print(f"  API error: {e}")
    
    return ''


def main():
    print("=" * 60)
    print("POLYMARKET BALANCE DETECTION TEST")
    print("=" * 60)
    
    # Step 1: Check environment variables
    print("\nSTEP 1: Environment Variables")
    print(f"  EOA (POLYMARKET_WALLET): {EOA or 'NOT SET'}")
    print(f"  PROXY_WALLET (POLYMARKET_PROXY_WALLET): {PROXY_WALLET or 'NOT SET'}")
    
    if not EOA:
        print("\nPOLYMARKET_WALLET not set in .env")
        return
    
    # Step 2: Try to get proxy wallet
    print("\nSTEP 2: Proxy Wallet Detection")
    
    proxy = PROXY_WALLET
    if not proxy:
        print("  POLYMARKET_PROXY_WALLET not set, trying API...")
        proxy = get_proxy_from_api(EOA)
    
    if proxy:
        print(f"  Proxy wallet: {proxy}")
    else:
        print("  Could not determine proxy wallet!")
        print("  Set POLYMARKET_PROXY_WALLET in .env to fix this")
    
    # Step 3: Check balances
    print("\nSTEP 3: Balance Check")
    
    total = 0.0
    
    # EOA balances
    print(f"\n  EOA Wallet ({EOA[:10]}...):")
    eoa_usdc_e = get_balance_for_address(EOA, USDC_ADDRESS, "USDC.e")
    print(f"    USDC.e: ${eoa_usdc_e:.2f}")
    total += eoa_usdc_e
    
    eoa_usdc = get_balance_for_address(EOA, NATIVE_USDC, "Native USDC")
    print(f"    Native USDC: ${eoa_usdc:.2f}")
    total += eoa_usdc
    
    # Proxy balances
    if proxy and proxy.lower() != EOA.lower():
        print(f"\n  Proxy Wallet ({proxy[:10]}...):")
        proxy_usdc_e = get_balance_for_address(proxy, USDC_ADDRESS, "USDC.e")
        print(f"    USDC.e: ${proxy_usdc_e:.2f}")
        total += proxy_usdc_e
        
        proxy_usdc = get_balance_for_address(proxy, NATIVE_USDC, "Native USDC")
        print(f"    Native USDC: ${proxy_usdc:.2f}")
        total += proxy_usdc
    
    # Summary
    print("\n" + "=" * 60)
    print(f"TOTAL BALANCE: ${total:.2f}")
    print("=" * 60)
    
    if total < 1.0:
        print("\nWARNING: Balance is very low!")
        print("   Trades require minimum $1.10")
    elif total > 0:
        print("\nBalance is sufficient for trading")
    else:
        print("\nERROR: No balance detected!")
        print("   Check if POLYMARKET_PROXY_WALLET is correct")


if __name__ == "__main__":
    main()
