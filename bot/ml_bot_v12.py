#!/usr/bin/env python3
"""
ML Bot v12 - Random Forest Live Trading

This is a WRAPPER around momentum_bot_v12.py that enables ML mode.
It sets the USE_ML_BOT environment variable before starting the bot.

WARNING: This uses ML predictions for ALL live trading decisions.
Only run this if ML has been validated in shadow testing.
"""

import os
import sys

# Enable ML mode
os.environ['USE_ML_BOT'] = 'true'
os.environ['ML_THRESHOLD'] = '0.55'  # 55% win probability threshold

print("="*80)
print("🤖 STARTING ML BOT (Random Forest Mode)")
print("="*80)
print()
print("⚠️  WARNING: This bot uses ML predictions for LIVE trading")
print("   All agent consensus logic is bypassed")
print("   ML Threshold: 55% win probability")
print()
print("="*80)
print()

# Import and run the main bot
# The bot will detect USE_ML_BOT env var and use ML predictions
exec(open('bot/momentum_bot_v12.py').read())
