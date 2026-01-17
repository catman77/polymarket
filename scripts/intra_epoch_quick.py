#!/usr/bin/env python3
"""
Quick Intra-Epoch Analysis - 2 days of data, BTC only
Tests if minute-level patterns predict 15-minute outcomes
"""

import requests
import time
from collections import defaultdict

def get_epoch_minutes(epoch_start_ms: int) -> dict:
    """Fetch 15 one-minute candles for a 15-min epoch."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1m',
        'startTime': epoch_start_ms,
        'limit': 15
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None

        klines = resp.json()
        if len(klines) < 15:
            return None

        minutes = []
        for k in klines:
            open_p = float(k[1])
            close_p = float(k[4])
            minutes.append("Up" if close_p > open_p else "Down")

        epoch_open = float(klines[0][1])
        epoch_close = float(klines[-1][4])
        epoch_outcome = "Up" if epoch_close > epoch_open else "Down"

        return {'minutes': minutes, 'outcome': epoch_outcome}
    except:
        return None

def count_streak(outcomes: list) -> tuple:
    """Count consecutive same-direction from end."""
    if not outcomes:
        return ("None", 0)
    last = outcomes[-1]
    count = sum(1 for o in reversed(outcomes) if o == last)
    return (last, min(count, len(outcomes)))

print("\n" + "="*70)
print("  QUICK INTRA-EPOCH ANALYSIS (BTC, 2 days)")
print("="*70)

# Get last 2 days of epochs
import datetime
now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
current_epoch = now // 900 * 900

epochs = [current_epoch - (i+1) * 900 for i in range(192)]  # 2 days

print(f"\n  Fetching {len(epochs)} epochs...")

data = []
for i, ts in enumerate(epochs):
    if i % 20 == 0:
        print(f"    Progress: {i}/{len(epochs)}")
    result = get_epoch_minutes(ts * 1000)
    if result:
        data.append(result)
    time.sleep(0.1)

print(f"\n  Collected {len(data)} epochs with minute data")

# Analysis
print("\n" + "="*70)
print("  PATTERN ANALYSIS")
print("="*70)

# Pattern 1: First 3 minutes streak → mean reversion
print("\n  [1] First 3 minutes streak → Predict OPPOSITE (mean reversion)")
print("  " + "-"*60)

patterns_3min = defaultdict(lambda: {'mr_correct': 0, 'mom_correct': 0, 'total': 0})

for d in data:
    first_3 = d['minutes'][:3]
    streak_dir, streak_len = count_streak(first_3)
    outcome = d['outcome']

    if streak_len >= 2:
        key = f"{streak_len}_{streak_dir}"
        patterns_3min[key]['total'] += 1

        # Mean reversion: predict opposite
        if (streak_dir == "Up" and outcome == "Down") or (streak_dir == "Down" and outcome == "Up"):
            patterns_3min[key]['mr_correct'] += 1

        # Momentum: predict same
        if streak_dir == outcome:
            patterns_3min[key]['mom_correct'] += 1

for key in sorted(patterns_3min.keys()):
    p = patterns_3min[key]
    if p['total'] >= 10:
        mr_acc = p['mr_correct'] / p['total'] * 100
        mom_acc = p['mom_correct'] / p['total'] * 100
        streak_len, direction = key.split('_')
        print(f"\n    {streak_len} consecutive {direction}s in first 3 min (n={p['total']})")
        print(f"      Mean Reversion (predict opposite): {mr_acc:.1f}%")
        print(f"      Momentum (predict same):           {mom_acc:.1f}%")
        print(f"      Better strategy: {'MEAN REVERSION' if mr_acc > mom_acc else 'MOMENTUM'} (+{abs(mr_acc-mom_acc):.1f}%)")

# Pattern 2: First 5 minutes streak
print("\n\n  [2] First 5 minutes streak → Predict OPPOSITE (mean reversion)")
print("  " + "-"*60)

patterns_5min = defaultdict(lambda: {'mr_correct': 0, 'mom_correct': 0, 'total': 0})

for d in data:
    first_5 = d['minutes'][:5]
    streak_dir, streak_len = count_streak(first_5)
    outcome = d['outcome']

    if streak_len >= 3:
        key = f"{streak_len}_{streak_dir}"
        patterns_5min[key]['total'] += 1

        if (streak_dir == "Up" and outcome == "Down") or (streak_dir == "Down" and outcome == "Up"):
            patterns_5min[key]['mr_correct'] += 1
        if streak_dir == outcome:
            patterns_5min[key]['mom_correct'] += 1

for key in sorted(patterns_5min.keys()):
    p = patterns_5min[key]
    if p['total'] >= 5:
        mr_acc = p['mr_correct'] / p['total'] * 100
        mom_acc = p['mom_correct'] / p['total'] * 100
        streak_len, direction = key.split('_')
        print(f"\n    {streak_len} consecutive {direction}s in first 5 min (n={p['total']})")
        print(f"      Mean Reversion (predict opposite): {mr_acc:.1f}%")
        print(f"      Momentum (predict same):           {mom_acc:.1f}%")
        print(f"      Better strategy: {'MEAN REVERSION' if mr_acc > mom_acc else 'MOMENTUM'}")

# Pattern 3: All first 3 same direction
print("\n\n  [3] All first 3 minutes same direction")
print("  " + "-"*60)

all_3_up = {'mr': 0, 'mom': 0, 'total': 0}
all_3_down = {'mr': 0, 'mom': 0, 'total': 0}

for d in data:
    first_3 = d['minutes'][:3]
    outcome = d['outcome']

    if all(m == "Up" for m in first_3):
        all_3_up['total'] += 1
        if outcome == "Down": all_3_up['mr'] += 1
        if outcome == "Up": all_3_up['mom'] += 1
    elif all(m == "Down" for m in first_3):
        all_3_down['total'] += 1
        if outcome == "Up": all_3_down['mr'] += 1
        if outcome == "Down": all_3_down['mom'] += 1

if all_3_up['total'] >= 5:
    mr = all_3_up['mr'] / all_3_up['total'] * 100
    mom = all_3_up['mom'] / all_3_up['total'] * 100
    print(f"\n    All 3 first minutes UP (n={all_3_up['total']})")
    print(f"      Mean Reversion (predict DOWN): {mr:.1f}%")
    print(f"      Momentum (predict UP):         {mom:.1f}%")

if all_3_down['total'] >= 5:
    mr = all_3_down['mr'] / all_3_down['total'] * 100
    mom = all_3_down['mom'] / all_3_down['total'] * 100
    print(f"\n    All 3 first minutes DOWN (n={all_3_down['total']})")
    print(f"      Mean Reversion (predict UP):   {mr:.1f}%")
    print(f"      Momentum (predict DOWN):       {mom:.1f}%")

# Pattern 4: Net direction first 5 min
print("\n\n  [4] Net direction in first 5 minutes (4+ same direction)")
print("  " + "-"*60)

net_up = {'mr': 0, 'mom': 0, 'total': 0}
net_down = {'mr': 0, 'mom': 0, 'total': 0}

for d in data:
    first_5 = d['minutes'][:5]
    ups = sum(1 for m in first_5 if m == "Up")
    outcome = d['outcome']

    if ups >= 4:
        net_up['total'] += 1
        if outcome == "Down": net_up['mr'] += 1
        if outcome == "Up": net_up['mom'] += 1
    elif ups <= 1:
        net_down['total'] += 1
        if outcome == "Up": net_down['mr'] += 1
        if outcome == "Down": net_down['mom'] += 1

if net_up['total'] >= 5:
    mr = net_up['mr'] / net_up['total'] * 100
    mom = net_up['mom'] / net_up['total'] * 100
    print(f"\n    4+ of first 5 minutes UP (n={net_up['total']})")
    print(f"      Mean Reversion (predict DOWN): {mr:.1f}%")
    print(f"      Momentum (predict UP):         {mom:.1f}%")

if net_down['total'] >= 5:
    mr = net_down['mr'] / net_down['total'] * 100
    mom = net_down['mom'] / net_down['total'] * 100
    print(f"\n    4+ of first 5 minutes DOWN (n={net_down['total']})")
    print(f"      Mean Reversion (predict UP):   {mr:.1f}%")
    print(f"      Momentum (predict DOWN):       {mom:.1f}%")

print("\n" + "="*70)
print("  SUMMARY")
print("="*70)
print("\n  Question: Can minute-level patterns within an epoch predict outcome?")
print("\n  Answer: Compare mean reversion vs momentum accuracy above.")
print("          If mean reversion > 55%, it's actionable for intra-epoch trading.")
print("="*70 + "\n")
