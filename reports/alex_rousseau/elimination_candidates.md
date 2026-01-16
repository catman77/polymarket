# Component Elimination Audit

**Analyst:** Alex 'Occam' Rousseau (First Principles Engineer)
**Generated:** 2026-01-16 15:00 UTC
**Philosophy:** *Complexity is a liability. Every component must earn its keep.*

---

## Executive Summary

**Total Components Analyzed:** 26

- 🔴 **DELETE (high confidence):** 1 components
- 🟠 **DISABLE (test removal):** 4 components
- 🟡 **REVIEW (low value):** 18 components
- 🟢 **KEEP (marginal value):** 1 components
- ✅ **ESSENTIAL (proven value):** 2 components

### Key Findings

1. **Negative ROI Components:** Components that actively hurt win rate
2. **Dead Weight:** Components with zero measurable impact
3. **Redundancy:** Multiple components doing similar work
4. **Complexity Tax:** High LOC without corresponding value

**Total Lines of Code:** 3,301 lines (maintenance burden)

---

## Ranked Elimination Candidates

*Higher elimination score = stronger candidate for removal*

| Rank | Component | Type | Score | Recommendation | LOC | WR Impact | Freq | Burden |
|------|-----------|------|-------|----------------|-----|-----------|------|--------|
| 1 | Trend Filter | feature | 10.0 | 🔴 DELETE (high confidence) | 60 | -3.0% | 40% | MODERATE |
| 2 | SocialSentimentAgent | agent | 8.0 | 🟠 DISABLE (test removal) | 121 | +0.0% | 0% | MODERATE |
| 3 | TechAgent | agent | 7.0 | 🟠 DISABLE (test removal) | 254 | +0.0% | 50% | HIGH |
| 4 | SentimentAgent | agent | 7.0 | 🟠 DISABLE (test removal) | 238 | +0.0% | 50% | HIGH |
| 5 | RegimeAgent | agent | 7.0 | 🟠 DISABLE (test removal) | 233 | +0.0% | 50% | HIGH |
| 6 | TimePatternAgent | agent | 5.0 | 🟡 REVIEW (low value) | 92 | +0.0% | 25% | MODERATE |
| 7 | CandleAgent | agent | 5.0 | 🟡 REVIEW (low value) | 154 | +0.0% | 50% | MODERATE |
| 8 | GamblerAgent | agent | 5.0 | 🟡 REVIEW (low value) | 130 | +0.0% | 50% | MODERATE |
| 9 | ClaudeDecisionAgent | agent | 5.0 | 🟡 REVIEW (low value) | 60 | +0.0% | 50% | MODERATE |
| 10 | RiskAgent | agent | 5.0 | 🟡 REVIEW (low value) | 175 | +0.0% | 50% | MODERATE |
| 11 | OnchainAgent | agent | 5.0 | 🟡 REVIEW (low value) | 43 | +0.0% | 50% | LOW |
| 12 | OrderbookAgent | agent | 5.0 | 🟡 REVIEW (low value) | 94 | +0.0% | 50% | MODERATE |
| 13 | FundingRateAgent | agent | 5.0 | 🟡 REVIEW (low value) | 177 | +0.0% | 40% | MODERATE |
| 14 | RSI Indicator | feature | 5.0 | 🟡 REVIEW (low value) | 80 | +0.0% | 80% | MODERATE |
| 15 | Exchange Confluence | feature | 5.0 | 🟡 REVIEW (low value) | 120 | +0.0% | 90% | MODERATE |
| 16 | Regime Detection | feature | 5.0 | 🟡 REVIEW (low value) | 200 | +0.0% | 100% | HIGH |
| 17 | Recovery Mode Controller | feature | 5.0 | 🟡 REVIEW (low value) | 150 | +0.0% | 20% | MODERATE |
| 18 | Auto-Redemption | feature | 5.0 | 🟡 REVIEW (low value) | 100 | +0.0% | 100% | MODERATE |
| 19 | Candlestick Pattern Recognition | feature | 5.0 | 🟡 REVIEW (low value) | 200 | +0.0% | 70% | HIGH |
| 20 | Time Pattern Analysis | feature | 5.0 | 🟡 REVIEW (low value) | 150 | +0.0% | 50% | MODERATE |
| 21 | Orderbook Microstructure | feature | 5.0 | 🟡 REVIEW (low value) | 180 | +0.0% | 60% | MODERATE |
| 22 | Funding Rate Analysis | feature | 5.0 | 🟡 REVIEW (low value) | 120 | +0.0% | 50% | MODERATE |
| 23 | Configuration Complexity | config | 5.0 | 🟡 REVIEW (low value) | 68 | +0.0% | 100% | MODERATE |
| 24 | Position Correlation Limits | feature | 0.0 | 🟢 KEEP (marginal value) | 80 | +2.0% | 30% | MODERATE |
| 25 | Tiered Position Sizing | feature | -10.0 | ✅ ESSENTIAL (proven value) | 50 | +3.0% | 100% | MODERATE |
| 26 | Drawdown Protection | feature | -10.0 | ✅ ESSENTIAL (proven value) | 40 | +5.0% | 100% | LOW |

---

## Detailed Component Analysis

### 🔴 DELETE (high confidence) Trend Filter

**Type:** feature
**File:** `bot/momentum_bot_v12.py`
**Elimination Score:** 10.0

**Metrics:**
- Lines of Code: 60
- Maintenance Burden: MODERATE
- Decision Frequency: 40%
- Win Rate Contribution: -3.00%

**Description:** Directional bias filter (blocks trades against trend)

**Elimination Rationale:**
- ⚠️  **Negative ROI:** Actively hurts performance

### 🟠 DISABLE (test removal) SocialSentimentAgent

**Type:** agent
**File:** `agents/voting/social_sentiment_agent.py`
**Elimination Score:** 8.0

**Metrics:**
- Lines of Code: 121
- Maintenance Burden: MODERATE
- Decision Frequency: 0%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes
- ⚠️  **Low Utilization:** Used in <10% of decisions

### 🟠 DISABLE (test removal) TechAgent

**Type:** agent
**File:** `agents/tech_agent.py`
**Elimination Score:** 7.0

**Metrics:**
- Lines of Code: 254
- Maintenance Burden: HIGH
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Config Parameters (9):**
- `TECH_MIN_EXCHANGES_AGREE`
- `TECH_CONFLUENCE_THRESHOLD`
- `TECH_RSI_PERIOD`
- `TECH_RSI_OVERBOUGHT`
- `TECH_RSI_OVERSOLD`
- *...and 4 more*

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes
- ⚠️  **High Maintenance:** 254 LOC to maintain

### 🟠 DISABLE (test removal) SentimentAgent

**Type:** agent
**File:** `agents/sentiment_agent.py`
**Elimination Score:** 7.0

**Metrics:**
- Lines of Code: 238
- Maintenance Burden: HIGH
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Config Parameters (10):**
- `SENTIMENT_CONTRARIAN_PRICE_THRESHOLD`
- `SENTIMENT_CONTRARIAN_MAX_ENTRY`
- `SENTIMENT_EXTREME_THRESHOLD`
- `SENTIMENT_CHEAP_ENTRY`
- `SENTIMENT_MIN_TIME`
- *...and 5 more*

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes
- ⚠️  **High Maintenance:** 238 LOC to maintain

### 🟠 DISABLE (test removal) RegimeAgent

**Type:** agent
**File:** `agents/regime_agent.py`
**Elimination Score:** 7.0

**Metrics:**
- Lines of Code: 233
- Maintenance Burden: HIGH
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Config Parameters (8):**
- `REGIME_ADJUSTMENT_STRENGTH`
- `REGIME_ADJUSTMENT_ENABLED`
- `REGIME_HIGH_VOLATILITY`
- `REGIME_TREND_THRESHOLD`
- `REGIME_STRONG_TREND_RATIO`
- *...and 3 more*

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes
- ⚠️  **High Maintenance:** 233 LOC to maintain

### 🟡 REVIEW (low value) TimePatternAgent

**Type:** agent
**File:** `agents/time_pattern_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 92
- Maintenance Burden: MODERATE
- Decision Frequency: 25%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) CandleAgent

**Type:** agent
**File:** `agents/candle_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 154
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) GamblerAgent

**Type:** agent
**File:** `agents/gambler_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 130
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) ClaudeDecisionAgent

**Type:** agent
**File:** `agents/claude_decision_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 60
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) RiskAgent

**Type:** agent
**File:** `agents/risk_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 175
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Config Parameters (11):**
- `RISK_POSITION_TIERS`
- `RISK_MAX_POSITION_USD`
- `RISK_MIN_BET_USD`
- `RISK_MAX_DRAWDOWN`
- `RISK_MAX_TOTAL_POSITIONS`
- *...and 6 more*

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) OnchainAgent

**Type:** agent
**File:** `agents/voting/onchain_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 43
- Maintenance Burden: LOW
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) OrderbookAgent

**Type:** agent
**File:** `agents/voting/orderbook_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 94
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) FundingRateAgent

**Type:** agent
**File:** `agents/voting/funding_rate_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 177
- Maintenance Burden: MODERATE
- Decision Frequency: 40%
- Win Rate Contribution: +0.00%

**Description:** Agent voting on market direction

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) RSI Indicator

**Type:** feature
**File:** `bot/momentum_bot_v12.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 80
- Maintenance Burden: MODERATE
- Decision Frequency: 80%
- Win Rate Contribution: +0.00%

**Description:** 14-period RSI calculation across all cryptos

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Exchange Confluence

**Type:** feature
**File:** `bot/momentum_bot_v12.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 120
- Maintenance Burden: MODERATE
- Decision Frequency: 90%
- Win Rate Contribution: +0.00%

**Description:** Multi-exchange price agreement detection

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Regime Detection

**Type:** feature
**File:** `bot/ralph_regime_adapter.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 200
- Maintenance Burden: HIGH
- Decision Frequency: 100%
- Win Rate Contribution: +0.00%

**Description:** Market classification (bull/bear/sideways/volatile)

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Recovery Mode Controller

**Type:** feature
**File:** `bot/momentum_bot_v12.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 150
- Maintenance Burden: MODERATE
- Decision Frequency: 20%
- Win Rate Contribution: +0.00%

**Description:** Adjusts position sizing based on recent losses

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Auto-Redemption

**Type:** feature
**File:** `bot/momentum_bot_v12.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 100
- Maintenance Burden: MODERATE
- Decision Frequency: 100%
- Win Rate Contribution: +0.00%

**Description:** Automatic winning position redemption

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Candlestick Pattern Recognition

**Type:** feature
**File:** `agents/candle_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 200
- Maintenance Burden: HIGH
- Decision Frequency: 70%
- Win Rate Contribution: +0.00%

**Description:** Detects bullish/bearish candlestick patterns

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Time Pattern Analysis

**Type:** feature
**File:** `agents/time_pattern_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 150
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Historical hourly performance patterns

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Orderbook Microstructure

**Type:** feature
**File:** `agents/voting/orderbook_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 180
- Maintenance Burden: MODERATE
- Decision Frequency: 60%
- Win Rate Contribution: +0.00%

**Description:** Bid-ask spread and depth analysis

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Funding Rate Analysis

**Type:** feature
**File:** `agents/voting/funding_rate_agent.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 120
- Maintenance Burden: MODERATE
- Decision Frequency: 50%
- Win Rate Contribution: +0.00%

**Description:** Derivatives funding rate signals

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

### 🟡 REVIEW (low value) Configuration Complexity

**Type:** config
**File:** `config/agent_config.py`
**Elimination Score:** 5.0

**Metrics:**
- Lines of Code: 68
- Maintenance Burden: MODERATE
- Decision Frequency: 100%
- Win Rate Contribution: +0.00%

**Description:** 68 tunable parameters creating configuration space explosion

**Elimination Rationale:**
- ⚠️  **Zero Impact:** No measurable effect on outcomes

---

## Implementation Recommendations

### Phase 1: Delete Negative ROI Components (Week 1)

- [ ] **DELETE Trend Filter** (-3.00% WR impact)
  - File: `bot/momentum_bot_v12.py`
  - Expected improvement: +3.0% win rate

### Phase 2: Disable Dead Weight (Week 2)

- [ ] **DISABLE SocialSentimentAgent** (zero impact, 121 LOC)
  - Set `ENABLE_SOCIALSENTIMENT_AGENT = False`
  - Monitor: Should see no WR change
- [ ] **DISABLE TechAgent** (zero impact, 254 LOC)
  - Set `ENABLE_TECH_AGENT = False`
  - Monitor: Should see no WR change
- [ ] **DISABLE SentimentAgent** (zero impact, 238 LOC)
  - Set `ENABLE_SENTIMENT_AGENT = False`
  - Monitor: Should see no WR change
- [ ] **DISABLE RegimeAgent** (zero impact, 233 LOC)
  - Set `ENABLE_REGIME_AGENT = False`
  - Monitor: Should see no WR change

### Phase 3: Config Simplification (Week 3)

- [ ] **REDUCE config parameters from 68 to <15**
  - Remove: Per-agent thresholds (use global)
  - Remove: Unused regime adjustment parameters
  - Remove: Feature flags for disabled components

### Testing Protocol

For each component removal:

1. **Shadow test:** Add strategy with component disabled to shadow trading
2. **Run 50 trades:** Accumulate statistical significance
3. **Compare WR:** If WR ≥ baseline, remove permanently
4. **Measure complexity reduction:** LOC removed, params removed
5. **Rollback plan:** Keep component in git history for 30 days

---

## First Principles Question

**"If we started from scratch, what would we build?"**

Based on this audit, the simplest viable system might be:

1. **Single best agent** (from Vic's performance ranking)
2. **Entry price filter** (<$0.25 for fee advantage)
3. **Position sizing** (tiered based on balance)
4. **Drawdown protection** (30% halt)

**Total LOC estimate:** <500 lines (vs current 3300+ lines)

**Next step:** Implement Minimal Viable Strategy (US-RC-031D) to test this hypothesis

