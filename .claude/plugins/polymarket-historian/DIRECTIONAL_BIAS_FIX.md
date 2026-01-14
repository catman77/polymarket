# Directional Bias Fix - Jan 14, 2026

## Problem Identified:
Trend filter blocked 319 DOWN bets but 0 UP bets during Jan 13-14 session.

**Root Cause:**
- Crypto had weak positive trend (scores 0.70-1.00)
- Trend filter blocked ALL DOWN trades
- Allowed ALL UP trades
- Result: 96.5% UP bias (275 UP, 10 DOWN)
- Markets were choppy within slight uptrend → UP trades lost to mean reversion

## Fix Implemented:
Added `STRONG_TREND_THRESHOLD = 1.0` to bot configuration

**Behavior:**
- Choppy markets (trend < 0.15): Skip entirely
- Weak trends (0.15 - 1.0): Allow BOTH directions (no bias)
- Strong trends (> 1.0): Apply directional filter

**Expected Result:**
- 40-60% directional balance (not 96-4%)
- Better performance in choppy/weak trend environments
- Maintains trend-following in strong trends

## Monitoring:
Watch for:
- Directional balance should be 40-60% over 50+ trades
- If still > 70% same direction → further tuning needed
- Win rate should improve from previous ~5% to 50-60%

## Date: 2026-01-14 14:00 UTC
