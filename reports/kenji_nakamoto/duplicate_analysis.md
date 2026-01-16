# Duplicate Trade Analysis Report

**Generated:** 2026-01-16 10:40:04
**Analyst:** Dr. Kenji Nakamoto (Data Forensics Specialist)
**Purpose:** Detect API retries or logging bugs that inflate win rates artificially

---

## Executive Summary

- **Total Trades Analyzed:** 0
- **Exact Duplicates Found:** 0
- **Near-Duplicates Found:** 0 (within 5 seconds)
- **Total Duplicate Pairs:** 0
- **Duplicate Rate:** 0.00%

### Data Integrity Assessment

🟢 **EXCELLENT** - No duplicates detected. Data integrity is high.

---

## Findings

### Exact Duplicates

Exact duplicates share identical timestamp, crypto, direction, and entry price.
**Suspected Cause:** API retry logic, logging bug, or order placement retry.

✅ No exact duplicates found.

### Near-Duplicates

Near-duplicates occur within 5 seconds with same crypto and direction.  
**Suspected Cause:** Rapid re-entry, bot restart retry, or race condition.

✅ No near-duplicates found.

---

## Recommendations

1. ✅ **No action needed** - Duplicate detection shows clean data
2. 🔁 **Continue monitoring** - Run this check periodically

---

## Data Sources

- **Log File:** `bot.log`
- **CSV Export:** `reports/kenji_nakamoto/duplicate_analysis.csv`
- **Detection Method:** Hash-based (exact) + time-window (near)
- **Time Window:** 5 seconds (configurable)

---

## Technical Details

### Detection Algorithm

**Exact Duplicate Hash:**
```python
hash = MD5(timestamp + crypto + direction + entry_price)
```

**Near-Duplicate Logic:**
```python
if (same_crypto AND same_direction AND time_diff <= 5s):
    flag_as_near_duplicate()
```

