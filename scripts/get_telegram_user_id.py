#!/usr/bin/env python3
"""
Get Telegram User ID

This script fetches your Telegram user ID by reading recent updates from your bot.
Run this script, then send any message to your bot (@PolymarketAutoTraderBot).
"""

import requests
import sys

BOT_TOKEN = "8209081744:AAGuPN-UYuVXdkhBlgBJVVCGQe-Fd0MFOqI"

def get_user_id():
    """Fetch recent updates and extract user ID."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data.get('ok'):
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return None

        updates = data.get('result', [])

        if not updates:
            print("⚠️  No messages found yet.")
            print("\n📱 Please send any message to @PolymarketAutoTraderBot in Telegram")
            print("   Then run this script again.\n")
            return None

        # Get the most recent message
        latest_update = updates[-1]

        # Extract user info
        if 'message' in latest_update:
            user = latest_update['message']['from']
        elif 'edited_message' in latest_update:
            user = latest_update['edited_message']['from']
        else:
            print("❌ Could not find user info in updates")
            return None

        user_id = user['id']
        username = user.get('username', 'N/A')
        first_name = user.get('first_name', 'N/A')

        print("=" * 60)
        print("✅ TELEGRAM USER ID FOUND")
        print("=" * 60)
        print(f"User ID: {user_id}")
        print(f"Username: @{username}")
        print(f"First Name: {first_name}")
        print("=" * 60)
        print("\n📋 Add this to your .env file:\n")
        print(f"TELEGRAM_BOT_TOKEN={BOT_TOKEN}")
        print(f"TELEGRAM_AUTHORIZED_USER_ID={user_id}")
        print(f"TELEGRAM_NOTIFICATIONS_ENABLED=true")
        print("\n" + "=" * 60)

        return user_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

if __name__ == "__main__":
    print("🤖 Fetching Telegram user ID...\n")
    user_id = get_user_id()

    if user_id:
        sys.exit(0)
    else:
        sys.exit(1)
