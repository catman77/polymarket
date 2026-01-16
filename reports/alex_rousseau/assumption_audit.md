# Assumption Archaeology: Questioning the Architecture

**Analyst:** Alex 'Occam' Rousseau (First Principles Engineer)
**Generated:** 2026-01-16
**Philosophy:** *Every assumption should be interrogated. What looks like architecture might just be accumulated folklore.*

---

## Introduction

This audit challenges every major architectural decision in the Polymarket AutoTrader system. For each assumption, we ask:

1. **What problem does this solve?**
2. **What's the empirical evidence it works?**
3. **What would break if we removed it?**
4. **What's the simplest alternative?**

**Goal:** Separate essential complexity (necessary for the problem) from accidental complexity (artifact of implementation choices).

---

## Architectural Decisions Analyzed

### 1. Multi-Agent Consensus Voting

**Assumption:** "More agents = better decisions. Wisdom of crowds."

**Who decided this?** Unknown. Appears to be modeled after ensemble methods in ML.

**What problem does it solve?**
- Supposedly reduces individual agent bias
- Diversifies signal sources
- Prevents single-point-of-failure

**What's the empirical evidence it works?**
- ❌ **No evidence.** Component audit shows most agents have 0% WR contribution
- ❌ **Correlation matrix** (US-RC-027) will reveal if agents are independent or herding
- ❌ **No A/B test** comparing single-agent vs multi-agent

**What would break if we removed it?**
- Nothing. System could run with 1-3 agents instead of 11
- Vic's per-agent analysis (US-RC-020) will identify which 1-2 agents actually help

**Simplest alternative:**
- **Single best agent** (from performance ranking) + entry price filter
- OR: **2-agent system** (best performing + risk veto)

**Verdict:** 🔴 **Weak assumption. Test for removal.**

**Evidence needed:**
- Per-agent win rates (US-RC-020)
- Single-agent shadow strategies (already running: `tech_only`, `sentiment_only`)
- Compare: 11-agent consensus WR vs single-agent WR

---

### 2. Weighted Voting (Not Equal Weights)

**Assumption:** "Some agents should have more influence than others."

**Who decided this?** Initial architecture. Weight = perceived reliability.

**What problem does it solve?**
- Prevents bad agents from dragging down good ones
- Allows expert agents to override novices

**What's the empirical evidence it works?**
- ⚠️ **Weak evidence.** ADAPTIVE_WEIGHTS = True, but no performance logs showing improvement
- ❌ **No comparison** between weighted vs unweighted voting
- ❌ Component audit shows TechAgent (weight 1.0) has 0% contribution despite high weight

**What would break if we removed it?**
- System reverts to democratic voting (1 agent = 1 vote)
- Bad agents get equal say with good agents
- But if we DELETE bad agents (Phase 2), this problem disappears

**Simplest alternative:**
- **Equal weights** (0.50 weight per agent in 2-agent system)
- OR: **Boolean veto** (agent either approves or blocks, no fuzzy weights)

**Verdict:** 🟡 **Questionable. Depends on agent elimination results.**

**Evidence needed:**
- Shadow strategy: `equal_weights_static` (already running)
- Compare WR: weighted vs unweighted

---

### 3. Adaptive Threshold Adjustment

**Assumption:** "Thresholds should adjust based on recent performance."

**Who decided this?** `ADAPTIVE_WEIGHTS = True` in config. Implies dynamic tuning.

**What problem does it solve?**
- Responds to regime changes (bull/bear/choppy)
- Reduces bad trades when agents are underperforming

**What's the empirical evidence it works?**
- ❌ **No evidence.** No performance logs showing threshold adjustments
- ❌ **No comparison** between static vs adaptive thresholds
- ⚠️ Current system: CONSENSUS_THRESHOLD = 0.75 (static, raised Jan 15)

**What would break if we removed it?**
- System uses fixed threshold (e.g., 0.75) regardless of market conditions
- May trade too much in bad regimes, too little in good regimes
- But if regime detection is noise (US-RC-030), adaptive adjustment is also noise

**Simplest alternative:**
- **Static threshold** (0.75 or 0.80, tuned once via shadow testing)
- OR: **Manual adjustment** (operator changes config after reviewing performance)

**Verdict:** 🟡 **Unproven. Disable and test.**

**Evidence needed:**
- Shadow strategy: `equal_weights_static` (no adaptive adjustment, already running)
- Compare WR: adaptive vs static

---

### 4. Regime Detection & Adjustment

**Assumption:** "Markets have regimes (bull/bear/sideways). Strategy should adapt to regime."

**Who decided this?** `ralph_regime_adapter.py` + RegimeAgent. Modeled after quant hedge funds.

**What problem does it solve?**
- Momentum strategies work in trends, contrarian works in chop
- Boosts TechAgent in bull/bear, boosts SentimentAgent in sideways

**What's the empirical evidence it works?**
- ❌ **No evidence.** Component audit: RegimeAgent = 0% WR contribution
- ❌ **No accuracy validation.** US-RC-030 will measure if regime classifications are correct
- ❌ **No performance by regime.** US-RC-031 will measure if strategies actually perform differently by regime
- 🔴 **Counter-evidence:** Trend filter (regime-based) caused -3% WR impact

**What would break if we removed it?**
- System treats all markets the same (no bull/bear/sideways)
- TechAgent and SentimentAgent keep constant weights
- May underperform in specific regimes... but current system also underperforms (56% WR)

**Simplest alternative:**
- **No regime detection.** Fixed agent weights.
- **Time-based patterns** (hourly, not regime) - TimePatternAgent

**Verdict:** 🔴 **Unproven and likely harmful. Strong removal candidate.**

**Evidence needed:**
- Regime classification accuracy (US-RC-030)
- Strategy performance by regime (US-RC-031)
- Shadow strategy: `no_regime_adjustment` (already running)

---

### 5. Shadow Trading System (27 Parallel Strategies)

**Assumption:** "Running virtual strategies in parallel helps us find better strategies."

**Who decided this?** Added Jan 14, 2026. Inspired by A/B testing best practices.

**What problem does it solve?**
- Zero-risk experimentation (no real money)
- Apples-to-apples comparison on live data
- Continuous learning without manual backtesting

**What's the empirical evidence it works?**
- ✅ **Proven useful.** Vic's shadow leaderboard (US-RC-018) will rank strategies
- ✅ **ML strategies outperform agents** (ml_random_forest_60 = best performer?)
- ✅ **Identifies failures.** Inverse strategies would reveal if agents are systematically wrong

**What would break if we removed it?**
- No way to test new strategies without risking real money
- Slower optimization cycle (manual backtests only)
- Loss of comparative performance data

**Simplest alternative:**
- **Historical backtesting** (slower, uses old data)
- **Paper trading account** (separate instance, not parallel)

**Verdict:** ✅ **Proven valuable. Keep and expand.**

**Evidence needed:**
- Shadow leaderboard (US-RC-018)
- Best strategy identification (US-RC-019, US-RC-021)

---

### 6. ML Random Forest Model (Unused)

**Assumption:** "Machine learning can predict outcomes better than agents."

**Who decided this?** Trained Jan 15, 2026 after agent failures. 67.3% test accuracy.

**What problem does it solve?**
- Replace agent complexity with single model
- Potentially higher win rate (67% vs 56%)
- Fewer lines of code to maintain

**What's the empirical evidence it works?**
- ⚠️ **Test accuracy: 67.3%** (claimed)
- ❌ **Production accuracy: Unknown.** US-RC-021 will measure Jan 2026 WR
- ⚠️ **Currently disabled:** `USE_ML_MODEL = False`

**What would break if we removed it?**
- Nothing. It's already disabled.
- Loss of potential 67% WR strategy

**Simplest alternative:**
- **Pure ML mode** (no agents, just Random Forest)
- Shadow strategy: `ml_random_forest_60` (high confidence only)

**Verdict:** 🟢 **Promising. Deploy if US-RC-021 shows >60% WR.**

**Evidence needed:**
- ML performance on unseen data (US-RC-021)
- Compare: ml_random_forest_60 vs default strategy

---

### 7. Position Sizing (Tiered by Balance)

**Assumption:** "Risk should scale with account size. Smaller balance = smaller bets."

**Who decided this?** Standard risk management (Kelly Criterion-inspired).

**What problem does it solve?**
- Prevents ruin at low balances (15% of $20 = $3 bet)
- Prevents overexposure at high balances (5% of $200 = $10 bet)
- Reduces volatility of returns

**What's the empirical evidence it works?**
- ✅ **Component audit: +3.0% WR contribution**
- ✅ **Stress test** (US-RC-023) will validate 10-loss streak protection
- ✅ **Essential component** (ranked -10.0 elimination score)

**What would break if we removed it?**
- Fixed bet size (e.g., $5 per trade)
- High risk of ruin at low balances
- Insufficient risk at high balances

**Simplest alternative:**
- **Fixed bet size** ($5 or $10 per trade)
- **Kelly Criterion** (optimal sizing based on edge) - shadow strategy `kelly_sizing`

**Verdict:** ✅ **Essential. Keep and optimize (Kelly sizing).**

**Evidence needed:**
- Stress test results (US-RC-023)
- Kelly sizing shadow strategy performance

---

### 8. Drawdown Protection (30% Halt)

**Assumption:** "If we lose 30% from peak, stop trading to prevent total loss."

**Who decided this?** Standard risk management. Inspired by hedge fund drawdown limits.

**What problem does it solve?**
- Prevents catastrophic loss (95% loss like Jan 14)
- Forces operator intervention when something is broken
- Psychological circuit breaker

**What's the empirical evidence it works?**
- ✅ **Component audit: +5.0% WR contribution**
- ⚠️ **Bug found:** Jan 16 state desync prevented halt from working
- ✅ **Stress test** (US-RC-023) will validate formula

**What would break if we removed it?**
- Bot could lose 100% of balance without halting
- No safety net for bugs or market regime changes
- Operator might not notice losses until too late

**Simplest alternative:**
- **Dollar-based limit** ($50 daily loss)
- **Consecutive loss limit** (halt after 10 losses)

**Verdict:** ✅ **Essential. Keep and fix bugs.**

**Evidence needed:**
- Drawdown formula audit (US-RC-022)
- State desync root cause (US-RC-007)

---

### 9. Contrarian Fade Strategy

**Assumption:** "When market is >70% on one side, fade it (bet opposite)."

**Who decided this?** SentimentAgent logic. Inspired by market maker theory (fade retail).

**What problem does it solve?**
- Captures cheap entries (<$0.20) with high upside (5x-10x)
- Exploits overreaction and mean reversion
- Works when markets are choppy/volatile

**What's the empirical evidence it works?**
- ❌ **Currently disabled:** `ENABLE_CONTRARIAN_TRADES = False`
- ❌ **No recent performance data.** US-RC-017 will analyze historical contrarian trades
- ⚠️ **CLAUDE.md claims:** "Best performer - many $0.06-$0.13 winners"
- 🔴 **Counter-evidence:** Disabled Jan 16 after bleeding funds

**What would break if we removed it?**
- Loss of cheap entry opportunities (<$0.20)
- Fewer trades (contrarian was 30-40% of opportunities)
- Miss mean reversion profits in choppy markets

**Simplest alternative:**
- **Price-based only** (buy <$0.20, skip >$0.20, no sentiment logic)
- **Regime-dependent** (contrarian only in sideways/volatile regimes)

**Verdict:** 🔴 **Currently failing. Re-enable only if US-RC-017 shows >60% WR in historical data.**

**Evidence needed:**
- Historical contrarian performance (US-RC-017)
- Strategy-by-regime analysis (US-RC-031)
- Shadow strategy: `contrarian_focused`

---

### 10. Recovery Mode (Normal → Conservative → Defensive)

**Assumption:** "After losses, reduce bet size to recover gradually."

**Who decided this?** Inspired by casino bankroll management (reduce bets after losses).

**What problem does it solve?**
- Limits damage during losing streaks
- Psychological comfort (operator feels in control)
- Reduces risk of ruin

**What's the empirical evidence it works?**
- ❌ **Component audit: 0% WR contribution**
- ❌ **No comparison:** Recovery mode WR vs normal mode WR
- ⚠️ **Behavioral bias risk:** Gambler's fallacy (US-RC-026 will test)

**What would break if we removed it?**
- Constant bet sizing (no reduction after losses)
- Higher volatility during losing streaks
- But also: No psychological bias from "recovery mindset"

**Simplest alternative:**
- **No recovery modes.** Fixed tiered sizing based on balance only.
- **Dollar-based circuit breaker** (halt after $50 loss, not gradual reduction)

**Verdict:** 🟡 **Unproven. Likely psychological theater.**

**Evidence needed:**
- Recovery mode performance (US-RC-025)
- Gambler's fallacy test (US-RC-026)

---

### 11. RSI (Relative Strength Index) Indicator

**Assumption:** "RSI predicts reversals. Overbought >70 = sell, oversold <30 = buy."

**Who decided this?** Standard technical analysis. TechAgent uses RSI for scoring.

**What problem does it solve?**
- Identifies overbought/oversold conditions
- Mean reversion signal (pair with contrarian)

**What's the empirical evidence it works?**
- ❌ **Component audit: 0% WR contribution**
- ❌ **TechAgent has 0% contribution** (includes RSI)
- ⚠️ **RSI is lagging indicator** (calculates on past 14 periods)

**What would break if we removed it?**
- Loss of mean reversion signal
- TechAgent simplified (fewer inputs)
- But TechAgent already has 0% contribution

**Simplest alternative:**
- **Price-based mean reversion** (simple % change from 15min ago)
- **No technical indicators** (pure momentum from exchange confluence)

**Verdict:** 🔴 **Unproven and likely useless. Strong removal candidate.**

**Evidence needed:**
- TechAgent performance (US-RC-020)
- Entry price vs WR analysis (US-RC-015) - does RSI signal improve WR?

---

### 12. Exchange Confluence (2+ Exchanges Agreeing)

**Assumption:** "If 2+ exchanges show same direction, momentum is real."

**Who decided this?** TechAgent core logic. Inspired by multi-source validation.

**What problem does it solve?**
- Reduces false signals (single exchange anomaly)
- Confirms trend across multiple markets
- Early momentum detection

**What's the empirical evidence it works?**
- ❌ **Component audit: 0% WR contribution**
- ❌ **TechAgent has 0% contribution** (includes confluence)
- ⚠️ **No isolation test.** Is confluence signal helpful, or just noise?

**What would break if we removed it?**
- Single exchange can trigger trades (more trades, lower quality?)
- Loss of momentum confirmation
- But TechAgent already has 0% contribution

**Simplest alternative:**
- **Single best exchange** (Binance or Kraken, whichever has cleaner data)
- **Price-only momentum** (buy if price up >0.5% in last 5min)

**Verdict:** 🟡 **Unproven. Isolate and test.**

**Evidence needed:**
- TechAgent performance (US-RC-020)
- Shadow strategy: `tech_only` (isolate confluence)

---

### 13. Configuration Complexity (68 Parameters)

**Assumption:** "More tunable parameters = more flexibility = better performance."

**Who decided this?** Accumulated over time. Each feature added parameters.

**What problem does it solve?**
- Allows fine-tuning without code changes
- Operator can adjust thresholds on the fly

**What's the empirical evidence it works?**
- 🔴 **Counter-evidence:** 68 parameters create configuration space explosion
- 🔴 **Tuning is impossible.** 68^n combinations to test
- ❌ **No evidence** that tuning helps vs using defaults

**What would break if we removed it?**
- Less flexibility (operator can't tweak every threshold)
- Must change code to adjust behavior
- But if we DELETE 20 components (Phase 2), 80% of parameters disappear

**Simplest alternative:**
- **<10 parameters** (threshold, max_entry, position_size, drawdown_limit)
- **Hard-coded defaults** (change via code, not config)

**Verdict:** 🔴 **Configuration space explosion. Reduce to <15 parameters.**

**Evidence needed:**
- Component elimination (US-RC-031B already complete)
- Minimal Viable Strategy (US-RC-031D) - how few parameters needed?

---

## Summary: Assumptions to Test by Removing

| Assumption | Verdict | Priority | Test Method |
|------------|---------|----------|-------------|
| Multi-agent consensus | 🔴 Weak | HIGH | Shadow: `tech_only`, per-agent WR (US-RC-020) |
| Weighted voting | 🟡 Questionable | MEDIUM | Shadow: `equal_weights_static` |
| Adaptive thresholds | 🟡 Unproven | MEDIUM | Shadow: `equal_weights_static` |
| Regime detection | 🔴 Likely harmful | HIGH | Shadow: `no_regime_adjustment`, accuracy (US-RC-030) |
| Shadow trading | ✅ Proven | N/A | Keep and expand |
| ML Random Forest | 🟢 Promising | HIGH | Shadow: `ml_random_forest_60`, Jan WR (US-RC-021) |
| Tiered position sizing | ✅ Essential | N/A | Optimize with Kelly (US-RC-023) |
| Drawdown protection | ✅ Essential | N/A | Fix bugs (US-RC-022) |
| Contrarian fade | 🔴 Currently failing | HIGH | Historical analysis (US-RC-017) |
| Recovery modes | 🟡 Theater | LOW | Performance (US-RC-025), bias test (US-RC-026) |
| RSI indicator | 🔴 Useless | MEDIUM | TechAgent performance (US-RC-020) |
| Exchange confluence | 🟡 Unproven | MEDIUM | TechAgent performance (US-RC-020) |
| 68 config parameters | 🔴 Explosion | HIGH | Component elimination (US-RC-031B) |

---

## First Principles: What Would We Build From Scratch?

**Given what we know now, a minimal system would be:**

### Minimal Viable System (MVS)

**Components (4 total):**
1. **Best performing agent** (from Vic's ranking, US-RC-020)
   - OR: ML Random Forest (if US-RC-021 shows >60% WR)
2. **Entry price filter** (<$0.25 for fee advantage)
3. **Tiered position sizing** (balance-based risk scaling)
4. **Drawdown protection** (30% halt with fixed bugs)

**Configuration (5 parameters):**
1. `CONFIDENCE_THRESHOLD` = 0.60 (minimum to trade)
2. `MAX_ENTRY_PRICE` = 0.25 (fee breakeven optimization)
3. `POSITION_SIZE_TIERS` = [(30, 0.15), (75, 0.10), (150, 0.07), (inf, 0.05)]
4. `MAX_DRAWDOWN` = 0.30 (halt threshold)
5. `DAILY_LOSS_LIMIT` = $50 (circuit breaker)

**Code size estimate:** 300-500 lines (vs current 3300+ lines)

**Expected performance:**
- Win rate: 60-65% (if we pick the right agent/model)
- Trade frequency: 3-5/day (selective)
- Maintenance burden: 85% reduction

**Migration path:**
1. Identify best single agent/model (US-RC-020, US-RC-021)
2. Deploy MVS as shadow strategy
3. Run 100 trades (2-3 weeks)
4. If MVS ≥ current system, replace entire codebase
5. Keep old system in git branch for 60 days (rollback insurance)

---

## Conclusion

**Key Insight:** Most architectural complexity is **accidental, not essential**.

**Evidence:**
- 26 components analyzed
- 5 elimination candidates (1 DELETE, 4 DISABLE)
- 18 components with 0% WR contribution
- 68 config parameters (target: <10)

**Next Steps:**
1. **US-RC-031D:** Implement and test Minimal Viable Strategy
2. **US-RC-020:** Identify best single agent (if any)
3. **US-RC-021:** Validate ML model on Jan 2026 data
4. **US-RC-031E:** Calculate complexity cost-benefit (formal ROI)
5. **US-RC-031F:** Design first principles system (concrete architecture)

**Philosophy:**
> "We should make things as simple as possible, but not simpler." - Einstein
>
> Current system is **simpler-er** than necessary. Start deleting.

---

## Appendices

### Evidence Dependencies

This audit identifies assumptions. The following research tasks will provide empirical evidence:

- **US-RC-017:** Contrarian performance (historical)
- **US-RC-018:** Shadow leaderboard (best strategies)
- **US-RC-019:** Random baseline comparison (edge validation)
- **US-RC-020:** Per-agent win rates (identify best agent)
- **US-RC-021:** ML model validation (Jan 2026 WR)
- **US-RC-022:** Drawdown formula audit (bug fixes)
- **US-RC-023:** Position sizing stress test (validate tiers)
- **US-RC-025:** Recovery mode performance (theater or value?)
- **US-RC-026:** Gambler's fallacy test (behavioral bias)
- **US-RC-027:** Agent correlation (herding detection)
- **US-RC-030:** Regime classification accuracy
- **US-RC-031:** Strategy performance by regime

**Once these tasks complete, we'll have data to remove/keep each assumption.**
