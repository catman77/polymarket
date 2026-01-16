# PRD: Elite Research Team - Polymarket AutoTrader System Evaluation
**Product Requirements Document**

---

## Document Information

- **Project:** Polymarket AutoTrader Comprehensive System Evaluation
- **Version:** 1.0.0
- **Date:** 2026-01-16
- **Status:** DRAFT
- **Owner:** Lead Researcher (Binary Trading Systems & Gambling Philosophy Expert)
- **Stakeholders:** System Owner, VPS Operations, Strategy Development Team

---

## Executive Summary

This PRD defines a comprehensive evaluation of the Polymarket AutoTrader v12.1 binary options trading system by an elite 8-person research team. Each researcher has specialized tasks aligned with their expertise to collectively answer: **Is the system profitable, sustainable, optimizable, safe, and trustworthy?**

**Timeline:** 4 weeks (Jan 16 - Feb 13, 2026)

**Expected Outcome:** Actionable recommendations to achieve 60-65% win rate target with validated risk controls.

---

## Background

### System Overview

**Polymarket AutoTrader v12.1** - Automated trading bot for 15-minute binary outcome markets

**Current State:**
- **Balance:** $200.97 (33% drawdown from $300 peak)
- **Win Rate:** 56-60% (claimed, needs validation)
- **Architecture:** Multi-agent consensus system (4-11 agents voting)
- **Risk Controls:** 30% drawdown halt, tiered position sizing, correlation limits
- **Environment:** Production VPS (24/7 trading since Jan 2026)

**Critical Issues:**
1. **Jan 14 Incident:** Lost 95% ($157 → $7) due to trend filter bias (96.5% UP trades)
2. **Jan 16 Incident:** State tracking desync ($186 error in peak_balance)
3. **Optimization Need:** Current 56% win rate vs 60-65% target

**Opportunity:**
- 27 shadow strategies running in parallel
- 4-week optimization roadmap in progress
- ML model available (67.3% test accuracy claimed)

---

## Goals & Success Criteria

### Primary Goals

1. **Validate Performance Claims**
   - Is 56-60% win rate statistically significant?
   - What's the true expected value per trade after fees?

2. **Identify System Vulnerabilities**
   - Hidden bugs beyond documented incidents
   - Risk control weaknesses
   - Data integrity issues

3. **Optimize Strategy**
   - Which agents add vs subtract value?
   - Which shadow strategies should be promoted?
   - Path to 60-65% win rate

4. **Ensure Safety**
   - Probability of ruin calculation
   - Stress test drawdown protections
   - Validate position sizing math

### Success Metrics

- **Coverage:** All 8 research domains completed
- **Actionability:** ≥10 concrete optimization recommendations
- **Validation:** Statistical significance achieved (p < 0.05)
- **Risk Assessment:** Probability of ruin calculated with 95% confidence
- **Timeline:** All deliverables completed within 4 weeks

---

## Research Team & Task Assignments

---

## RESEARCHER #1: Dr. Sarah Chen - Probabilistic Mathematician

### Research Domain
**Mathematical foundation validation & expected value analysis**

### Primary Research Question
**Is the Polymarket AutoTrader mathematically profitable after accounting for fees, and what is the optimal position sizing strategy?**

### Tasks

#### Task 1.1: Fee Economics Validation
**Objective:** Verify breakeven calculations and fee impact on profitability

**Activities:**
1. Validate fee schedule claims:
   - Confirm 6.3% round-trip at 50% probability
   - Calculate exact fees at $0.12, $0.20, $0.25, $0.30 entry prices
   - Map fee curve across 0-100% probability range

2. Calculate true breakeven win rate:
   - Account for variable fees per entry price
   - Factor in slippage (if observable in logs)
   - Calculate weighted average breakeven across actual trade distribution

3. Expected value analysis:
   - Given current 56-60% win rate, what's EV per $1 risked?
   - At what win rate does system become unprofitable?
   - Sensitivity analysis: EV vs win rate curve

**Deliverables:**
- `reports/sarah_chen/fee_economics_validation.md` - Detailed fee analysis
- `reports/sarah_chen/breakeven_calculator.py` - Python script for fee calculations
- `reports/sarah_chen/ev_sensitivity_chart.png` - EV vs win rate visualization

**Success Criteria:**
- Fee calculations match Polymarket documentation within 0.1%
- Breakeven win rate calculated with mathematical proof
- EV curve validated against actual trade history (100+ trades)

**Data Sources:**
- Polymarket fee documentation
- `bot.log` - Extract actual entry prices from trades
- `simulation/trade_journal.db` - Shadow strategy outcomes

**Timeline:** Days 1-3

---

#### Task 1.2: Position Sizing Optimization
**Objective:** Compare current tiered sizing vs Kelly Criterion optimal

**Activities:**
1. Audit current tiered sizing:
   ```python
   RISK_POSITION_TIERS = [
       (30, 0.15),     # Balance < $30: max 15% per trade
       (75, 0.10),     # Balance $30-75: max 10%
       (150, 0.07),    # Balance $75-150: max 7%
       (inf, 0.05),    # Balance > $150: max 5%
   ]
   ```
   - Are these tiers mathematically justified?
   - Compare to Kelly Criterion formula: `f* = (bp - q) / b`
     - b = odds (payout ratio)
     - p = win probability
     - q = loss probability (1-p)

2. Calculate optimal Kelly sizing:
   - At 56% win rate, what's Kelly optimal?
   - At 60% win rate, what's Kelly optimal?
   - Compare full Kelly vs fractional Kelly (0.25x, 0.5x)

3. Backtest alternative sizing:
   - Apply Kelly sizing to historical trades
   - Compare final balance vs actual tiered sizing
   - Calculate risk-adjusted returns (Sharpe ratio)

4. Probability of ruin calculation:
   - Given current sizing, what's prob of hitting $0?
   - How many consecutive losses until ruin?
   - Monte Carlo simulation (10,000 trials)

**Deliverables:**
- `reports/sarah_chen/kelly_vs_tiered_analysis.md` - Sizing comparison
- `reports/sarah_chen/kelly_backtest.py` - Backtesting script
- `reports/sarah_chen/probability_of_ruin.ipynb` - Jupyter notebook with simulations
- `reports/sarah_chen/optimal_sizing_recommendation.md` - Final recommendation

**Success Criteria:**
- Kelly calculations verified by independent implementation
- Backtest uses actual trade history (≥100 trades)
- Probability of ruin calculated with 95% confidence interval
- Clear recommendation: keep tiered sizing OR switch to Kelly (with rationale)

**Data Sources:**
- `state/trading_state.json` - Balance history
- `bot.log` - Historical trades with entry/exit prices
- `simulation/trade_journal.db` - Shadow strategy results

**Timeline:** Days 4-7

---

#### Task 1.3: Statistical Significance Testing
**Objective:** Determine if win rate is statistically different from coin flip

**Activities:**
1. Hypothesis testing:
   - H0: Win rate = 50% (coin flip)
   - H1: Win rate > 50% (system has edge)
   - Calculate z-score and p-value
   - Determine required sample size for 95% confidence

2. Confidence interval calculation:
   - 95% CI for current win rate
   - At what sample size does CI narrow to ±2%?

3. Variance analysis:
   - Is win rate consistent across cryptos (BTC/ETH/SOL/XRP)?
   - Is win rate consistent across strategies (early/contrarian/late)?
   - Is win rate consistent across time (morning/afternoon/evening)?

4. Power analysis:
   - Given current sample size, what effect size can we detect?
   - How many more trades needed to detect 60% vs 56% difference?

**Deliverables:**
- `reports/sarah_chen/statistical_significance.md` - Hypothesis test results
- `reports/sarah_chen/confidence_intervals.csv` - CI calculations per segment
- `reports/sarah_chen/power_analysis.py` - Sample size calculator

**Success Criteria:**
- Null hypothesis rejected with p < 0.05 (or conclusion that more data needed)
- Confidence intervals calculated for all sub-segments
- Minimum sample size recommendation for future testing

**Data Sources:**
- `bot.log` - All historical trades
- `simulation/trade_journal.db` - Shadow strategy results (1000+ trades)

**Timeline:** Days 8-10

---

#### Task 1.4: Risk-Adjusted Return Metrics
**Objective:** Calculate Sharpe ratio, Sortino ratio, and max drawdown statistics

**Activities:**
1. Calculate daily returns:
   - Extract balance snapshots from state file
   - Calculate daily ROI
   - Annualize returns

2. Volatility metrics:
   - Standard deviation of daily returns
   - Downside deviation (Sortino)
   - Maximum drawdown (peak to trough)

3. Risk-adjusted ratios:
   - Sharpe ratio: (Return - RiskFree) / StdDev
   - Sortino ratio: (Return - RiskFree) / DownsideDev
   - Calmar ratio: Return / MaxDrawdown

4. Benchmarking:
   - Compare to random baseline (50/50 coin flip)
   - Compare to best shadow strategy
   - Compare to "hodl" BTC strategy

**Deliverables:**
- `reports/sarah_chen/risk_adjusted_metrics.md` - Comprehensive metrics report
- `reports/sarah_chen/performance_dashboard.png` - Visual comparison chart
- `reports/sarah_chen/benchmark_comparison.csv` - Performance vs baselines

**Success Criteria:**
- Sharpe ratio > 1.0 indicates good risk-adjusted performance
- Sortino ratio > Sharpe (downside risk lower than total volatility)
- Performance metrics comparable to industry standards

**Data Sources:**
- `state/trading_state.json` - Balance history
- `bot.log` - Trade-level P&L
- `simulation/trade_journal.db` - Shadow strategy comparisons

**Timeline:** Days 11-14

---

### Dependencies
- **Upstream:** Needs clean data from Dr. Kenji Nakamoto (Data Forensics)
- **Downstream:** Results inform James Martinez (entry price optimization) and Colonel Stevens (risk sizing validation)

### Risk Mitigation
- **Risk:** Insufficient trade history for statistical significance
  - **Mitigation:** Use shadow trading data (27 strategies × trades = larger sample)
- **Risk:** Fee calculations don't match reality
  - **Mitigation:** Validate against actual on-chain transaction costs

---

## RESEARCHER #2: James "Jimmy the Greek" Martinez - Market Microstructure Specialist

### Research Domain
**Order book dynamics, entry timing optimization, and liquidity analysis**

### Primary Research Question
**What are the optimal entry prices and timing windows for maximizing edge while minimizing fee drag?**

### Tasks

#### Task 2.1: Entry Price Distribution Analysis
**Objective:** Identify actual entry prices vs configured limits

**Activities:**
1. Extract all entry prices from trade logs:
   - Parse `bot.log` for "ORDER PLACED" entries
   - Extract entry price, direction, crypto, epoch time

2. Statistical analysis:
   - Mean, median, mode entry prices
   - Distribution by strategy (early momentum, contrarian, late confirmation)
   - Distribution by crypto (BTC/ETH/SOL/XRP)
   - Correlation: entry price vs outcome (win/loss)

3. Compare to configuration:
   - Configured limits: MAX_ENTRY=0.25, EARLY_MAX_ENTRY=0.30, CONTRARIAN_MAX=0.20
   - Are actual entries respecting these limits?
   - How many trades rejected due to price too high?

4. Fee impact analysis:
   - Calculate actual fees paid per trade
   - Weighted average fee rate
   - Identify outlier trades (unusually high fees)

**Deliverables:**
- `reports/jimmy_martinez/entry_price_distribution.md` - Statistical analysis
- `reports/jimmy_martinez/entry_price_histogram.png` - Visual distribution
- `reports/jimmy_martinez/entry_vs_outcome.csv` - Correlation data
- `reports/jimmy_martinez/fee_analysis.md` - Actual fees vs theoretical

**Success Criteria:**
- All trades from `bot.log` successfully parsed (≥100 trades)
- Clear identification of sweet spot entry ranges
- Statistically significant correlation between entry price and win rate (p < 0.05)

**Data Sources:**
- `bot.log` - Historical trade entries
- `config/agent_config.py` - Configured price limits
- Polymarket API - On-chain transaction costs

**Timeline:** Days 1-4

---

#### Task 2.2: Timing Window Optimization
**Objective:** Determine best time within epoch to place trades

**Activities:**
1. Extract epoch timing data:
   - Parse `bot.log` for "seconds into epoch" field
   - Categorize trades:
     - Early momentum: 15-300s
     - Mid-epoch contrarian: 30-700s
     - Late confirmation: 720-900s (12-15 min)

2. Win rate by timing window:
   - Calculate win rate for each 60s bucket (0-60s, 60-120s, etc.)
   - Identify highest win rate windows
   - Test statistical significance of differences

3. Price evolution analysis:
   - How do market prices change throughout epoch?
   - Do early entries get better prices than late entries?
   - Does "future window" logic (v12.1) improve timing?

4. Opportunity cost analysis:
   - How many profitable windows were missed (no trade placed)?
   - How many unprofitable trades could have been avoided by waiting?

**Deliverables:**
- `reports/jimmy_martinez/timing_window_analysis.md` - Win rate by timing
- `reports/jimmy_martinez/timing_heatmap.png` - Visual win rate by epoch second
- `reports/jimmy_martinez/price_evolution_chart.png` - Market price changes
- `reports/jimmy_martinez/timing_recommendations.md` - Optimal windows

**Success Criteria:**
- Identify timing windows with ≥5% win rate advantage
- Quantify opportunity cost of current timing strategy
- Provide actionable entry timing rules

**Data Sources:**
- `bot.log` - Trade timing data
- `simulation/trade_journal.db` - Shadow strategy timing experiments

**Timeline:** Days 5-8

---

#### Task 2.3: Contrarian Fade Strategy Validation
**Objective:** Evaluate contrarian trades (fade >70% overpricing)

**Activities:**
1. Identify contrarian trades:
   - Parse `bot.log` for "CONTRARIAN" or "SentimentAgent" signals
   - Extract: entry price, opposite side price, outcome

2. Performance analysis:
   - Win rate of contrarian trades vs non-contrarian
   - Average ROI per contrarian trade
   - Success rate by extremity level (70-80%, 80-90%, 90-100%)

3. Regime dependency:
   - Does contrarian work better in choppy markets?
   - Does contrarian fail in trending markets? (Jan 14 incident analysis)
   - Correlation: contrarian win rate vs RegimeAgent classification

4. Timing within contrarian window:
   - Configured: 30-700s
   - Does early contrarian (30-300s) beat late (300-700s)?
   - Optimal contrarian entry timing

5. Price threshold analysis:
   - Current: Fade when opposite side >70%
   - Test alternative thresholds: 75%, 80%, 85%
   - Which threshold maximizes edge?

**Deliverables:**
- `reports/jimmy_martinez/contrarian_performance.md` - Win rate analysis
- `reports/jimmy_martinez/contrarian_by_regime.csv` - Performance per regime
- `reports/jimmy_martinez/contrarian_threshold_test.md` - Optimal threshold
- `reports/jimmy_martinez/contrarian_recommendation.md` - Keep/modify/disable?

**Success Criteria:**
- Clear answer: Is contrarian profitable? (Yes/No with statistical proof)
- If profitable: Optimal threshold and timing identified
- If unprofitable: Regime conditions where it works (if any)

**Data Sources:**
- `bot.log` - Contrarian trade history
- `agents/sentiment_agent.py` - Contrarian logic code review
- `config/agent_config.py` - ENABLE_CONTRARIAN_TRADES flag (currently False)

**Timeline:** Days 9-12

---

#### Task 2.4: Liquidity & Slippage Analysis
**Objective:** Measure actual execution prices vs expected prices

**Activities:**
1. Order execution analysis:
   - Compare intended entry price (from logs) vs actual fill price (on-chain)
   - Calculate slippage: (ActualPrice - IntendedPrice) / IntendedPrice
   - Identify high-slippage trades

2. Market depth assessment:
   - Use Polymarket CLOB API to snapshot order books
   - Measure bid/ask spreads during bot trading hours
   - Identify thin markets (low liquidity)

3. Position size impact:
   - Does larger position size cause more slippage?
   - Current max: $15 per trade
   - Test: Would smaller positions get better fills?

4. Timing impact on liquidity:
   - Is liquidity better early or late in epoch?
   - Correlation: slippage vs seconds into epoch

**Deliverables:**
- `reports/jimmy_martinez/slippage_analysis.md` - Execution quality report
- `reports/jimmy_martinez/liquidity_by_crypto.csv` - Order book depth per asset
- `reports/jimmy_martinez/position_size_impact.png` - Slippage vs trade size
- `reports/jimmy_martinez/execution_recommendations.md` - Order placement improvements

**Success Criteria:**
- Slippage quantified for ≥50 trades
- Identify if slippage is material (>1% of edge)
- Provide actionable order placement strategy

**Data Sources:**
- Polymarket CLOB API - Order book snapshots
- Polygon RPC - On-chain transaction data
- `bot.log` - Intended vs actual prices

**Timeline:** Days 13-16

---

### Dependencies
- **Upstream:** Needs fee validation from Dr. Sarah Chen
- **Downstream:** Timing/entry insights feed into Victor Ramanujan (strategy optimization)

### Risk Mitigation
- **Risk:** CLOB API rate limiting prevents order book snapshots
  - **Mitigation:** Sample order books during off-peak hours, use cached data
- **Risk:** On-chain data difficult to parse
  - **Mitigation:** Use Polymarket Data API as fallback

---

## RESEARCHER #3: Dr. Amara Johnson - Behavioral Finance Expert

### Research Domain
**Psychological biases in risk controls, recovery modes, and agent decision-making**

### Primary Research Question
**What behavioral biases are embedded in the system's design, and do they help or hurt performance?**

### Tasks

#### Task 3.1: Loss Aversion & Recovery Mode Analysis
**Objective:** Evaluate psychological safety mechanisms in risk controls

**Activities:**
1. Recovery mode logic audit:
   - Review code in `bot/momentum_bot_v12.py` (RecoveryController class)
   - Modes: normal → conservative → defensive → recovery → halted
   - Triggers: 8% loss, 15% loss, 25% loss, 30% drawdown

2. Position sizing adjustments:
   - How much does sizing reduce in each mode?
   - Is this mathematically justified or emotionally driven?
   - Compare to loss aversion theory (losses feel 2x worse than gains)

3. Historical mode transitions:
   - Parse `bot.log` for mode changes
   - Calculate: time spent in each mode
   - Performance in each mode (win rate, ROI)

4. Behavioral bias identification:
   - **Loss aversion:** Does defensive mode reduce risk too much?
   - **Recency bias:** Does bot overreact to recent losses?
   - **Anchoring:** Is peak_balance anchor causing premature halts?

5. Alternative recovery strategies:
   - What if sizing didn't change, only trade frequency?
   - What if bot increased aggression after losses (martingale-lite)?
   - Monte Carlo: Test alternative recovery logic

**Deliverables:**
- `reports/amara_johnson/recovery_mode_audit.md` - Behavioral analysis
- `reports/amara_johnson/mode_performance.csv` - Win rate per mode
- `reports/amara_johnson/bias_identification.md` - Documented biases
- `reports/amara_johnson/alternative_recovery.ipynb` - Simulation of alternatives
- `reports/amara_johnson/recovery_recommendations.md` - Improved logic proposal

**Success Criteria:**
- All mode transitions documented from logs
- Statistical test: Does recovery mode improve or hurt performance?
- At least 3 behavioral biases identified with evidence
- Actionable recommendation: keep/modify/remove recovery modes

**Data Sources:**
- `bot/momentum_bot_v12.py` - RecoveryController code
- `bot.log` - Mode transition history
- `state/trading_state.json` - Current mode state

**Timeline:** Days 1-5

---

#### Task 3.2: Gambler's Fallacy vs Hot Hand Detection
**Objective:** Test if consecutive wins/losses affect decision quality

**Activities:**
1. Streak analysis:
   - Extract consecutive wins and losses from logs
   - Current tracking: `consecutive_wins`, `consecutive_losses` in state

2. Decision quality after streaks:
   - After 2+ wins: Do trades become overconfident (lower entry standards)?
   - After 2+ losses: Do trades become too conservative (higher entry standards)?
   - Compare: win rate after streaks vs baseline

3. Agent voting patterns:
   - Does agent consensus threshold change after streaks?
   - Do individual agents become more/less confident?
   - Parse `simulation/trade_journal.db` for agent_votes table

4. Gambler's fallacy test:
   - After 3 losses, does bot expect a win? (betting more aggressively)
   - Statistical test: Are consecutive outcomes independent?

5. Hot hand effect test:
   - After 3 wins, does bot bet more? (believing "hot streak")
   - Is there actual momentum in outcomes? (autocorrelation test)

**Deliverables:**
- `reports/amara_johnson/streak_analysis.md` - Consecutive W/L patterns
- `reports/amara_johnson/decision_quality_after_streaks.csv` - Performance data
- `reports/amara_johnson/gambler_fallacy_test.md` - Statistical test results
- `reports/amara_johnson/streak_recommendations.md` - Should bot react to streaks?

**Success Criteria:**
- Statistical test: Are outcomes independent? (p < 0.05)
- Identify if bot exhibits gambler's fallacy or hot hand bias
- Clear recommendation: Adjust/remove streak-based logic

**Data Sources:**
- `bot.log` - Win/loss sequences
- `state/trading_state.json` - Consecutive streak counters
- `simulation/trade_journal.db` - Agent voting after streaks

**Timeline:** Days 6-9

---

#### Task 3.3: Consensus Voting Bias Analysis
**Objective:** Identify groupthink and herding in agent system

**Activities:**
1. Agent agreement patterns:
   - How often do all agents agree (unanimous votes)?
   - How often is there 1 dissenter vs majority?
   - Distribution of voting splits (4-0, 3-1, 2-2)

2. Herding detection:
   - Do agents copy each other's votes? (correlation analysis)
   - Are certain agents "followers" vs "leaders"?
   - Does RegimeAgent bias others? (regime multipliers in effect)

3. Diversity of thought:
   - Is agent disagreement healthy (improves outcomes)?
   - Or is consensus required for edge (unanimous = high confidence)?
   - Compare: unanimous votes vs split votes → win rates

4. Groupthink scenarios:
   - Jan 14 incident: Did all agents vote UP together (herding)?
   - Identify other groupthink failures
   - When agents disagree, who's usually right?

5. Optimal consensus threshold:
   - Current: 0.75 weighted score required
   - Test: Would 0.60 or 0.85 improve performance?
   - Trade-off: More trades (lower threshold) vs better trades (higher threshold)

**Deliverables:**
- `reports/amara_johnson/agent_voting_patterns.md` - Agreement analysis
- `reports/amara_johnson/herding_detection.csv` - Agent correlation matrix
- `reports/amara_johnson/groupthink_incidents.md` - Case studies
- `reports/amara_johnson/optimal_consensus.ipynb` - Threshold sensitivity analysis
- `reports/amara_johnson/voting_recommendations.md` - Consensus improvements

**Success Criteria:**
- Correlation matrix for all agent pairs (detect herding)
- Statistical test: Does unanimous vote → better outcomes?
- Optimal consensus threshold identified (maximize Sharpe ratio)

**Data Sources:**
- `simulation/trade_journal.db` - agent_votes table (individual agent decisions)
- `agents/voting/vote_aggregator.py` - Consensus logic code
- `config/agent_config.py` - Current thresholds (0.75/0.60)

**Timeline:** Days 10-14

---

#### Task 3.4: Overconfidence & Confirmation Bias Audit
**Objective:** Identify if agents/bot exhibit overconfidence in predictions

**Activities:**
1. Calibration analysis:
   - When agents vote 80% confidence, do they win 80% of the time?
   - Plot: Predicted confidence vs actual win rate
   - Perfect calibration: line y=x

2. Overconfidence detection:
   - If predicted 80% but actual 60% → overconfident
   - Calculate calibration error per agent
   - Which agents are worst calibrated?

3. Confirmation bias in data:
   - Do agents selectively use data that confirms their bias?
   - Example: TechAgent ignoring contrary RSI signals
   - Code review: `agents/tech_agent.py`, `agents/sentiment_agent.py`

4. Hindsight bias:
   - After loss, does bot say "I should have known"? (logs)
   - Is post-hoc rationalization present in logic?

5. Confidence interval analysis:
   - Do agents provide uncertainty estimates?
   - Or only point predictions? (Less Bayesian thinking)

**Deliverables:**
- `reports/amara_johnson/calibration_analysis.md` - Predicted vs actual
- `reports/amara_johnson/calibration_plot.png` - Visual calibration curve
- `reports/amara_johnson/overconfidence_per_agent.csv` - Calibration errors
- `reports/amara_johnson/confirmation_bias_audit.md` - Code review findings
- `reports/amara_johnson/confidence_recommendations.md` - Improve calibration

**Success Criteria:**
- Calibration curve generated for each agent
- Identify overconfident agents (calibration error >10%)
- Provide recalibration strategy (e.g., adjust confidence multipliers)

**Data Sources:**
- `simulation/trade_journal.db` - Agent confidence scores + outcomes
- `agents/*.py` - Code review for selective data usage
- `bot.log` - Post-hoc rationalizations (if logged)

**Timeline:** Days 15-18

---

### Dependencies
- **Upstream:** Needs clean agent voting data from Dr. Kenji Nakamoto
- **Downstream:** Bias findings inform Victor Ramanujan (agent weight adjustments)

### Risk Mitigation
- **Risk:** Agent voting data incomplete in database
  - **Mitigation:** Reconstruct from `bot.log` parsing
- **Risk:** Code review reveals no obvious biases
  - **Mitigation:** Focus on statistical calibration analysis

---

## RESEARCHER #4: Victor "Vic" Ramanujan - Quantitative Strategist

### Research Domain
**Agent performance evaluation, ML model validation, and strategy optimization**

### Primary Research Question
**Which agents/strategies provide genuine edge, and what's the optimal configuration for 60-65% win rate?**

### Tasks

#### Task 4.1: Per-Agent Performance Tracking
**Objective:** Isolate individual agent contribution to win rate

**Activities:**
1. Agent voting history extraction:
   - Query `simulation/trade_journal.db` → agent_votes table
   - Extract: agent_name, vote_direction, confidence, outcome
   - Calculate per-agent metrics:
     - Win rate when agent votes Up vs Down
     - Average confidence when right vs wrong
     - Correlation: agent confidence → outcome

2. Agent isolation testing:
   - Using shadow strategies: `tech_only`, `sentiment_only`, etc.
   - Compare: Single-agent win rate vs multi-agent consensus
   - Identify agents that hurt performance (WR < 50%)

3. Agent weight sensitivity:
   - Current weights: All 1.0 (equal)
   - Test: What if TechAgent 2.0x weight? SentimentAgent 0.5x?
   - Shadow strategy: `momentum_focused` (Tech boosted)
   - Find optimal weight vector

4. Redundancy analysis:
   - Are multiple agents providing same signal? (correlation)
   - Example: Do TechAgent + RegimeAgent duplicate?
   - Dimensionality reduction: PCA on agent votes

5. Underperformer identification:
   - Which agents have WR < 50% (coin flip)?
   - Recommendation: Disable or retrain
   - Current disable flags in `config/agent_config.py`

**Deliverables:**
- `reports/vic_ramanujan/per_agent_performance.md` - Win rate per agent
- `reports/vic_ramanujan/agent_correlation_matrix.csv` - Redundancy analysis
- `reports/vic_ramanujan/optimal_weights.ipynb` - Weight optimization
- `reports/vic_ramanujan/agent_rankings.csv` - Ranked by contribution
- `reports/vic_ramanujan/disable_recommendations.md` - Agents to disable

**Success Criteria:**
- Per-agent win rate calculated with ≥50 votes each
- Identify ≥1 underperforming agent (WR < 50%, p < 0.05)
- Optimal weight vector found (maximizes Sharpe ratio)
- Clear disable/enable recommendations

**Data Sources:**
- `simulation/trade_journal.db` - agent_votes table
- Shadow strategies: `tech_only`, `sentiment_only`, etc.
- `config/agent_config.py` - Current weights and flags

**Timeline:** Days 1-5

---

#### Task 4.2: ML Model Validation (Random Forest)
**Objective:** Verify 67.3% test accuracy claim and assess production readiness

**Activities:**
1. Model artifact inspection:
   - Locate trained model: `models/random_forest_model.pkl` (if exists)
   - Review training code: Check for data leakage
   - Validate train/test split (temporal split? random?)

2. Feature engineering audit:
   - What features are used? (price, volume, RSI, agent votes?)
   - Are future-looking features included? (data leakage risk)
   - Feature importance analysis (which features drive predictions?)

3. Test set validation:
   - Reproduce 67.3% accuracy on original test set
   - Calculate: precision, recall, F1, AUC-ROC
   - Confusion matrix: Where does model fail?

4. Out-of-sample testing:
   - Test on Jan 2026 data (post-training)
   - Does accuracy hold? Or overfitting?
   - Compare: ML win rate vs agent system win rate

5. Confidence calibration:
   - When model says 60% confidence, is actual WR 60%?
   - Calibration curve (like Dr. Johnson's agent analysis)
   - Adjust: Platt scaling or isotonic regression

6. Shadow strategy performance:
   - Review: `ml_random_forest_50`, `ml_random_forest_55`, `ml_random_forest_60`
   - Which threshold performs best?
   - Compare: ML vs agent consensus

7. Production deployment risk:
   - Current: `USE_ML_MODEL = False` (disabled due to 40% WR concern)
   - Why did production fail? (40% WR vs 67% test?)
   - Should ML replace agents or augment them?

**Deliverables:**
- `reports/vic_ramanujan/ml_model_audit.md` - Training/testing validation
- `reports/vic_ramanujan/ml_feature_importance.png` - Feature analysis
- `reports/vic_ramanujan/ml_confusion_matrix.png` - Error analysis
- `reports/vic_ramanujan/ml_calibration_curve.png` - Confidence calibration
- `reports/vic_ramanujan/ml_vs_agents.csv` - Performance comparison
- `reports/vic_ramanujan/ml_recommendation.md` - Deploy/retrain/abandon?

**Success Criteria:**
- 67.3% accuracy reproduced on test set (or discrepancy explained)
- Data leakage audit completed (clean bill of health OR issues identified)
- Clear recommendation: Use ML or stick with agents (with rationale)

**Data Sources:**
- `models/` directory (if exists) - Trained model artifacts
- `ml_training/` directory (if exists) - Training scripts
- `simulation/trade_journal.db` - ML shadow strategy results
- `config/agent_config.py` - USE_ML_MODEL flag

**Timeline:** Days 6-10

---

#### Task 4.3: Shadow Strategy Tournament Analysis
**Objective:** Identify best-performing shadow strategy for promotion to production

**Activities:**
1. Shadow strategy leaderboard:
   - Query `simulation/trade_journal.db` → performance table
   - Rank by: Total P&L, Win Rate, Sharpe Ratio, Max Drawdown
   - Current strategies: 27 running (see `config/agent_config.py`)

2. Statistical significance testing:
   - Is top strategy significantly better than #2? (t-test)
   - How many trades needed for 95% confidence?
   - Are results stable over time? (rolling win rate)

3. Strategy clustering:
   - Group similar strategies (k-means)
   - Example: Conservative cluster vs Aggressive cluster
   - Identify strategy "families" that work

4. Regime-dependent performance:
   - Does `contrarian_focused` win in choppy markets?
   - Does `momentum_focused` win in trending markets?
   - Conditional strategy switching recommendation

5. Inverse strategy analysis:
   - Review: `inverse_consensus`, `inverse_momentum`, `inverse_sentiment`
   - If these win, agents are consistently wrong!
   - Diagnostic: Are agents anti-predictive?

6. Baseline comparison:
   - `random_baseline` (50/50 coin flip)
   - Does ANY strategy beat random? (sanity check)
   - If not, system has no edge

7. Kelly sizing strategy:
   - Review: `kelly_sizing` shadow strategy
   - Does Kelly beat tiered sizing? (vs Dr. Chen's analysis)
   - Validate with actual trade simulations

**Deliverables:**
- `reports/vic_ramanujan/shadow_leaderboard.csv` - Ranked strategies
- `reports/vic_ramanujan/strategy_significance.md` - Statistical tests
- `reports/vic_ramanujan/strategy_clusters.png` - Visual grouping
- `reports/vic_ramanujan/regime_performance.csv` - Strategy vs regime
- `reports/vic_ramanujan/inverse_analysis.md` - Are agents anti-predictive?
- `reports/vic_ramanujan/promotion_recommendation.md` - Which strategy to deploy?

**Success Criteria:**
- All 27 strategies ranked with statistical confidence
- Top strategy identified with p < 0.05 vs baseline
- Regime-switching logic proposed (if applicable)
- Clear promotion decision: Strategy name + deployment plan

**Data Sources:**
- `simulation/trade_journal.db` - All shadow strategy results
- `simulation/strategy_configs.py` - Strategy definitions
- `config/agent_config.py` - SHADOW_STRATEGIES list

**Timeline:** Days 11-16

---

#### Task 4.4: Optimization Roadmap Validation
**Objective:** Assess feasibility of 4-week plan to reach 60-65% win rate

**Activities:**
1. Current performance baseline:
   - Actual win rate: 56-60% (validate with data)
   - Target: 60-65%
   - Gap: +4-9 percentage points needed

2. Week 1 progress (per-agent tracking):
   - Is per-agent tracking implemented? (Task 4.1 answers this)
   - Impact: Can we get +2-3% by disabling bad agents?
   - Estimate: Conservative 1-2%, Optimistic 3-5%

3. Week 2 projection (selective trading):
   - Shadow strategy: `ultra_selective` (0.80/0.70 thresholds)
   - Does higher threshold → higher win rate?
   - Trade-off: Fewer trades (5-10/day) vs better quality
   - Estimate: +2-4% win rate, -50% trade volume

4. Week 3 projection (Kelly sizing):
   - Shadow strategy: `kelly_sizing`
   - Does Kelly improve ROI? (vs Dr. Chen's analysis)
   - Estimate: +10-20% ROI (not win rate, but risk-adjusted return)

5. Week 4 projection (automation):
   - Auto-promotion of top shadow strategy
   - Continuous optimization infrastructure
   - Estimate: Sustains improvements, prevents degradation

6. Cumulative impact model:
   - If Week 1 = +2%, Week 2 = +3%, Week 3 = +1% (Kelly not WR)
   - Cumulative: 56% → 58% → 61% → 61%
   - Does this reach 60-65% target?

7. Alternative paths:
   - What if ML model deployed? (67% test accuracy)
   - What if contrarian re-enabled in choppy regime only?
   - What if new agents added (OrderBook, FundingRate)?

**Deliverables:**
- `reports/vic_ramanujan/roadmap_validation.md` - Feasibility analysis
- `reports/vic_ramanujan/impact_model.csv` - Week-by-week projections
- `reports/vic_ramanujan/alternative_paths.md` - Other optimization routes
- `reports/vic_ramanujan/timeline_recommendation.md` - Realistic timeline
- `reports/vic_ramanujan/success_probability.md` - Monte Carlo: Prob of hitting 60-65%

**Success Criteria:**
- Realistic impact estimates per optimization lever
- Probability of reaching 60-65% calculated (Monte Carlo, 10k trials)
- Alternative paths identified if primary roadmap insufficient
- Revised timeline if 4 weeks unrealistic

**Data Sources:**
- `docs/PRD-strategic.md` - 4-week optimization roadmap
- Shadow strategy results (all tasks above)
- Historical improvement rates (if available)

**Timeline:** Days 17-21

---

### Dependencies
- **Upstream:** Needs agent voting data from Dr. Nakamoto, statistical validation from Dr. Chen
- **Downstream:** Strategy recommendations inform final deployment (Prof. Nash's strategic synthesis)

### Risk Mitigation
- **Risk:** Shadow strategy sample sizes too small for significance
  - **Mitigation:** Extend observation period, use bootstrap confidence intervals
- **Risk:** ML model files not accessible
  - **Mitigation:** Focus on shadow strategy `ml_random_forest_*` results instead

---

## RESEARCHER #5: Colonel Rita "The Guardian" Stevens - Risk Management Architect

### Research Domain
**Risk control validation, drawdown protection, and position limit enforcement**

### Primary Research Question
**Are the risk controls mathematically sound and operationally reliable?**

### Tasks

#### Task 5.1: Drawdown Protection Audit
**Objective:** Validate 30% drawdown halt mechanism

**Activities:**
1. Drawdown calculation review:
   - Code audit: `bot/momentum_bot_v12.py` → Guardian.check_kill_switch()
   - Formula: `(peak_balance - current_balance) / peak_balance`
   - Is this correct? (Should use realized cash, not unrealized positions)

2. Peak balance tracking:
   - Jan 16 incident: $186 desync in peak_balance
   - Root cause: Does peak include unredeemed position values?
   - Review state management: `state/trading_state.json`
   - Is peak updated correctly on redemptions?

3. Historical drawdown analysis:
   - Extract balance history from logs
   - Plot: Balance over time with peak markers
   - Identify: Max historical drawdown (Jan 14: 95%)
   - Calculate: Time to recovery from drawdowns

4. False halt scenarios:
   - When did bot halt incorrectly? (Jan 16 after deposit)
   - Peak tracking issues causing premature halts
   - Recommendation: Reset logic or realized-only tracking

5. Stress testing:
   - Monte Carlo: 10-loss streak at current sizing
   - What % drawdown would occur?
   - Would 30% halt trigger appropriately?

6. Alternative drawdown metrics:
   - Should use underwater equity curve? (time below peak)
   - Should use rolling 30-day drawdown vs all-time peak?
   - Recommendation: Improve drawdown calculation

**Deliverables:**
- `reports/rita_stevens/drawdown_audit.md` - Calculation validation
- `reports/rita_stevens/drawdown_history.png` - Balance chart with peaks
- `reports/rita_stevens/false_halt_analysis.md` - Jan 16 incident report
- `reports/rita_stevens/stress_test_results.csv` - Monte Carlo simulations
- `reports/rita_stevens/drawdown_recommendations.md` - Improved tracking logic

**Success Criteria:**
- Drawdown calculation bugs identified (if any)
- Jan 16 desync root cause documented
- Stress test: Probability of hitting 30% in next 100 trades
- Actionable fix: Code changes to prevent false halts

**Data Sources:**
- `bot/momentum_bot_v12.py` - Guardian class code
- `state/trading_state.json` - Peak balance tracking
- `bot.log` - Balance history and halt events

**Timeline:** Days 1-4

---

#### Task 5.2: Position Sizing Validation
**Objective:** Verify tiered sizing math and enforcement

**Activities:**
1. Tiered sizing audit:
   - Code review: `agents/risk_agent.py` → calculate_position_size()
   - Current tiers:
     ```python
     (30, 0.15),     # < $30: 15%
     (75, 0.10),     # $30-75: 10%
     (150, 0.07),    # $75-150: 7%
     (inf, 0.05),    # > $150: 5%
     ```
   - Are percentages correct? (Cross-check with Dr. Chen's Kelly analysis)

2. Mode multipliers validation:
   - Recovery mode reduces sizing: normal=1.0, conservative=0.8, defensive=0.65, recovery=0.5
   - Are these enforced correctly?
   - Parse logs: Verify actual position sizes match calculated

3. Absolute limits enforcement:
   - Max: $15 per trade
   - Min: $1.10 (minimum bet)
   - Are these hard limits respected? (grep bot.log for violations)

4. Edge cases:
   - What if balance = $29.99? (tier boundary)
   - What if mode = recovery and tier = 15%? (0.5 × 0.15 = 7.5%)
   - Test: Position size calculator with edge cases

5. Historical position size distribution:
   - Extract actual position sizes from logs
   - Plot: Distribution (should cluster at tier limits)
   - Identify: Outliers (violating limits)

**Deliverables:**
- `reports/rita_stevens/position_sizing_audit.md` - Code validation
- `reports/rita_stevens/position_size_distribution.png` - Histogram
- `reports/rita_stevens/edge_case_tests.csv` - Boundary condition results
- `reports/rita_stevens/sizing_violations.md` - Any limit breaches
- `reports/rita_stevens/sizing_recommendations.md` - Improvements (if needed)

**Success Criteria:**
- All position sizes from logs verified against tiers
- Zero violations found (OR violations documented with fix)
- Edge cases tested (≥10 scenarios)
- Code changes proposed if bugs found

**Data Sources:**
- `agents/risk_agent.py` - Position sizing code
- `bot.log` - Actual position sizes
- `state/trading_state.json` - Current balance and mode

**Timeline:** Days 5-7

---

#### Task 5.3: Correlation & Position Limits
**Objective:** Validate position count and directional exposure limits

**Activities:**
1. Position limit enforcement:
   - Max total positions: 4 (1 per crypto)
   - Max same direction: 3 (e.g., 3 Up, 1 Down allowed)
   - Max directional exposure: 8% of balance
   - Code audit: `agents/risk_agent.py` → check_correlation_limits()

2. Violation detection:
   - Parse logs for "BLOCKED: Position limit" messages
   - Count: How many trades rejected due to limits?
   - Were limits correct? (or false positives)

3. Position tracking accuracy:
   - Code review: How does bot track open positions?
   - Uses: Polymarket Data API → `/positions` endpoint
   - Issue: Does bot see positions immediately after order?
   - Or latency causes double-entry? (place 2 BTC trades before API updates)

4. Directional exposure calculation:
   - Example: 3 Up positions at $5 each = $15 exposure
   - 8% of $200 balance = $16 max
   - Is this calculation correct? (net exposure or gross?)

5. Crypto correlation analysis:
   - BTC/ETH/SOL/XRP often move together
   - Does 1-per-crypto limit prevent correlated losses?
   - Or should limit be 1 total crypto position? (stricter)

6. Stress test:
   - Simulate: 4 simultaneous positions, all same direction, all lose
   - Impact on balance: -20% to -30% drawdown risk
   - Is this acceptable? (30% halt would trigger)

**Deliverables:**
- `reports/rita_stevens/position_limits_audit.md` - Code validation
- `reports/rita_stevens/limit_violations.csv` - Rejected trades analysis
- `reports/rita_stevens/position_tracking.md` - API latency issues (if any)
- `reports/rita_stevens/crypto_correlation.png` - BTC/ETH/SOL/XRP correlation matrix
- `reports/rita_stevens/stress_test_4positions.csv` - Worst-case scenario
- `reports/rita_stevens/limit_recommendations.md` - Tighten/loosen limits?

**Success Criteria:**
- All position limits verified as enforced
- API latency issues documented (if any)
- Correlation analysis: Quantify simultaneous loss risk
- Recommendation: Keep current limits OR adjust (with rationale)

**Data Sources:**
- `agents/risk_agent.py` - Limit enforcement code
- `bot.log` - Blocked trades and position counts
- Polymarket Data API - Position snapshots
- Exchange APIs - Crypto price correlation data

**Timeline:** Days 8-11

---

#### Task 5.4: Daily Loss Limits & Emergency Stops
**Objective:** Validate daily loss tracking and halt mechanisms

**Activities:**
1. Daily loss limit audit:
   - Code review: `bot/momentum_bot_v12.py` → Guardian class
   - Limits: $30 OR 20% of balance (whichever hit first)
   - Calculation: `day_start_balance - current_balance`
   - Reset: Daily at midnight? Or rolling 24h?

2. Historical daily loss events:
   - Jan 14: Lost $149.54 in ~12 hours (did daily limit trigger?)
   - If not, why? (limit too high? or not implemented?)
   - Parse logs for "HALTED: Daily loss" messages

3. Edge cases:
   - What if balance increases during day (winning trades)?
   - Does `day_start_balance` update? (should not until next day)
   - What if deposit made mid-day? (affects 20% calculation)

4. Recovery from halt:
   - After daily loss limit hit, when does bot resume?
   - Automatic at midnight? Or manual restart?
   - Code review: Halt recovery logic

5. Emergency kill switch:
   - Is there a manual "STOP EVERYTHING" command?
   - Remote VPS access: `systemctl stop polymarket-bot`
   - Documented procedure in `docs/DEPLOYMENT.md`?

6. Comparison to exchange circuit breakers:
   - Stock exchanges halt trading after 7%/13%/20% drops
   - Is bot's 20-30% halt appropriate for binary options?
   - Or should be tighter? (10% daily, 20% drawdown)

**Deliverables:**
- `reports/rita_stevens/daily_limit_audit.md` - Code and logic validation
- `reports/rita_stevens/jan14_loss_analysis.md` - Why didn't limit trigger?
- `reports/rita_stevens/halt_recovery.md` - Resume procedures
- `reports/rita_stevens/emergency_procedures.md` - Kill switch documentation
- `reports/rita_stevens/limit_comparison.md` - Industry benchmarks
- `reports/rita_stevens/daily_limit_recommendations.md` - Tighten/adjust limits

**Success Criteria:**
- Daily loss limit calculation verified
- Jan 14 incident explained (limit too high OR bug)
- Emergency procedures documented
- Recommendation: Adjust daily limits (with rationale)

**Data Sources:**
- `bot/momentum_bot_v12.py` - Guardian class
- `state/trading_state.json` - Day start balance
- `bot.log` - Jan 14 loss sequence
- Industry research: Exchange circuit breaker standards

**Timeline:** Days 12-15

---

### Dependencies
- **Upstream:** Needs drawdown history from Dr. Chen, position tracking from Dmitri Volkov
- **Downstream:** Risk validation informs final deployment decision (Prof. Nash)

### Risk Mitigation
- **Risk:** Jan 14 logs incomplete (12-hour loss period)
  - **Mitigation:** Reconstruct from state file snapshots
- **Risk:** Emergency procedures not documented
  - **Mitigation:** Create documentation as deliverable

---

## RESEARCHER #6: Dmitri "The Hammer" Volkov - System Reliability Engineer

### Research Domain
**State management, API reliability, VPS uptime, and operational resilience**

### Primary Research Question
**Can the system operate reliably 24/7 without data corruption or service failures?**

### Tasks

#### Task 6.1: State Management Audit
**Objective:** Validate `trading_state.json` persistence and correctness

**Activities:**
1. State file inspection:
   - Review: `state/trading_state.json`
   - Fields: balance, peak_balance, daily_pnl, mode, streaks, total_trades
   - Are all fields updated atomically? (or race conditions?)

2. State update code review:
   - Code: `bot/momentum_bot_v12.py` → save_state() function
   - Is file written atomically? (tmp file + rename for crash safety)
   - Are updates synchronized? (mutex/lock for concurrency)

3. Historical state corruption:
   - Jan 16: peak_balance desync ($186 error)
   - Root cause: Unredeemed positions counted in peak?
   - Parse logs: When did peak_balance change incorrectly?

4. State recovery scenarios:
   - What if `trading_state.json` deleted?
   - Does bot crash or create new state?
   - What if state file corrupted (invalid JSON)?
   - Error handling: Try/except blocks present?

5. Multi-process safety:
   - Is bot running as single process? (should be)
   - Could multiple instances write to state? (VPS safety)
   - Check: `systemctl status polymarket-bot` (1 process only)

6. State backup strategy:
   - Is state backed up? (Git ignore excludes `state/`)
   - Recommendation: Daily backups to S3 or VPS cron job
   - Recovery procedure documentation

**Deliverables:**
- `reports/dmitri_volkov/state_audit.md` - Correctness validation
- `reports/dmitri_volkov/jan16_desync_root_cause.md` - Incident analysis
- `reports/dmitri_volkov/state_recovery_tests.csv` - Failure scenario tests
- `reports/dmitri_volkov/atomic_write_analysis.md` - Crash safety review
- `reports/dmitri_volkov/backup_recommendation.md` - State backup strategy
- `reports/dmitri_volkov/state_fix_pr.md` - Code changes (if bugs found)

**Success Criteria:**
- Jan 16 desync root cause documented with code fix
- State corruption scenarios tested (≥5 scenarios)
- Atomic write verification (or fix implemented)
- Backup strategy documented

**Data Sources:**
- `state/trading_state.json` - Current state
- `bot/momentum_bot_v12.py` - State persistence code
- `bot.log` - State update events
- VPS filesystem - State file history (`ls -lht state/`)

**Timeline:** Days 1-4

---

#### Task 6.2: API Reliability & Circuit Breakers
**Objective:** Test external API failure handling

**Activities:**
1. API dependency mapping:
   - Polymarket Gamma API (market discovery)
   - Polymarket CLOB API (order placement)
   - Polymarket Data API (position tracking)
   - Binance/Kraken/Coinbase (price feeds)
   - Polygon RPC (balance checks, redemptions)

2. Timeout configuration audit:
   - Code review: Are all API calls wrapped in try/except?
   - Are timeouts set? (default: 10s in requests library)
   - Code: `requests.get(url, timeout=10)`
   - Are retries implemented? (or fail immediately)

3. Failure mode testing:
   - Simulate: Gamma API down (no markets found)
   - Does bot crash or skip cycle gracefully?
   - Simulate: CLOB API 429 rate limit
   - Does bot backoff or hammer API?
   - Simulate: Polygon RPC timeout
   - Does bot retry or fail trade?

4. Circuit breaker pattern:
   - Is circuit breaker implemented? (stop calling failed API)
   - Pattern: After 3 failures, wait 5 min before retry
   - Code review: Look for circuit breaker logic

5. Historical API failures:
   - Parse logs for "timeout", "connection error", "API error"
   - How often do APIs fail?
   - Does bot recover automatically?
   - Were any trades missed due to API failures?

6. Fallback mechanisms:
   - If Binance down, does bot use Kraken/Coinbase?
   - If Gamma API down, does bot use cached market list?
   - Are fallbacks implemented? (or single point of failure)

**Deliverables:**
- `reports/dmitri_volkov/api_dependency_map.md` - All external APIs
- `reports/dmitri_volkov/timeout_audit.md` - Configuration review
- `reports/dmitri_volkov/failure_mode_tests.csv` - Simulated failures
- `reports/dmitri_volkov/circuit_breaker_analysis.md` - Pattern detection
- `reports/dmitri_volkov/api_failure_history.csv` - Log analysis
- `reports/dmitri_volkov/resilience_recommendations.md` - Improve fault tolerance

**Success Criteria:**
- All API calls verified with timeouts
- ≥5 failure scenarios tested
- Circuit breaker implemented OR added as recommendation
- Historical failure rate quantified

**Data Sources:**
- `bot/momentum_bot_v12.py` - API call code
- `bot.log` - API error messages
- VPS: `curl` tests to external APIs (check reachability)

**Timeline:** Days 5-8

---

#### Task 6.3: VPS Operational Health Check
**Objective:** Assess production environment stability

**Activities:**
1. Service monitoring:
   - Check: `systemctl status polymarket-bot`
   - Uptime: How long has service been running?
   - Restarts: How many times restarted in Jan 2026?
   - Parse: `journalctl -u polymarket-bot` for crash logs

2. Resource utilization:
   - CPU: `top` or `htop` snapshot during trading
   - Memory: Is bot leaking memory over time?
   - Disk: Is `bot.log` filling disk? (log rotation configured?)
   - Network: Bandwidth usage (API calls per minute)

3. Log management:
   - Current log size: `ls -lh bot.log`
   - Log rotation: Is logrotate configured?
   - Retention: How many days of logs kept?
   - Recommendation: Daily rotation, 30-day retention

4. Security audit:
   - SSH key access: `~/.ssh/polymarket_vultr`
   - Is private key encrypted?
   - `.env` file permissions: `chmod 600` verified?
   - Are credentials exposed in logs? (grep for POLYMARKET_PRIVATE_KEY)

5. Deployment process:
   - Review: `scripts/deploy.sh`
   - Is deployment idempotent? (safe to run multiple times)
   - Does deployment cause downtime? (service restart)
   - Blue/green deployment possible?

6. Monitoring & alerts:
   - Are alerts configured? (email, Telegram, etc.)
   - What triggers alerts? (bot halt, consecutive losses, balance drop)
   - Manual check: `tail -f bot.log` only way to monitor?
   - Recommendation: Prometheus + Grafana or Datadog

**Deliverables:**
- `reports/dmitri_volkov/vps_health_report.md` - Uptime and resource usage
- `reports/dmitri_volkov/service_restart_history.csv` - Crash analysis
- `reports/dmitri_volkov/log_management_audit.md` - Rotation and retention
- `reports/dmitri_volkov/security_audit.md` - Credential safety
- `reports/dmitri_volkov/deployment_process.md` - Deploy.sh review
- `reports/dmitri_volkov/monitoring_recommendations.md` - Alerting setup

**Success Criteria:**
- VPS uptime documented (target: >99% in Jan 2026)
- Resource leaks identified (if any)
- Security vulnerabilities found (if any) and mitigated
- Monitoring/alerting plan proposed

**Data Sources:**
- VPS: `ssh root@216.238.85.11`
- `systemctl status polymarket-bot`
- `journalctl -u polymarket-bot`
- `bot.log` and disk usage
- `scripts/deploy.sh`

**Timeline:** Days 9-12

---

#### Task 6.4: Data Integrity & Database Health
**Objective:** Validate SQLite database and shadow trading logs

**Activities:**
1. Database inspection:
   - File: `simulation/trade_journal.db`
   - Size: How large is DB? (performance concern if >1GB)
   - Schema review: `sqlite3 trade_journal.db .schema`
   - Tables: strategies, decisions, trades, outcomes, agent_votes, performance

2. Data consistency checks:
   - Foreign key integrity: Are all trade_ids valid?
   - Outcome resolution: Do all trades have outcomes? (or pending?)
   - Duplicate detection: Any duplicate trade entries?
   - Orphan records: Agent votes without corresponding trades?

3. Query performance:
   - Test queries: `SELECT * FROM performance ORDER BY total_pnl DESC`
   - Response time: <100ms? Or slow (needs indexing)?
   - Indexing audit: Are indexes on key fields? (strategy, timestamp, outcome)

4. Shadow trading logging:
   - Code review: `simulation/orchestrator.py` → log_decision()
   - Are all 27 shadow strategies logging correctly?
   - Logs mention: "Shadow trading not logging decisions"
   - Debug: Why aren't decisions logged?

5. Backup & recovery:
   - Is `trade_journal.db` backed up?
   - Manual backup: `scp root@216.238.85.11:/opt/.../trade_journal.db ./backup/`
   - Recovery test: Can DB be restored from backup?

6. Database corruption scenarios:
   - Run: `sqlite3 trade_journal.db "PRAGMA integrity_check;"`
   - Result: Should return "ok"
   - If corrupted: Recovery plan (rebuild from logs)

**Deliverables:**
- `reports/dmitri_volkov/database_health.md` - Schema and integrity report
- `reports/dmitri_volkov/consistency_check_results.csv` - Data validation
- `reports/dmitri_volkov/query_performance.md` - Indexing recommendations
- `reports/dmitri_volkov/shadow_logging_debug.md` - Why decisions not logged?
- `reports/dmitri_volkov/database_backup_plan.md` - Backup strategy
- `reports/dmitri_volkov/integrity_check.txt` - PRAGMA results

**Success Criteria:**
- PRAGMA integrity_check passes
- All shadow strategies confirmed logging (or bug identified)
- Query performance <100ms for key operations
- Backup/recovery plan documented

**Data Sources:**
- `simulation/trade_journal.db` - SQLite database
- `simulation/orchestrator.py` - Logging code
- VPS: Database file size and permissions
- Logs: Shadow trading mentions in `bot.log`

**Timeline:** Days 13-16

---

### Dependencies
- **Upstream:** Independent (provides clean infrastructure for other researchers)
- **Downstream:** Reliable system required for all other research

### Risk Mitigation
- **Risk:** VPS access issues during audit
  - **Mitigation:** Work with cached logs and local state files
- **Risk:** Database corruption during integrity check
  - **Mitigation:** Backup DB before running tests

---

## RESEARCHER #7: Dr. Kenji Nakamoto - Data Forensics Specialist

### Research Domain
**Data integrity validation, overfitting detection, and statistical anomaly identification**

### Primary Research Question
**Is the historical performance data trustworthy, or are there signs of data leakage, p-hacking, or survivorship bias?**

### Tasks

#### Task 7.1: Data Provenance & Integrity Audit
**Objective:** Validate that all performance data is genuine and unmanipulated

**Activities:**
1. Trade log completeness:
   - Parse `bot.log` for all trades
   - Expected fields: timestamp, crypto, direction, entry, shares, outcome
   - Missing data: Are any trades incomplete? (no outcome recorded)
   - Corrupted entries: JSON parse errors, malformed logs

2. Timestamp consistency:
   - Are timestamps monotonic? (no time travel)
   - Are epoch timestamps valid? (aligned to 15-min boundaries)
   - Are gaps suspicious? (bot offline or data deleted?)

3. Balance reconciliation:
   - Trace balance from initial deposit → current
   - Sum: Starting balance + total P&L = current balance?
   - Discrepancies: Missing deposits/withdrawals? Unredeemed positions?

4. Duplicate detection:
   - Same trade logged twice? (API retry causing double entry)
   - Same outcome resolved twice? (redemption bug)
   - Hash trades: timestamp + crypto + direction (detect exact duplicates)

5. Chain of custody:
   - When was data collected? (Jan 2026 only? Or historical?)
   - Who has access to VPS? (could data be modified?)
   - Git history: Any suspicious commits to state files?

6. On-chain verification:
   - Sample 10 trades: Verify on Polygon blockchain
   - Use Polygonscan to confirm transactions
   - Do on-chain outcomes match bot logs?

**Deliverables:**
- `reports/kenji_nakamoto/data_integrity_report.md` - Completeness audit
- `reports/kenji_nakamoto/missing_data.csv` - Incomplete trades
- `reports/kenji_nakamoto/balance_reconciliation.md` - Cash flow validation
- `reports/kenji_nakamoto/duplicate_analysis.csv` - Duplicate trades (if any)
- `reports/kenji_nakamoto/on_chain_verification.md` - Blockchain cross-check
- `reports/kenji_nakamoto/data_provenance.md` - Chain of custody

**Success Criteria:**
- ≥95% of trades have complete data
- Balance reconciliation matches within $1
- Zero duplicates found (OR duplicates explained)
- On-chain verification: 10/10 trades match logs

**Data Sources:**
- `bot.log` - All trading activity
- `state/trading_state.json` - Balance checkpoints
- Polygon blockchain (Polygonscan API)
- Git history: `git log state/`

**Timeline:** Days 1-4

---

#### Task 7.2: Survivorship Bias Detection
**Objective:** Identify if performance cherry-picks successful periods

**Activities:**
1. Historical performance claims:
   - Documentation: "56-60% win rate"
   - Time period: What dates does this cover?
   - Is this lifetime? Or selected time window?

2. Period selection bias:
   - If only Jan 13-15 data shown (recovery period), biased
   - If Jan 14 loss day excluded, survivorship bias
   - Test: Does win rate change if including ALL days?

3. Strategy evolution tracking:
   - When did v12.1 start? (Jan 13 per docs)
   - Are v11 losses excluded from v12 metrics?
   - Should compare: v12 only vs all-time

4. Shadow strategy filtering:
   - Are only "winning" shadow strategies shown?
   - Test: Query DB for ALL shadow strategies (including losers)
   - Are strategies removed from config after poor performance?

5. Backtest vs forward test:
   - Is performance from backtest (historical data)?
   - Or live trading (forward test)?
   - Backtest always optimistic (overfitting risk)

6. Deleted data detection:
   - Git history: Were trades deleted from logs?
   - Logs mention: "Trade history reset" or similar?
   - VPS: Old log files in `/var/log` or rotated?

**Deliverables:**
- `reports/kenji_nakamoto/survivorship_bias_report.md` - Bias detection
- `reports/kenji_nakamoto/time_period_analysis.csv` - Performance per period
- `reports/kenji_nakamoto/strategy_evolution.md` - v11 vs v12 vs v12.1
- `reports/kenji_nakamoto/shadow_strategy_filter.md` - Missing strategies?
- `reports/kenji_nakamoto/backtest_vs_live.md` - Data source classification
- `reports/kenji_nakamoto/deleted_data_audit.md` - Git + log inspection

**Success Criteria:**
- All time periods accounted for (no missing days)
- v12 performance compared to v11 (apple-to-apple)
- All shadow strategies documented (not just winners)
- Confidence: Data is NOT cherry-picked

**Data Sources:**
- `CLAUDE.md` - Performance claims ("56-60% win rate")
- `bot.log` - All historical trades
- `simulation/trade_journal.db` - Shadow strategies
- Git history: `git log --all --full-history state/ bot.log`

**Timeline:** Days 5-8

---

#### Task 7.3: P-Hacking & Overfitting Detection
**Objective:** Identify if strategy was over-optimized to historical data

**Activities:**
1. Parameter sensitivity analysis:
   - Config: CONSENSUS_THRESHOLD = 0.75, MIN_CONFIDENCE = 0.60
   - Test: Performance at 0.70, 0.75, 0.80 (is 0.75 cherry-picked?)
   - Plot: Win rate vs threshold (smooth curve or spike at 0.75?)

2. Multiple testing correction:
   - How many parameter combinations tested? (27 shadow strategies)
   - With 27 tests, expect 1-2 false positives by chance (p < 0.05)
   - Bonferroni correction: Adjust significance threshold

3. In-sample vs out-of-sample:
   - ML model: 67.3% test accuracy claim
   - Was test set truly held out? Or used for tuning?
   - Recommendation: Test on post-Jan-15 data (unseen)

4. Feature engineering archaeology:
   - Review: ML training code (if available)
   - Features: Price, RSI, agent votes, etc.
   - Are features created based on hindsight? (data leakage)
   - Example: Using future price as feature (obvious leakage)

5. Walk-forward validation:
   - Did strategy retrain on new data? (adaptive)
   - Or fixed parameters since Jan 1? (static)
   - Walk-forward: Train on Month 1, test on Month 2, retrain on Month 1-2, test on Month 3
   - If not done, overfitting risk

6. Agent weight optimization:
   - Current: All agents 1.0 weight
   - Shadow: `momentum_focused` (TechAgent 1.5x)
   - Were weights grid-searched? (overfitting risk)
   - Test: Random weights perform similarly? (no real edge)

**Deliverables:**
- `reports/kenji_nakamoto/parameter_sensitivity.ipynb` - Threshold sweep
- `reports/kenji_nakamoto/multiple_testing.md` - Bonferroni correction
- `reports/kenji_nakamoto/in_sample_vs_out.md` - ML model validation
- `reports/kenji_nakamoto/feature_leakage_audit.md` - ML feature review
- `reports/kenji_nakamoto/walk_forward_test.csv` - Out-of-sample validation
- `reports/kenji_nakamoto/overfitting_verdict.md` - Overall assessment

**Success Criteria:**
- Parameter sensitivity shows smooth curve (not spike at current value)
- Bonferroni-corrected p-values still significant (p < 0.002)
- No feature leakage found in ML model
- Walk-forward test: Performance holds out-of-sample

**Data Sources:**
- `config/agent_config.py` - Current parameters
- `simulation/trade_journal.db` - Shadow strategy results
- `ml_training/` (if exists) - ML training code
- Historical logs - Parameter changes over time

**Timeline:** Days 9-13

---

#### Task 7.4: Statistical Anomaly Detection
**Objective:** Identify suspicious patterns in trading data

**Activities:**
1. Win rate clustering:
   - Plot: Rolling 20-trade win rate over time
   - Expected: Random walk around true WR (e.g., 58%)
   - Anomaly: Sudden jump (e.g., 40% → 70%) without strategy change

2. Outcome distribution:
   - Expected: Bernoulli distribution (binary outcomes)
   - Test: Chi-square goodness of fit
   - Anomaly: Too many wins clustered together (not independent)

3. Entry price anomalies:
   - Expected: Distribution matches market opportunities
   - Anomaly: All entries exactly $0.25 (suspicious uniformity)
   - Anomaly: Impossible prices (e.g., $1.50 entry for binary option)

4. Temporal patterns:
   - Are wins/losses evenly distributed across hours?
   - Anomaly: Only wins during US market hours (suspicious)
   - Test: ANOVA - performance by hour of day

5. Crypto-specific anomalies:
   - Does BTC have 80% win rate but ETH 40%? (suspicious)
   - Test: Chi-square test - WR by crypto
   - Expected: Similar WR across cryptos (strategy agnostic)

6. Shadow strategy anomalies:
   - Is `random_baseline` (coin flip) beating default? (impossible)
   - Are inverse strategies winning? (agents anti-predictive)
   - Test: Sanity checks on shadow results

7. Outlier detection:
   - Identify trades with extreme P&L (e.g., +$50 or -$50)
   - Are these legitimate? Or data errors?
   - Review: Top 10 wins and top 10 losses

**Deliverables:**
- `reports/kenji_nakamoto/win_rate_clustering.png` - Rolling WR chart
- `reports/kenji_nakamoto/outcome_distribution.md` - Chi-square test
- `reports/kenji_nakamoto/entry_price_anomalies.csv` - Suspicious entries
- `reports/kenji_nakamoto/temporal_analysis.md` - Performance by hour
- `reports/kenji_nakamoto/crypto_anomalies.csv` - WR by asset
- `reports/kenji_nakamoto/shadow_sanity_checks.md` - Impossible results
- `reports/kenji_nakamoto/outlier_trades.csv` - Extreme P&L events
- `reports/kenji_nakamoto/anomaly_summary.md` - Overall findings

**Success Criteria:**
- Chi-square tests pass (p > 0.05 = no anomaly)
- No impossible prices found
- Performance consistent across hours and cryptos
- Random baseline does NOT beat default (sanity check)
- Outliers explained (legitimate or removed)

**Data Sources:**
- `bot.log` - All trades
- `simulation/trade_journal.db` - Shadow strategies
- Statistical tests: Python scipy.stats

**Timeline:** Days 14-18

---

### Dependencies
- **Upstream:** Independent (provides clean data for all other researchers)
- **Downstream:** All researchers depend on data integrity validation

### Risk Mitigation
- **Risk:** On-chain verification blocked by RPC rate limits
  - **Mitigation:** Sample smaller set (5 trades instead of 10)
- **Risk:** ML training code not available
  - **Mitigation:** Focus on shadow strategy `ml_random_forest_*` results

---

## RESEARCHER #8: Prof. Eleanor Nash - Game Theory Economist

### Research Domain
**Strategic synthesis, multi-epoch dynamics, and competitive equilibria**

### Primary Research Question
**What is the optimal long-term strategy given market maker dynamics and regime changes?**

### Tasks

#### Task 8.1: Multi-Epoch Strategic Analysis
**Objective:** Evaluate strategy performance across multiple epochs

**Activities:**
1. Epoch sequence patterns:
   - Do winning epochs predict next epoch outcome?
   - Autocorrelation test: Is Win_t correlated with Win_(t-1)?
   - Result: Independent epochs (expected) or momentum?

2. Future window trading validation:
   - v12.1 feature: "Look ahead 2-3 windows for pricing anomalies"
   - Code review: `bot/momentum_bot_v12.py` → FutureWindowTrader
   - Does this create strategic edge? Or data leakage?

3. Market maker response:
   - If bot consistently wins early momentum (15-300s), do MMs adapt?
   - Evidence: Entry prices increasing over time (MMs front-run bot)
   - Test: Correlation between bot activity and market prices

4. Contrarian equilibrium:
   - Why does contrarian work? (market overreaction)
   - Game theory: If everyone fades >70%, does threshold shift to >80%?
   - Nash equilibrium: Where do contrarians and momentum traders balance?

5. Optimal timing windows:
   - Early: High variance, low efficiency (fees high)
   - Late: Low variance, high efficiency (fees low, but less edge)
   - Game theory: Which window has competitive advantage?

**Deliverables:**
- `reports/eleanor_nash/epoch_autocorrelation.md` - Independence testing
- `reports/eleanor_nash/future_window_analysis.md` - Strategic vs leakage
- `reports/eleanor_nash/market_maker_adaptation.png` - Price evolution over time
- `reports/eleanor_nash/contrarian_equilibrium.md` - Nash equilibrium analysis
- `reports/eleanor_nash/timing_strategy.md` - Optimal entry windows
- `reports/eleanor_nash/multi_epoch_recommendations.md` - Strategic adjustments

**Success Criteria:**
- Autocorrelation test: Independent epochs (p > 0.05)
- Future window: Edge vs leakage determination
- Market maker adaptation: Evidence found OR ruled out
- Nash equilibrium: Contrarian threshold optimized
- Timing strategy: Clear recommendation (early/mid/late)

**Data Sources:**
- `bot.log` - Sequential epoch outcomes
- `bot/momentum_bot_v12.py` - Future window code
- Polymarket API - Historical market prices
- Game theory literature - Nash equilibrium models

**Timeline:** Days 1-6

---

#### Task 8.2: Regime-Based Strategy Switching
**Objective:** Develop regime-conditional trading rules

**Activities:**
1. Regime classification validation:
   - RegimeAgent classifies: bull_momentum, bear_momentum, sideways, volatile
   - Code: `agents/regime_agent.py`
   - Are classifications accurate? (manual spot-check)

2. Strategy performance by regime:
   - Query DB: Win rate per strategy per regime
   - Example: Does `contrarian_focused` win in sideways?
   - Example: Does `momentum_focused` win in bull/bear?

3. Regime transition matrix:
   - How often: bull → sideways → bear → bull?
   - Average regime duration: 1 hour? 1 day? 1 week?
   - Markov chain: Predict next regime from current

4. Adaptive strategy selection:
   - Current: Agents use regime multipliers (adjust weights)
   - Alternative: Switch strategies entirely
   - Example: If sideways → use `contrarian_focused`
   - Example: If bull → use `momentum_focused`

5. Jan 14 incident analysis:
   - Regime was: Weak uptrend (trend score 0.70-1.00)
   - Bot traded: 96.5% UP (failed due to choppy reversals)
   - Root cause: Regime detection too coarse? (should have been "choppy")
   - Recommendation: Finer regime granularity

6. Regime prediction:
   - Can bot predict regime 1 epoch ahead?
   - Features: Recent volatility, trend slope, RSI divergence
   - If predictable: Pre-adjust strategy before regime shifts

**Deliverables:**
- `reports/eleanor_nash/regime_validation.md` - Classification accuracy
- `reports/eleanor_nash/strategy_by_regime.csv` - Performance matrix
- `reports/eleanor_nash/regime_transitions.png` - Markov chain
- `reports/eleanor_nash/adaptive_switching.ipynb` - Simulation of strategy switching
- `reports/eleanor_nash/jan14_regime_analysis.md` - Incident post-mortem
- `reports/eleanor_nash/regime_prediction.md` - Forecast feasibility
- `reports/eleanor_nash/regime_recommendations.md` - Improved classification

**Success Criteria:**
- Regime classification accuracy >70% (manual validation)
- Strategy performance significantly different across regimes (ANOVA p < 0.05)
- Regime transition matrix constructed (Markov chain)
- Adaptive switching simulated: Beats static strategy?
- Jan 14 incident: Regime misclassification confirmed
- Regime prediction: Feasibility assessed (possible or not)

**Data Sources:**
- `agents/regime_agent.py` - Classification code
- `simulation/trade_journal.db` - Strategy performance by regime
- `bot.log` - Jan 14 incident timeline
- Exchange APIs - Historical volatility and trend data

**Timeline:** Days 7-13

---

#### Task 8.3: Competitive Strategy Analysis
**Objective:** Evaluate bot's strategy vs other market participants

**Activities:**
1. Market participant profiling:
   - Who trades Polymarket 15-min binary options?
   - Retail traders (low volume, random)
   - Bots (high volume, systematic)
   - Market makers (liquidity providers)

2. Volume analysis:
   - Extract: Polymarket market volume over time
   - Bot trades: $1.10 - $15 per trade
   - Market volume: $1,000 - $10,000 per epoch?
   - Bot impact: <1% of market (price taker)

3. Contrarian vs momentum equilibrium:
   - If 90% of traders are momentum (buy rising prices), contrarian wins
   - If 90% of traders are contrarian (fade extremes), momentum wins
   - Current balance: What's the market composition?
   - Bot's role: Should be contrarian or momentum?

4. Information asymmetry:
   - Does bot have information edge? (multi-exchange feeds)
   - Or just faster execution? (2s scan interval)
   - Or better risk management? (position sizing)
   - Sustainable edge: What's the source?

5. Market efficiency:
   - Are Polymarket prices efficient? (reflect true probabilities)
   - Inefficiency sources: Overreaction, underreaction, liquidity gaps
   - Bot's exploit: Which inefficiency?

6. Long-term viability:
   - If bot is profitable, will others copy strategy?
   - Competitive moat: What prevents copycats?
   - Evolution: How should strategy adapt as market matures?

**Deliverables:**
- `reports/eleanor_nash/market_participants.md` - Profiling analysis
- `reports/eleanor_nash/volume_analysis.csv` - Bot vs market volume
- `reports/eleanor_nash/contrarian_momentum_balance.md` - Market composition
- `reports/eleanor_nash/information_edge.md` - Source of bot advantage
- `reports/eleanor_nash/market_efficiency.md` - Inefficiency exploitation
- `reports/eleanor_nash/competitive_moat.md` - Long-term viability
- `reports/eleanor_nash/evolution_strategy.md` - Adaptation roadmap

**Success Criteria:**
- Market participant types identified
- Bot volume <5% of market (not moving prices)
- Information edge source documented
- Market inefficiency quantified (e.g., 5% overreaction)
- Competitive moat assessed (strong/weak/none)
- Evolution roadmap: Next 6-12 months

**Data Sources:**
- Polymarket API - Market volume data
- Polymarket CLOB - Order book depth
- Academic research - Prediction market efficiency
- Competitor analysis - Other trading bots (if detectable)

**Timeline:** Days 14-20

---

#### Task 8.4: Strategic Recommendations & Final Synthesis
**Objective:** Integrate all research findings into actionable strategy

**Activities:**
1. Research synthesis:
   - Compile findings from all 7 researchers
   - Key insights: What did we learn?
   - Contradictions: Any conflicting recommendations?

2. Optimization priority ranking:
   - Which improvements have highest ROI?
   - Example: Disabling bad agents (+2% WR) vs ML deployment (risk)
   - Rank: Impact vs implementation effort

3. 60-65% win rate feasibility:
   - Based on all research: Is this achievable?
   - Current: 56-60%
   - Gap: +4-9 percentage points
   - Path: Concrete steps to close gap

4. Risk-adjusted strategy:
   - Not just win rate, but Sharpe ratio
   - Accept lower win rate if volatility decreases?
   - Trade-off: Frequency vs quality

5. Deployment roadmap:
   - Week 1: Quick wins (disable bad agents, raise thresholds)
   - Week 2-3: Medium effort (strategy switching, Kelly sizing)
   - Week 4+: Long-term (ML retraining, new agents)

6. Exit criteria:
   - When should bot be shut down? (unrecoverable loss)
   - When should bot pause? (regime shift detected)
   - When should bot scale up? (consistent profitability)

7. Continuous improvement:
   - Weekly reviews: Per-agent performance
   - Monthly audits: Shadow strategy promotion
   - Quarterly: Full system evaluation (repeat this research)

8. Final report:
   - Executive summary (2 pages)
   - Detailed findings (50+ pages)
   - Appendices: All researcher deliverables

**Deliverables:**
- `reports/eleanor_nash/research_synthesis.md` - Integrated findings
- `reports/eleanor_nash/optimization_priorities.csv` - Ranked recommendations
- `reports/eleanor_nash/60_65_wr_roadmap.md` - Path to target win rate
- `reports/eleanor_nash/risk_adjusted_strategy.md` - Sharpe-optimized plan
- `reports/eleanor_nash/deployment_roadmap.md` - Implementation timeline
- `reports/eleanor_nash/exit_criteria.md` - When to stop/pause/scale
- `reports/eleanor_nash/continuous_improvement.md` - Ongoing optimization
- `reports/FINAL_REPORT.md` - **Comprehensive evaluation report**
- `reports/EXECUTIVE_SUMMARY.md` - **2-page summary for stakeholders**

**Success Criteria:**
- All 7 researchers' findings integrated
- Top 10 recommendations prioritized
- 60-65% WR roadmap: Realistic with probability estimate
- Deployment roadmap: Concrete milestones with owners
- Exit criteria: Clear triggers (quantitative)
- Final report: >50 pages, peer-reviewed by team
- Executive summary: 2 pages, non-technical language

**Data Sources:**
- All previous researcher deliverables
- Stakeholder interviews (system owner, VPS ops)
- Industry benchmarks (other prediction market bots)
- Academic research (binary options trading strategies)

**Timeline:** Days 21-28 (Final week)

---

### Dependencies
- **Upstream:** ALL 7 researchers (requires all findings)
- **Downstream:** Final deployment decision (stakeholder approval)

### Risk Mitigation
- **Risk:** Conflicting recommendations from researchers
  - **Mitigation:** Convene team meeting to resolve contradictions
- **Risk:** 60-65% WR roadmap not feasible
  - **Mitigation:** Provide alternative target (e.g., 58-60% with higher Sharpe)

---

## Timeline & Milestones

### Week 1 (Jan 16-22): Foundation Research
- **Days 1-4:** Data integrity (Kenji), State management (Dmitri), Drawdown audit (Rita)
- **Days 5-7:** Fee validation (Sarah), Entry price analysis (Jimmy), Recovery mode audit (Amara)
- **Deliverables:** Clean data, infrastructure validated, math foundation set

### Week 2 (Jan 23-29): Performance Analysis
- **Days 8-11:** Agent performance (Vic), Timing optimization (Jimmy), Position limits (Rita)
- **Days 12-14:** Statistical significance (Sarah), Contrarian validation (Jimmy), API reliability (Dmitri)
- **Deliverables:** Agent rankings, entry strategy, risk validation

### Week 3 (Jan 30 - Feb 5): Strategic Evaluation
- **Days 15-18:** ML model validation (Vic), Voting bias (Amara), Shadow tournament (Vic)
- **Days 19-21:** Database health (Dmitri), Overfitting detection (Kenji), Regime analysis (Eleanor)
- **Deliverables:** ML recommendation, strategy rankings, regime switching

### Week 4 (Feb 6-13): Synthesis & Recommendations
- **Days 22-24:** Multi-epoch strategy (Eleanor), Competitive analysis (Eleanor)
- **Days 25-28:** Final synthesis (Eleanor), Executive report, Stakeholder presentation
- **Deliverables:** Final report, optimization roadmap, deployment plan

---

## Resource Requirements

### Access & Credentials
- VPS SSH: `root@216.238.85.11`
- Database: `simulation/trade_journal.db`
- Environment variables: `.env` file (wallet, API keys)
- Polygon RPC: For on-chain verification

### Tools & Software
- **Python 3.11+** - Analysis scripts
- **Jupyter Notebook** - Interactive analysis
- **SQLite** - Database queries
- **Git** - Version control and history analysis
- **SSH** - VPS access
- **curl/wget** - API testing

### Computational Resources
- Local development: MacBook Pro (sufficient)
- Optional: Cloud compute for Monte Carlo (10k+ trials)
- Storage: ~5GB for logs, DB backups, analysis artifacts

### Domain Expertise
- Each researcher brings specialized knowledge
- External validation: Peer review by trading experts
- Academic papers: Binary options, prediction markets

---

## Risk Assessment

### Data Availability Risks
- **Risk:** Jan 14 logs incomplete (12-hour loss period)
- **Mitigation:** Reconstruct from state file snapshots, on-chain data

### Technical Risks
- **Risk:** VPS access issues during research period
- **Mitigation:** Work with cached logs and local backups

### Analytical Risks
- **Risk:** Insufficient sample size for statistical significance
- **Mitigation:** Use shadow trading data (27 strategies × trades)

### Timeline Risks
- **Risk:** Research takes longer than 4 weeks
- **Mitigation:** Prioritize critical findings, defer nice-to-haves

### Resource Risks
- **Risk:** Researchers unavailable simultaneously
- **Mitigation:** Sequential dependencies managed, parallel work where possible

---

## Success Criteria

### Coverage
- ✅ All 8 research domains completed
- ✅ All 32 major tasks executed
- ✅ All deliverables submitted

### Quality
- ✅ Statistical significance achieved (p < 0.05)
- ✅ No data integrity issues found (OR issues documented with fixes)
- ✅ All code audits completed (vulnerabilities documented)

### Actionability
- ✅ ≥10 concrete recommendations provided
- ✅ Optimization roadmap validated (60-65% WR feasible OR alternative proposed)
- ✅ Deployment plan approved by stakeholders

### Impact
- ✅ Win rate improvement identified (quantified)
- ✅ Risk controls validated (OR improvements implemented)
- ✅ System reliability improved (bugs fixed)

---

## Deliverables Summary

### Reports (by Researcher)
1. **Dr. Sarah Chen:** 12 reports (fee validation, Kelly analysis, statistics, risk metrics)
2. **James Martinez:** 12 reports (entry analysis, timing, contrarian, liquidity)
3. **Dr. Amara Johnson:** 12 reports (recovery modes, streaks, voting bias, overconfidence)
4. **Victor Ramanujan:** 16 reports (agent performance, ML validation, shadow tournament, roadmap)
5. **Colonel Rita Stevens:** 16 reports (drawdown, position sizing, limits, daily loss)
6. **Dmitri Volkov:** 16 reports (state audit, API reliability, VPS health, database)
7. **Dr. Kenji Nakamoto:** 16 reports (data integrity, survivorship bias, p-hacking, anomalies)
8. **Prof. Eleanor Nash:** 20 reports (multi-epoch, regime switching, competitive strategy, synthesis)

**Total:** ~120 individual reports + 1 final comprehensive report

### Final Deliverables
- `reports/FINAL_REPORT.md` - Comprehensive 50+ page evaluation
- `reports/EXECUTIVE_SUMMARY.md` - 2-page stakeholder summary
- `reports/OPTIMIZATION_ROADMAP.md` - Actionable improvement plan
- `reports/DEPLOYMENT_PLAN.md` - Implementation timeline
- `reports/CODE_FIXES/` - Bug fixes and improvements
- `reports/RISK_ASSESSMENT.md` - Updated risk profile

---

## Approval & Sign-off

### Stakeholder Approval
- [ ] **System Owner:** Approved research scope and access
- [ ] **VPS Operations:** Granted SSH access and credentials
- [ ] **Strategy Team:** Aligned on success criteria

### Researcher Acceptance
- [ ] **Dr. Sarah Chen:** Accepted tasks and timeline
- [ ] **James Martinez:** Accepted tasks and timeline
- [ ] **Dr. Amara Johnson:** Accepted tasks and timeline
- [ ] **Victor Ramanujan:** Accepted tasks and timeline
- [ ] **Colonel Rita Stevens:** Accepted tasks and timeline
- [ ] **Dmitri Volkov:** Accepted tasks and timeline
- [ ] **Dr. Kenji Nakamoto:** Accepted tasks and timeline
- [ ] **Prof. Eleanor Nash:** Accepted tasks and timeline

### Lead Researcher Sign-off
- [ ] **Lead Researcher:** PRD complete and approved

---

## Next Steps

1. **IMMEDIATE:** Obtain stakeholder approval on this PRD
2. **Day 1:** Kick-off meeting with all 8 researchers
3. **Day 1:** Grant VPS access, database credentials, API keys
4. **Days 1-28:** Execute research plan per timeline
5. **Day 28:** Final report delivery and presentation

---

## Appendix: Task Dependencies Graph

```
Week 1: Foundation
├── Kenji (Data) ────────► (Clean data for all)
├── Dmitri (System) ─────► (Reliable infrastructure)
└── Rita (Drawdown) ─────► Sarah (Math)

Week 2: Analysis
├── Sarah (Math) ────────► Jimmy (Entry), Rita (Sizing)
├── Jimmy (Timing) ──────► Vic (Strategy)
└── Amara (Recovery) ────► Vic (Voting)

Week 3: Strategy
├── Vic (Agents) ────────► Eleanor (Regime)
├── Vic (ML) ────────────► Eleanor (Strategy)
└── Kenji (Overfitting) ─► Vic (Validation)

Week 4: Synthesis
└── All Researchers ─────► Eleanor (Final Report)
```

---

**END OF PRD**

**Status:** Ready for stakeholder review and approval.

**Contact:** Lead Researcher (Binary Trading Systems & Gambling Philosophy Expert)

**Date:** 2026-01-16
