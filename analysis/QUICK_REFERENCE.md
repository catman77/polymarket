# Econophysics Analysis - Quick Reference Card

**One-page guide for immediate use**

---

## Run Everything (5 min)

```bash
cd /Volumes/TerraTitan/Development/polymarket-autotrader
python3 analysis/run_all_analyses.py && python3 analysis/visualize_results.py
```

---

## Key Metrics Cheat Sheet

| Metric | Good | Bad | Interpretation |
|--------|------|-----|----------------|
| **Entropy** | < 0.75 | > 0.85 | Lower = more predictable |
| **Edge** | > 10% | < 5% | Need >6% to beat fees |
| **p-value** | < 0.05 | > 0.10 | Lower = more significant |
| **Kelly** | 0.2-0.5 | < 0.1 | Position size guidance |
| **Sharpe** | > 0.8 | < 0.3 | Risk-adjusted return |
| **Hurst** | >0.5 = momentum | <0.5 = reversion | Strategy selector |
| **Sample** | > 20 | < 10 | Minimum for confidence |

---

## Quick Commands

```bash
# View best opportunities
cat analysis/results_best_opportunities.csv | column -t -s,

# Top Kelly hours
sort -t, -k9 -rn analysis/results_hourly_performance.csv | head -10

# Most predictable hours
sort -t, -k5 -n analysis/results_hourly_entropy.csv | head -10
```

---

## Position Sizing Formula

```python
kelly = 2 * win_rate - 1
position_size = balance * 0.05 * kelly * 0.5  # Half Kelly
```

---

## Key Files

1. **results_best_opportunities.csv** - Start here
2. **results_hourly_entropy.csv** - Predictable hours
3. **plots/hourly_entropy_heatmap.png** - Visual money map

---

## One-Line Summary

**Use entropy < 0.75, edge > 10%, p < 0.05 to filter trades. Size with Kelly. Profit.**
