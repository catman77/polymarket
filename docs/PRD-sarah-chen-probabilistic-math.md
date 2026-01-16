# PRD: Dr. Sarah Chen - Probabilistic Mathematics

**Product Requirements Document**

---

## Document Information

- **Project:** Polymarket AutoTrader System Evaluation
- **Researcher:** Dr. Sarah Chen, PhD - Probabilistic Mathematician
- **Version:** 1.0.0
- **Date:** 2026-01-16
- **Status:** ACTIVE
- **Dependencies:** Kenji Nakamoto (Data Forensics), Dmitri Volkov (System Reliability)

---

## 1. Executive Summary

Dr. Sarah Chen will conduct a rigorous mathematical analysis of the Polymarket AutoTrader's profitability, validating whether the system has positive expected value after accounting for fees, randomness, and statistical uncertainty. Her work establishes the mathematical ground truth for whether the bot is fundamentally profitable or simply experiencing variance.

**Key Deliverables:**
1. Expected value calculation per trade (accounting for fees)
2. Statistical significance analysis of 56-60% win rate claim
3. Kelly Criterion position sizing optimization
4. Breakeven analysis with confidence intervals
5. Long-term profitability projection (1000+ trade simulation)

**Timeline:** 5-7 days (depends on data availability from Kenji)

---

## 2. Research Questions

### Primary Question

**Is the Polymarket AutoTrader mathematically profitable after fees, or is the observed performance due to random variance?**

### Secondary Questions

1. **Expected Value:** What is E[profit] per $1 wagered after accounting for 3-6% round-trip fees?
2. **Statistical Significance:** Is the 56-60% win rate statistically different from the 53% breakeven threshold? (p < 0.05)
3. **Sample Size Adequacy:** Do we have enough trades to make reliable conclusions? (Power analysis)
4. **Optimal Sizing:** Are current position sizing tiers optimal compared to Kelly Criterion?
5. **Fee Impact:** How much does entry price affect net profitability? (Contrarian <$0.20 vs Late Confirmation >$0.85)
6. **Variance Tolerance:** What is the probability of a 30% drawdown given true win rate and position sizing?
7. **Long-term Sustainability:** Can the system maintain profitability over 1000+ trades with 95% confidence?

### Out of Scope

- **Agent performance evaluation** (Victor Ramanujan's domain)
- **Market microstructure** (James Martinez's domain)
- **Behavioral biases** (Dr. Amara Johnson's domain)
- **Risk control logic** (Colonel Rita Stevens's domain)
- **Code bugs/reliability** (Dmitri Volkov's domain)
- **Data integrity issues** (Dr. Kenji Nakamoto's domain)

Dr. Chen focuses purely on **mathematical properties** of the trading distribution, not implementation details or psychology.

---

## 3. Methodology

### Data Sources

#### Primary Data (from Kenji Nakamoto)
- **Validated trade log** (`reports/kenji_nakamoto/trade_log_completeness.md`)
  - ORDER PLACED entries with: timestamp, crypto, direction, entry_price
  - WIN/LOSS outcomes with: P&L, final_price
  - Data quality assessment (completeness %, duplicate rate)

- **Balance reconciliation** (`reports/kenji_nakamoto/balance_reconciliation.md`)
  - Starting balance, deposits, withdrawals
  - Calculated balance vs actual balance (discrepancy check)

- **On-chain verification** (`reports/kenji_nakamoto/on_chain_verification.md`)
  - Blockchain-confirmed transactions (80% verification threshold)

#### Secondary Data (from Dmitri Volkov)
- **State management audit** (`reports/dmitri_volkov/state_audit.md`)
  - Current balance: $200.97
  - Peak balance: $300.00
  - Total trades, wins, losses
  - Validation of state file integrity

- **VPS uptime report** (`reports/dmitri_volkov/vps_uptime_report.md`)
  - Service restarts that might have caused missed trades
  - Downtime periods (affects sample completeness)

#### Configuration Data
- **Position sizing tiers** (`bot/momentum_bot_v12.py` lines 100-110)
  ```python
  POSITION_TIERS = [
      (30, 0.15),     # Balance < $30: max 15% per trade
      (75, 0.10),     # Balance $30-75: max 10%
      (150, 0.07),    # Balance $75-150: max 7%
      (inf, 0.05),    # Balance > $150: max 5%
  ]
  ```

- **Fee structure** (Polymarket documentation)
  - Taker fee formula: `fee = abs(0.5 - probability) * 6.3%`
  - At 50% probability: 3.15% per side = 6.3% round-trip
  - At extremes (10% or 90%): ~1.3% per side = 2.6% round-trip

### Analysis Techniques

#### 1. Expected Value Calculation

**Formula:**
```
E[profit] = (win_rate × avg_win) - ((1 - win_rate) × avg_loss) - avg_fee
```

**Inputs:**
- `win_rate`: Empirical win rate from trade log (target: 56-60%)
- `avg_win`: Average profit on winning trades (entry-dependent)
- `avg_loss`: Average loss on losing trades (typically -100% of wager)
- `avg_fee`: Average round-trip fee (3-6% depending on entry price)

**Breakeven Calculation:**
```
breakeven_win_rate = (avg_loss + avg_fee) / (avg_win + avg_loss + avg_fee)
```

For typical binary options:
- Entry at $0.50 (fair): Need ~53% win rate to break even
- Entry at $0.20 (cheap): Need ~50% win rate (lower fees)
- Entry at $0.85 (expensive): Need ~60% win rate (lower payout)

#### 2. Statistical Significance Testing

**Hypothesis Test:**
- **H0 (null):** True win rate = breakeven rate (system is not profitable)
- **H1 (alternative):** True win rate > breakeven rate (system is profitable)
- **Test:** One-sample proportion z-test
- **Significance level:** α = 0.05 (95% confidence)

**Formula:**
```
z = (observed_rate - breakeven_rate) / sqrt(breakeven_rate * (1 - breakeven_rate) / n)
p_value = 1 - Φ(z)  # Upper-tail test
```

**Interpretation:**
- If p < 0.05: Reject H0 → System is statistically profitable
- If p ≥ 0.05: Fail to reject H0 → Cannot conclude profitability

#### 3. Power Analysis (Sample Size Adequacy)

**Question:** Given observed win rate, how many trades needed to detect profitability with 80% power?

**Formula:**
```
n_required = (z_α + z_β)² × [p₀(1-p₀) + p₁(1-p₁)] / (p₁ - p₀)²
```

Where:
- `z_α = 1.96` (95% confidence)
- `z_β = 0.84` (80% power)
- `p₀ = breakeven rate` (e.g., 0.53)
- `p₁ = observed rate` (e.g., 0.58)

**Example:**
To detect 58% vs 53% with 80% power: ~785 trades needed

#### 4. Confidence Intervals

**95% Confidence Interval for True Win Rate:**
```
CI = observed_rate ± 1.96 × sqrt(observed_rate × (1 - observed_rate) / n)
```

**Interpretation:**
- If lower bound of CI > breakeven rate → Profitable with 95% confidence
- If lower bound < breakeven rate → Profitability uncertain

#### 5. Kelly Criterion Position Sizing

**Optimal Bet Size:**
```
f* = (p × b - q) / b
```

Where:
- `p` = probability of winning (true win rate)
- `q` = 1 - p (probability of losing)
- `b` = odds received (payout ratio)

**Example:**
- Entry at $0.20, win rate 58%
- Payout: $1.00 / $0.20 = 5x (b = 4 net)
- Kelly fraction: (0.58 × 4 - 0.42) / 4 = 0.475 (47.5% of bankroll!)

**Reality Check:**
Kelly often suggests aggressive sizing. Use **fractional Kelly** (20-25% of f*) for practical risk management.

**Comparison to Current Tiers:**
- Current: 5-15% per trade (fixed tiers)
- Kelly: Dynamic sizing based on edge and bankroll
- Analysis: Compare Sharpe ratio and max drawdown of both approaches

#### 6. Monte Carlo Simulation

**Purpose:** Project long-term performance under different scenarios

**Method:**
1. Fit probability distribution to observed trade returns
2. Simulate 10,000 paths of 1000 trades each
3. Calculate percentiles of final balance
4. Estimate probability of ruin (hitting $0 or drawdown halt)

**Key Metrics:**
- Median final balance (50th percentile)
- 5th percentile (worst-case scenario)
- 95th percentile (best-case scenario)
- Probability of 30% drawdown
- Expected time to recover from drawdown

#### 7. Variance Decomposition

**Question:** How much of P&L variance is due to:
- Win rate variance (skill)
- Entry price variance (timing)
- Crypto-specific variance (asset selection)
- Epoch-level variance (market conditions)

**Method:** ANOVA or linear regression

```
P&L = β₀ + β₁(crypto) + β₂(entry_price) + β₃(time_of_day) + β₄(strategy) + ε
```

**Goal:** Identify which factors contribute most to profitability

### Tools & Environment

#### Python Libraries
```python
import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.power import zt_ind_solve_power
```

#### Statistical Software
- **Jupyter Notebook** for interactive analysis
- **matplotlib/seaborn** for visualizations
- **scipy.stats** for hypothesis testing
- **numpy** for Monte Carlo simulation

#### Compute Resources
- **Local machine** (sufficient for analysis)
- **No VPS access required** (operates on Kenji's validated datasets)

---

## 4. Deliverables

### Required Outputs

#### 1. Expected Value Analysis Report
**File:** `reports/sarah_chen/expected_value_analysis.md`

**Contents:**
- Executive summary (is system profitable? yes/no)
- E[profit] per $1 wagered (with 95% CI)
- Breakeven win rate calculation
- Observed vs required win rate comparison
- Fee impact analysis (by entry price tier)
- Verdict: PROFITABLE / BREAKEVEN / UNPROFITABLE

**Acceptance Criteria:**
- Clear yes/no answer on profitability
- Confidence interval includes uncertainty quantification
- Fee calculation validated against Polymarket docs

#### 2. Statistical Significance Report
**File:** `reports/sarah_chen/statistical_significance.md`

**Contents:**
- Hypothesis test results (z-score, p-value)
- Power analysis (current n vs required n)
- 95% confidence interval for true win rate
- Sample size recommendations (how many more trades needed?)
- Verdict: SIGNIFICANT / INSUFFICIENT_DATA / NOT_SIGNIFICANT

**Acceptance Criteria:**
- p-value < 0.05 for significance claim
- Power analysis shows adequate sample size (≥80% power)
- Recommendations actionable (specific trade count needed)

#### 3. Kelly Criterion Position Sizing Analysis
**File:** `reports/sarah_chen/kelly_criterion_analysis.md`

**Contents:**
- Full Kelly fractions calculated for typical scenarios
- Fractional Kelly recommendations (20-25% of f*)
- Comparison: Current tiers vs Kelly sizing
- Simulated performance: Sharpe ratio, max drawdown
- Recommendation: Keep current / Switch to Kelly / Hybrid approach

**Acceptance Criteria:**
- Kelly fractions calculated correctly (validated by hand calculation)
- Monte Carlo comparison includes ≥1000 simulation paths
- Recommendation backed by quantitative metrics

#### 4. Long-term Profitability Projection
**File:** `reports/sarah_chen/profitability_projection.md`

**Contents:**
- Monte Carlo simulation (10,000 paths × 1000 trades)
- Percentile distribution (5th, 50th, 95th)
- Probability of 30% drawdown in next 100/500/1000 trades
- Expected time to double bankroll (if profitable)
- Risk of ruin (probability of hitting $0)

**Acceptance Criteria:**
- Simulation uses validated trade distribution from Kenji's data
- Results presented with clear visualizations (histograms, percentile plots)
- Risk assessment includes confidence intervals

#### 5. Variance Decomposition Analysis
**File:** `reports/sarah_chen/variance_decomposition.md`

**Contents:**
- ANOVA results: Which factors explain P&L variance?
- Crypto-specific performance (BTC vs ETH vs SOL vs XRP)
- Entry price impact (cheap <$0.20 vs expensive >$0.70)
- Time-of-day effects (if any)
- Recommendations: Focus on high-variance-explained factors

**Acceptance Criteria:**
- R² ≥ 0.30 (model explains ≥30% of variance)
- Factor rankings clear (which matters most?)
- Recommendations specific (e.g., "avoid BTC trades" if statistically worse)

### Format Standards

#### Report Format
- **Markdown** for human-readable reports
- **Jupyter Notebook** for reproducible analysis (`.ipynb` in `scripts/research/`)
- **CSV exports** for downstream researchers (James, Victor, Rita)

#### Visualization Requirements
- **High-resolution** plots (300 DPI for reports)
- **Clear labels** (axes, titles, legends)
- **Color-blind friendly** palettes (seaborn colorblind10)
- **Annotations** for key thresholds (e.g., breakeven line, 30% drawdown)

#### Code Documentation Standards
- **Docstrings** for all functions (NumPy style)
- **Inline comments** for complex calculations
- **Type hints** for function signatures
- **Unit tests** for critical calculations (e.g., Kelly formula)

### Delivery Schedule

- **Day 1:** Receive validated data from Kenji → Begin EV analysis
- **Day 2:** Complete expected value report + statistical significance
- **Day 3:** Kelly Criterion analysis + comparison to current tiers
- **Day 4:** Monte Carlo simulation + long-term projection
- **Day 5:** Variance decomposition + factor analysis
- **Day 6:** Review, revisions, stakeholder presentation
- **Day 7:** BUFFER (for unexpected issues or deeper dives)

**Final Delivery:** Day 6 (with Day 7 as contingency)

---

## 5. Success Criteria

### Quantitative Metrics

#### Statistical Rigor
- **Significance tests:** p-values correctly calculated (α = 0.05)
- **Power analysis:** Achieved ≥80% statistical power
- **Sample size:** If n < required, clearly state insufficient data
- **Confidence intervals:** All estimates include 95% CI

#### Reproducibility
- **Code execution:** Jupyter notebook runs without errors
- **Seed fixing:** Monte Carlo uses fixed random seed (reproducible)
- **Version control:** All scripts committed to git with clear commit messages

#### Accuracy
- **Fee calculation:** Validated against Polymarket fee formula
- **Kelly formula:** Cross-checked with academic literature (Thorp, Kelly)
- **Simulation:** Results converge (10k paths sufficient, not 1k)

### Qualitative Standards

#### Clarity
- **Executive summaries:** Non-technical stakeholders understand yes/no verdict
- **Technical sections:** Statisticians can validate methodology
- **Visualizations:** Plots tell story without reading full report

#### Completeness
- **All deliverables:** 5 reports delivered on schedule
- **Edge cases handled:** Insufficient data scenarios addressed
- **Limitations documented:** Known issues/assumptions stated clearly

#### Actionability
- **Recommendations concrete:** "Add 200 more trades" not "collect more data"
- **Trade-offs clear:** Kelly vs current tiers (pros/cons of each)
- **Prioritization:** Most impactful findings highlighted

### Acceptance Criteria

**Definition of "Done":**
1. All 5 reports delivered in markdown format
2. Jupyter notebook(s) execute without errors
3. Statistical tests validated by peer review (Victor Ramanujan)
4. Visualizations included in reports (PNG/SVG embedded)
5. CSV exports available for downstream researchers
6. Stakeholder sign-off received (clear verdict on profitability)

**Review Process:**
1. Self-review: Check calculations by hand
2. Peer review: Victor Ramanujan validates methodology
3. Stakeholder review: Lead researcher approves conclusions
4. Final sign-off: Reports published to team repository

**Sign-off Requirements:**
- [ ] Dr. Sarah Chen: Confirms accuracy of all calculations
- [ ] Victor Ramanujan: Validates statistical methodology
- [ ] Lead Researcher: Approves conclusions and recommendations

---

## 6. Dependencies

### Upstream Dependencies

#### From Dr. Kenji Nakamoto (Data Forensics) - BLOCKING
**Required Inputs:**
1. **Validated trade log** with completeness assessment
   - Need ≥100 trades with complete outcomes (ORDER + WIN/LOSS matched)
   - Duplicate rate <1% (to avoid inflated sample size)
   - File: `reports/kenji_nakamoto/trade_log_completeness.md`

2. **Balance reconciliation** to validate P&L accuracy
   - Starting balance, deposits, withdrawals
   - Discrepancy <$10 (to trust calculated balance)
   - File: `reports/kenji_nakamoto/balance_reconciliation.md`

3. **Survivorship bias check** to ensure data completeness
   - No missing days (gaps in trading history)
   - No removed strategies inflating win rate
   - File: `reports/kenji_nakamoto/survivorship_bias_report.md`

**Blocking Condition:**
If Kenji finds <100 complete trades or >5% duplicate rate → Sarah cannot proceed with significance testing (insufficient sample).

**Mitigation:**
If data insufficient, Sarah will document limitations and provide qualitative analysis only (no statistical claims).

#### From Dmitri Volkov (System Reliability) - PARALLEL (Non-blocking)
**Optional Inputs:**
1. **State file validation** (confirms balance is accurate)
   - File: `reports/dmitri_volkov/state_audit.md`

2. **VPS uptime report** (identifies potential missed trades)
   - Downtime periods to cross-reference with trade gaps
   - File: `reports/dmitri_volkov/vps_uptime_report.md`

**Note:** Sarah can proceed without Dmitri's reports, but they provide context for explaining anomalies.

### Downstream Consumers

#### James Martinez (Market Microstructure) - CONSUMES SARAH'S OUTPUTS
**Uses:**
- Expected value analysis → Validates fee impact hypothesis
- Entry price variance analysis → Informs optimal entry timing
- CSV export: `trade_returns_by_entry_price.csv`

#### Victor Ramanujan (Quantitative Strategy) - CONSUMES SARAH'S OUTPUTS
**Uses:**
- Statistical significance → Validates agent performance claims
- Kelly Criterion → Informs optimal position sizing for shadow strategies
- Monte Carlo → Sets realistic performance targets for optimization
- CSV export: `trade_level_statistics.csv`

#### Colonel Rita Stevens (Risk Management) - CONSUMES SARAH'S OUTPUTS
**Uses:**
- Monte Carlo drawdown probability → Validates 30% halt threshold
- Variance decomposition → Identifies high-risk factors to limit
- Kelly Criterion → Evaluates current position sizing safety

#### Prof. Eleanor Nash (Game Theory) - CONSUMES SARAH'S OUTPUTS
**Uses:**
- Long-term profitability → Validates sustainable strategy equilibrium
- Expected value → Informs Nash equilibrium analysis

### Collaboration Requirements

#### Joint Sessions
1. **Day 3 Sync with Victor Ramanujan:**
   - Review Kelly Criterion methodology
   - Discuss fractional Kelly for shadow strategy testing

2. **Day 5 Sync with James Martinez:**
   - Share entry price variance findings
   - Coordinate on fee impact analysis

#### Data Sharing Protocols
- **CSV exports:** Delivered to `reports/sarah_chen/data/` directory
- **Jupyter notebooks:** Published to `scripts/research/sarah_chen/` directory
- **Raw calculations:** Documented in notebook (for reproducibility)

#### Communication Cadence
- **Daily standups:** 15-min sync with Kenji, Dmitri, Victor
- **Slack updates:** Share key findings as they emerge
- **Weekly review:** Present preliminary results to full team

---

## 7. Risk Assessment

### Data Availability Risks

#### Risk: Insufficient Sample Size
**Scenario:** Kenji finds <100 complete trades in logs

**Impact:**
- Cannot perform statistical significance testing (underpowered)
- Confidence intervals too wide to be useful
- Recommendations will be qualitative only

**Probability:** MODERATE (bot has been running for weeks, but logs may be incomplete)

**Mitigation:**
1. **Plan B:** Use shadow trading database (27 strategies × virtual trades)
   - More trades available, but not real money (lower confidence)
2. **Plan C:** Document limitations clearly (no false claims of significance)
3. **Recommendation:** Collect 100+ more trades before drawing conclusions

#### Risk: Data Quality Issues
**Scenario:** Kenji finds >5% duplicate rate or >10% missing outcomes

**Impact:**
- Sample size inflated (duplicates counted twice)
- Biased win rate (missing outcomes skew results)
- Expected value calculations unreliable

**Probability:** LOW (Kenji's duplicate detection should catch this)

**Mitigation:**
1. Use Kenji's cleaned dataset (duplicates removed, incomplete trades excluded)
2. Sensitivity analysis: Recalculate E[profit] under different data quality assumptions
3. Document assumptions clearly in reports

### Technical Risks

#### Risk: Compute Constraints for Monte Carlo
**Scenario:** 10,000 paths × 1,000 trades = 10M simulations (slow on laptop)

**Impact:**
- Long runtime (hours instead of minutes)
- May need to reduce simulation count

**Probability:** LOW (modern laptops handle this fine)

**Mitigation:**
1. Use NumPy vectorization (not Python loops)
2. Reduce to 5,000 paths if needed (still statistically valid)
3. Run overnight if necessary

#### Risk: Statistical Software Bugs
**Scenario:** scipy.stats or statsmodels miscalculates p-value

**Impact:**
- Incorrect significance claims
- Flawed recommendations

**Probability:** VERY LOW (well-tested libraries)

**Mitigation:**
1. Cross-check critical calculations by hand (e.g., z-test)
2. Use multiple libraries (scipy + statsmodels) for validation
3. Peer review with Victor Ramanujan (independent verification)

### Analytical Risks

#### Risk: Confounding Variables Not Accounted For
**Scenario:** Win rate varies by market regime, but analysis assumes constant

**Impact:**
- Expected value overestimated (if current regime is favorable)
- Long-term projection too optimistic

**Probability:** MODERATE (regime shifts documented in CLAUDE.md)

**Mitigation:**
1. Stratified analysis: Calculate E[profit] separately for BULL/BEAR/CHOPPY regimes
2. Worst-case scenario: Use lowest regime-specific win rate for projections
3. Recommend regime-aware position sizing to Rita Stevens

#### Risk: Non-Stationarity (Strategy Evolves Over Time)
**Scenario:** Bot performance improves/degrades over time (v12 → v12.1)

**Impact:**
- Historical win rate not representative of future performance
- Monte Carlo projection unreliable

**Probability:** HIGH (documented improvement from v11 → v12 → v12.1)

**Mitigation:**
1. Use only v12.1 data (most recent version)
2. Document version changes in reports
3. Recommend ongoing monitoring (recalculate E[profit] monthly)

---

## 8. Resources

### Access Requirements

#### Data Access
- **Kenji's reports:** `reports/kenji_nakamoto/*.md` (read-only)
- **Dmitri's reports:** `reports/dmitri_volkov/*.md` (read-only)
- **Bot code:** `bot/momentum_bot_v12.py` (read-only, for fee/sizing logic)
- **Config files:** `config/agent_config.py` (read-only)

**No VPS access required** (Sarah operates on validated datasets, not live system)

**No API keys required** (Sarah does not query external services)

#### Write Access
- **Reports directory:** `reports/sarah_chen/` (create directory if needed)
- **Scripts directory:** `scripts/research/sarah_chen/` (for Jupyter notebooks)
- **Data exports:** `reports/sarah_chen/data/` (CSV files for downstream researchers)

### Computational Resources

#### Hardware
- **Local laptop:** Sufficient for all analysis
  - CPU: 4+ cores (for parallel Monte Carlo)
  - RAM: 8GB+ (NumPy arrays)
  - Storage: 1GB (trade data + simulation results)

#### Software
- **Python 3.11+** (modern type hints)
- **Jupyter Notebook** (interactive analysis)
- **Required packages:**
  ```
  numpy>=1.24.0
  pandas>=2.0.0
  scipy>=1.10.0
  matplotlib>=3.7.0
  seaborn>=0.12.0
  statsmodels>=0.14.0
  jupyterlab>=4.0.0
  ```

### Domain Expertise Support

#### Subject Matter Experts
1. **Kelly Criterion:** Victor Ramanujan (review methodology)
2. **Binary options pricing:** James Martinez (validate fee calculations)
3. **Statistical methods:** Self (PhD in probabilistic mathematics)

#### Literature Review
- **Kelly Criterion:** "A New Interpretation of Information Rate" (Kelly 1956)
- **Optimal Betting:** "The Kelly Criterion in Blackjack Sports Betting" (Thorp 1997)
- **Binary options:** "The Mathematics of Gambling" (Ethier 2010)
- **Monte Carlo:** "Monte Carlo Methods in Financial Engineering" (Glasserman 2003)

#### External Validation
- **Polymarket fee docs:** https://docs.polymarket.com/fees
- **CLOB API:** https://docs.polymarket.com/api (for order book validation)

---

## 9. Appendix

### A. Reference Materials

#### Code Files to Analyze
```
bot/momentum_bot_v12.py
├── Lines 100-110: POSITION_TIERS (sizing logic)
├── Lines 500-550: Fee calculation (if present)
└── Lines 1800-1900: State persistence (balance tracking)

config/agent_config.py
├── CONSENSUS_THRESHOLD (affects trade frequency)
├── MIN_CONFIDENCE (affects trade selection)
└── SHADOW_STRATEGIES (alternative approaches)
```

#### System Documentation
- **CLAUDE.md:** Bot overview, performance history, known issues
- **SETUP.md:** Local development environment
- **DEPLOYMENT.md:** VPS deployment process

#### Academic Papers
1. Kelly, J. L. (1956). "A New Interpretation of Information Rate." *Bell System Technical Journal*, 35(4), 917-926.
2. Thorp, E. O. (1997). "The Kelly Criterion in Blackjack Sports Betting, and the Stock Market." *Handbook of Asset and Liability Management*, Vol 1, 385-428.
3. Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer.

### B. Glossary

**Terms:**
- **Expected Value (EV):** Average profit per $1 wagered over infinite trials
- **Kelly Criterion:** Formula for optimal bet sizing to maximize log growth
- **Breakeven Win Rate:** Minimum win rate needed for E[profit] = 0
- **Statistical Significance:** Probability that observed effect is not due to chance (p < 0.05)
- **Power Analysis:** Calculation of minimum sample size for reliable detection
- **Monte Carlo Simulation:** Repeated random sampling to estimate probability distributions
- **Confidence Interval (CI):** Range containing true parameter with specified probability (95%)
- **ANOVA:** Analysis of Variance (decomposes variance into explained/unexplained)

**Acronyms:**
- **EV:** Expected Value
- **CI:** Confidence Interval
- **PDF:** Probability Density Function
- **CDF:** Cumulative Distribution Function
- **ANOVA:** Analysis of Variance
- **MC:** Monte Carlo

### C. Change Log

**Version 1.0.0** (2026-01-16)
- Initial PRD draft
- Defined research questions, methodology, deliverables
- Established dependencies on Kenji and Dmitri
- Set 5-7 day timeline

**Future Revisions:**
- Version 1.1.0: Post-review updates from Lead Researcher
- Version 2.0.0: Adjustments based on data availability

---

## 10. Status Summary

**Current Status:** READY TO BEGIN (pending Kenji's data validation)

**Blockers:**
- Kenji Nakamoto's validated trade log (US-RC-001)
- Kenji Nakamoto's balance reconciliation (US-RC-003)
- Kenji Nakamoto's survivorship bias check (US-RC-005)

**Next Steps:**
1. Wait for Kenji's data deliverables
2. Set up Jupyter notebook environment
3. Begin expected value analysis (Day 1)

---

**APPROVAL SIGNATURES:**

- [ ] **Dr. Sarah Chen:** Methodology approved
- [ ] **Lead Researcher:** Research scope approved
- [ ] **Victor Ramanujan:** Statistical methods validated
- [ ] **Dr. Kenji Nakamoto:** Data dependencies confirmed

---

**END OF PRD**

Ready to execute upon receipt of validated data from Dr. Kenji Nakamoto. 🎯
