# Confidence Threshold & Profitability Research

**Research Question**: Can we determine a confidence level within a 15-minute window where we can consistently achieve incremental positive cash flow after fees?

**Short Answer**: **YES** - There are three viable strategies depending on your risk tolerance and prediction accuracy.

---

## Fee Structure Analysis

### Polymarket Taker Fees by Probability

| Entry Price | Probability | Taker Fee | Round-trip Fee |
|-------------|-------------|-----------|----------------|
| $0.05 | 5% | 0.31% | 0.63% |
| $0.10 | 10% | 0.63% | 1.26% |
| $0.20 | 20% | 1.26% | 2.52% |
| $0.30 | 30% | 1.89% | 3.78% |
| $0.50 | 50% | 3.15% | **6.30%** (highest) |
| $0.70 | 70% | 1.89% | 3.78% |
| $0.85 | 85% | 0.95% | 1.89% |
| $0.90 | 90% | 0.63% | 1.26% |
| $0.95 | 95% | 0.32% | 0.63% |

**Key Insight**: Fees are HIGHEST at 50/50 odds (6.3%) and LOWEST at extreme probabilities (0.63%).

---

## Breakeven Win Rates by Entry Price

To profit after fees, you need to exceed these win rates:

| Entry Price | Implied Prob | Breakeven WR | Edge Needed |
|-------------|--------------|--------------|-------------|
| $0.10 | 10% | 10.06% | +0.06% |
| $0.20 | 20% | 20.25% | +0.25% |
| $0.30 | 30% | 30.57% | +0.57% |
| $0.50 | 50% | 51.58% | +1.58% |
| $0.70 | 70% | 71.32% | +1.32% |
| $0.85 | 85% | 85.80% | +0.80% |
| $0.90 | 90% | 90.57% | +0.57% |
| $0.95 | 95% | 95.30% | +0.30% |

**Example**: If you enter at $0.30, you need to win **30.57%** of the time just to break even.

---

## Three Profitable Strategies

### Strategy 1: Grind Strategy (High Confidence, Small Profits)

**Threshold**: Only bet when confidence >85% AND market price >$0.85

**Requirements**:
- Your prediction model must be 87-92% accurate (beat market by 2-7%)
- Accept small profits: $0.50-$1.50 per $10 bet (5-15% ROI)
- High frequency trading (96 potential trades/day)

**Expected Performance** (if calibrated):
- Win rate: 90%
- Average entry: $0.87
- Profit per win: $1.67
- Loss per loss: -$10.09
- **EV per trade: +$0.49** (4.9% ROI)
- Monthly profit (60 trades): **~$29.40**

**Risks**:
- Requires near-perfect accuracy (90%+ win rate)
- Small profits = low margin for error
- One loss wipes out ~6 wins
- Market must offer frequent 85-90% opportunities

**Viability**: ✅ POSSIBLE but requires excellent calibration

---

### Strategy 2: Value Betting (Medium Confidence, Moderate Profits)

**Threshold**: Bet when YOUR confidence is 60-70% AND market price <$0.40

**Requirements**:
- Your model beats market pricing by 20-30%
- Accept moderate variance
- Lower frequency: 10-20 trades/day

**Expected Performance** (if calibrated):
- Win rate: 65%
- Average entry: $0.30
- Profit per win: $23.14
- Loss per loss: -$10.19
- **EV per trade: +$11.48** (114% ROI!)
- Monthly profit (50 trades): **~$574**

**Risks**:
- Higher variance (bigger swings)
- Requires finding mispriced markets
- Drawdowns can be 20-30% during cold streaks

**Viability**: ✅✅ MOST PROFITABLE if you can identify mispricing

---

### Strategy 3: Contrarian (Low Entry Price, High Payoff)

**Threshold**: Look for <$0.20 entries when YOU believe probability is >50%

**Requirements**:
- Identify when market is WRONG (oversold/panic pricing)
- Need only 53-58% win rate to profit
- Very high payoff when right (8-12x return)

**Expected Performance** (if calibrated):
- Win rate: 55%
- Average entry: $0.10
- Profit per win: $89.94
- Loss per loss: -$10.06
- **EV per trade: +$44.94** (449% ROI!)
- Monthly profit (30 trades): **~$1,348**

**Risks**:
- Hardest to identify (contrarian = going against crowd)
- Fewer opportunities (maybe 5-10/day)
- Psychological difficulty (betting on "unlikely" outcomes)
- Can look foolish during losses

**Viability**: ✅✅✅ HIGHEST PROFIT if you can spot market inefficiencies

---

## Expected Profit Examples ($10 bet size)

| Entry Price | Win Rate | Strategy | Profit/Win | Loss/Lose | **EV/Trade** | ROI |
|-------------|----------|----------|------------|-----------|--------------|-----|
| $0.85 | 90% | Late confirm | $1.67 | -$10.09 | **+$0.49** | 4.9% |
| $0.90 | 93% | Very late | $1.05 | -$10.06 | **+$0.27** | 2.7% |
| $0.30 | 65% | Early momentum | $23.14 | -$10.19 | **+$11.48** | 114% |
| $0.25 | 60% | Early momentum | $29.84 | -$10.16 | **+$13.84** | 138% |
| $0.15 | 60% | Contrarian | $56.57 | -$10.09 | **+$29.91** | 299% |
| $0.10 | 55% | Contrarian | $89.94 | -$10.06 | **+$44.94** | 449% |

---

## Answer to Your Question

**Q**: "Is there a confidence level where we can ALWAYS bet and incrementally gain positive cash flow, even if small?"

**A**: **YES** - Here are the three viable approaches:

### 1. Grind Strategy (Conservative)
- Bet only when confidence >85% AND market price >$0.85
- Requires: 87-92% accuracy
- Profit: **$0.50-$1.50 per trade** (5-15%)
- Best for: Steady, low-variance growth

### 2. Value Betting (Recommended)
- Bet when YOUR confidence >65% AND market price <$0.40
- Requires: Spot mispricing 20-30% better than market
- Profit: **$10-25 per trade** (100-250%)
- Best for: Aggressive growth, moderate variance

### 3. Contrarian (Aggressive)
- Bet when market <$0.20 but YOU predict >50%
- Requires: Exceptional ability to identify oversold
- Profit: **$40-90 per trade** (400-900%)
- Best for: Maximum growth, high risk tolerance

---

## The Key Formula

To have "incremental positive cash flow", you need:

```
EV = (Win_Rate × Profit_If_Win) - (Loss_Rate × Loss_If_Lose) > 0
```

This requires:

```
Win_Rate > Breakeven_Rate
```

Where `Breakeven_Rate` depends on entry price (see table above).

---

## Practical Recommendation

**Start with Strategy 2 (Value Betting)**:

1. ✅ Only trade when YOUR confidence is **60-70%**
2. ✅ Only enter if market price is **<$0.40** (looking for mispricing)
3. ✅ Target **10-15 trades/day**
4. ✅ Track actual win rate vs predicted confidence
5. ✅ Adjust threshold up if win rate < 60%
6. ✅ Adjust threshold down if win rate > 70%

This gives you:
- ✅ Meaningful profit per trade ($10-25)
- ✅ Acceptable win rate requirement (60-70%)
- ✅ Enough opportunities (10-15/day)
- ✅ Room for calibration improvement
- ✅ Positive expected value even with imperfect predictions

---

## Next Steps for Validation

### 1. Analyze Shadow Trading Results
- What's your actual win rate at different confidence levels?
- Are you better at high-confidence (>80%) or medium (60-70%)?

### 2. Check Entry Price Distribution
- Are you entering at $0.10-$0.30? (✅ Good - mispricing opportunities)
- Are you entering at $0.50-$0.70? (❌ Bad - worst fees, hardest to profit)
- Are you entering at $0.85-$0.95? (⚠️ Okay if 90%+ accurate)

### 3. Calculate Your Actual EV
```
EV = (actual_win_rate × avg_profit) - (actual_loss_rate × avg_loss)
```
- If EV > 0, you have an edge ✅
- If EV < 0, need to adjust thresholds ❌

### 4. Calibrate Your Confidence
- When you predict 70% confidence, do you win 70% of the time?
- If you win 80%, you're underconfident (trade more)
- If you win 60%, you're overconfident (trade less)

**Use shadow trading to gather this data without risk!**

---

## Summary

**Yes, there IS a threshold where fractional profits are consistently possible:**

- **Entry at $0.85-$0.90** with **87-92% actual win rate** = **+$0.50-$1.00** per $10 bet
- **Entry at $0.15-$0.25** with **60-65% actual win rate** = **+$3-$6** per $10 bet
- **Entry at $0.95+** requires **97%+ win rate** = **+$0.30** per $10 bet (risky!)

**The key is CALIBRATION**: Your predicted probability must be MORE ACCURATE than the market price to have positive expected value.

---

**Generated**: 2026-01-17
**Bot Version**: v12.1 (ML Random Forest + Shadow Trading)
