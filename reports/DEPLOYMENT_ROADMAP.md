# Deployment Roadmap: Research Implementation
**Version:** 1.0
**Created:** 2026-01-16
**Owner:** Prof. Eleanor Nash (Strategic Synthesis)
**Timeline:** 4 weeks (Jan 16 - Feb 13, 2026)

---

## Executive Summary

This roadmap translates research findings from 8 specialized personas (48 reports, 31 analyses) into executable implementation milestones.

**Strategic Approach:** Simplify first (remove what hurts), then optimize (improve what works).

**Expected Outcome:**
- Win Rate: 58% → 63-65%
- System Complexity: 11 agents → 3-5 agents
- Risk: Lower (better state management, no directional bias)
- Trade Quality: Higher confidence, cheaper entries

**Success Metrics:**
- Win rate improvement measured after each milestone
- Deployment is incremental (rollback if WR drops)
- Shadow testing validates changes before production deployment

---

## Week 1: Foundation & Quick Wins (Jan 16-23)

**Focus:** Critical fixes and immediate simplifications

### Milestone 1.1: Fix State Tracking Bugs
**Priority:** CRITICAL
**Owner:** Dmitri "The Hammer" Volkov (System Reliability)
**Effort:** 4 hours
**Risk Level:** LOW (fix only, no new features)

**Problem:**
- Peak balance includes unredeemed position values
- Causes false drawdown halts (Jan 16 desync: $186 error)
- Drawdown protection fails when positions settle

**Implementation:**
1. Review `bot/momentum_bot_v12.py` → `Guardian.check_kill_switch()`
2. Change `peak_balance` tracking to use **cash-only balance** (exclude open positions)
3. Update peak only on:
   - Deposit events
   - Winning position redemptions (cash increases)
   - NOT on order placement (positions are unrealized)
4. Add validation: `assert current_balance <= peak_balance`

**Files Changed:**
- `bot/momentum_bot_v12.py` (Guardian class)
- `state/trading_state.json` (reset peak to current cash balance)

**Success Metrics:**
- No false halts for 7 days
- Drawdown calculation accurate within $1
- Peak balance only increases on actual cash gains

**Rollback Plan:**
- Revert `Guardian.check_kill_switch()` to previous version
- Restore state file from backup

**Testing:**
- Unit test: Simulate open position + redemption scenario
- Verify peak doesn't update on order placement
- Verify peak updates correctly on redemption

---

### Milestone 1.2: Remove Trend Filter
**Priority:** HIGH
**Owner:** Alex "Occam" Rousseau (First Principles Engineer)
**Effort:** 2 hours
**Risk Level:** MEDIUM (removes decision logic)

**Problem:**
- Trend filter caused 96.5% UP bias (Jan 14 loss: $157 → $7)
- Blocked 319 DOWN bets, 0 UP bets in weak positive trend
- Regime detection (RegimeAgent) provides sufficient trend awareness

**Implementation:**
1. Review `bot/momentum_bot_v12.py` → trend filter logic
2. Remove `TREND_FILTER_ENABLED` and related code
3. Keep RegimeAgent for regime-based adjustments
4. Remove `STRONG_TREND_THRESHOLD` (no longer needed)

**Files Changed:**
- `bot/momentum_bot_v12.py` (remove trend filter sections)
- `config/agent_config.py` (remove TREND_FILTER_ENABLED flag)

**Success Metrics:**
- Directional balance: 40-60% (vs 96.5% before)
- Win rate: ≥58% (should improve without bias)
- Trade frequency: Similar or higher (no artificial blocks)

**Rollback Plan:**
- Re-enable `TREND_FILTER_ENABLED=True`
- Restore removed code from git history

**Testing:**
- Shadow test for 24 hours
- Monitor directional distribution (should be balanced)
- Compare WR to baseline (should not drop)

---

### Milestone 1.3: Disable Underperforming Agents
**Priority:** HIGH
**Owner:** Victor "Vic" Ramanujan (Quantitative Strategist)
**Effort:** 3 hours
**Risk Level:** LOW (config change only)

**Problem:**
- Per-agent analysis shows negative contributors:
  - **TechAgent:** 48% WR (below breakeven)
  - **SentimentAgent:** 52% WR (marginal)
  - **CandleAgent:** 49% WR (below breakeven)
- Consensus diluted by poor performers

**Implementation:**
1. Read `reports/vic_ramanujan/per_agent_performance.md`
2. Identify agents with <53% WR (below breakeven)
3. Update `config/agent_config.py`:
   - `ENABLE_TECH_AGENT = False`
   - `ENABLE_SENTIMENT_AGENT = False`
   - `ENABLE_CANDLE_AGENT = False`
4. Keep high performers: ML, RegimeAgent, RiskAgent

**Files Changed:**
- `config/agent_config.py` (disable flags)

**Success Metrics:**
- Trade frequency: Should drop 20-30% (higher quality bar)
- Win rate: Should improve 2-3% (removing bad votes)
- Consensus: Should be cleaner (fewer conflicting signals)

**Rollback Plan:**
- Set `ENABLE_*_AGENT = True` for reverted agents
- No code changes needed (config only)

**Testing:**
- Shadow test with disabled agents for 48 hours
- Compare WR: disabled vs baseline
- If WR drops >1%, re-enable one agent at a time

---

### Milestone 1.4: Implement Atomic State Writes
**Priority:** MEDIUM
**Owner:** Dmitri "The Hammer" Volkov (System Reliability)
**Effort:** 2 hours
**Risk Level:** LOW (safety improvement)

**Problem:**
- `trading_state.json` written directly (not atomic)
- Crash during write → corrupted state file
- Bot fails to start after corruption

**Implementation:**
1. Review `bot/momentum_bot_v12.py` → `save_state()` function
2. Implement atomic write pattern:
   - Write to `.tmp` file first
   - `os.rename()` to actual file (atomic on POSIX)
3. Add error handling: if write fails, don't delete old state

**Files Changed:**
- `bot/momentum_bot_v12.py` (save_state function)

**Success Metrics:**
- No state corruption in crash tests
- State file always valid JSON
- No data loss during crash recovery

**Rollback Plan:**
- Revert to direct write (less safe but simpler)
- Manual state file restore from backup if needed

**Testing:**
- Simulate crash during state save (SIGKILL mid-write)
- Verify state file remains valid
- Verify bot recovers gracefully

---

## Week 2: Optimization Improvements (Jan 24-31)

**Focus:** Threshold tuning and entry optimization

### Milestone 2.1: Raise Consensus Threshold
**Priority:** HIGH
**Owner:** Dr. Sarah Chen (Probabilistic Mathematician)
**Effort:** 3 hours
**Risk Level:** MEDIUM (changes trade selection)

**Problem:**
- Current threshold (0.75) allows marginal trades (52-56% WR)
- Need higher confidence bar for consistent profitability

**Implementation:**
1. Read `reports/sarah_chen/statistical_significance.md`
2. Calculate optimal threshold:
   - Current: 0.75 → 58% WR
   - Target: 0.82-0.85 → 63-65% WR (projected)
3. Update `config/agent_config.py`:
   - `CONSENSUS_THRESHOLD = 0.82`
   - `MIN_CONFIDENCE = 0.70` (raise from 0.60)

**Files Changed:**
- `config/agent_config.py` (threshold values)

**Success Metrics:**
- Trade frequency: Drop 30-40% (expected)
- Win rate: Improve 3-5% (higher quality trades)
- Min 5 trades/day (ensure sufficient activity)

**Rollback Plan:**
- Revert to `CONSENSUS_THRESHOLD = 0.75`
- If trade frequency <3/day, lower to 0.78

**Testing:**
- Shadow test for 48 hours at 0.82
- Measure trade frequency and WR
- Adjust threshold if needed (0.78-0.85 range)

---

### Milestone 2.2: Optimize Entry Timing Windows
**Priority:** MEDIUM
**Owner:** James "Jimmy the Greek" Martinez (Market Microstructure)
**Effort:** 4 hours
**Risk Level:** MEDIUM (changes timing strategy)

**Problem:**
- Early trades (0-300s): 54% WR (high risk)
- Late trades (600-900s): 62% WR (best performance)
- Current strategy doesn't prioritize late entries

**Implementation:**
1. Read `reports/jimmy_martinez/timing_window_analysis.md`
2. Add timing preference to decision logic:
   - Bonus confidence: +5% for 600-900s window
   - Penalty: -3% for 0-300s window (unless very strong signal)
3. Update `bot/momentum_bot_v12.py`:
   - Add `calculate_timing_bonus()` function
   - Apply to final confidence score

**Files Changed:**
- `bot/momentum_bot_v12.py` (timing logic)
- `config/agent_config.py` (timing thresholds)

**Success Metrics:**
- Late trades (600-900s): ≥60% of total trades
- Late trade WR: Maintain or improve 62%
- Overall WR: Improve 1-2%

**Rollback Plan:**
- Remove timing bonus logic
- Revert to time-agnostic strategy

**Testing:**
- Shadow test with timing bonus for 3 days
- Measure timing distribution (should shift later)
- Compare WR: timing-optimized vs baseline

---

### Milestone 2.3: Lower Entry Price Threshold
**Priority:** MEDIUM
**Owner:** James "Jimmy the Greek" Martinez (Market Microstructure)
**Effort:** 2 hours
**Risk Level:** LOW (tightens entry criteria)

**Problem:**
- Entries <$0.15: 68% WR (excellent)
- Entries >$0.25: 52% WR (poor)
- Current `MAX_ENTRY_PRICE = 0.30` (too permissive)

**Implementation:**
1. Read `reports/jimmy_martinez/entry_vs_outcome.csv`
2. Update `config/agent_config.py`:
   - `EARLY_MAX_ENTRY = 0.20` (from 0.30)
   - `CONTRARIAN_MAX_ENTRY = 0.15` (from 0.20)
   - `LATE_MAX_ENTRY = 0.25` (from 0.30)

**Files Changed:**
- `config/agent_config.py` (entry price limits)

**Success Metrics:**
- Average entry price: <$0.20 (from ~$0.24)
- Cheap entries (<$0.15): ≥40% of trades
- Win rate: Improve 2-3%

**Rollback Plan:**
- Revert to previous limits if trade frequency <3/day

**Testing:**
- Monitor trade frequency for 24 hours
- If too restrictive, adjust to 0.22/0.18/0.27

---

## Week 3: Simplification & Architecture (Feb 1-8)

**Focus:** Agent reduction and system cleanup

### Milestone 3.1: Reduce Agent Count (11 → 5)
**Priority:** MEDIUM
**Owner:** Alex "Occam" Rousseau (First Principles Engineer)
**Effort:** 6 hours
**Risk Level:** HIGH (major architecture change)

**Problem:**
- 11 agents is over-engineered (high correlation, redundancy)
- Maintenance burden: 11 configs, 11 weights, 11 voting logic paths
- Diminishing returns: Most agents don't improve consensus

**Implementation:**
1. Read `reports/alex_rousseau/elimination_candidates.md`
2. Keep only proven performers:
   - **ML Agent** (67% WR on test set)
   - **RegimeAgent** (provides market context)
   - **RiskAgent** (prevents overexposure)
   - **PriceAgent** (entry price validation)
   - **ConfluenceAgent** (multi-exchange agreement)
3. Remove:
   - TechAgent (already disabled in Week 1)
   - SentimentAgent (already disabled in Week 1)
   - CandleAgent (already disabled in Week 1)
   - VolumeAgent (redundant with ConfluenceAgent)
   - MomentumAgent (redundant with ML)
   - TimingAgent (logic moved to core bot)

**Files Changed:**
- `config/agent_config.py` (remove agent configs)
- `agents/` directory (archive removed agents)
- `bot/momentum_bot_v12.py` (simplify voting logic)

**Success Metrics:**
- Agent count: 11 → 5 (55% reduction)
- Code complexity: ~1600 lines → ~1200 lines
- Win rate: Maintain or improve (should not drop)
- Decision latency: Faster (fewer agents to query)

**Rollback Plan:**
- Keep removed agents in `agents/archived/`
- Re-enable from archive if WR drops >2%

**Testing:**
- Shadow test 5-agent system for 5 days
- Compare WR and decision quality
- Gradual rollout: disable 2 agents at a time

---

### Milestone 3.2: Re-enable Contrarian Strategy
**Priority:** LOW
**Owner:** James "Jimmy the Greek" Martinez (Market Microstructure)
**Effort:** 3 hours
**Risk Level:** MEDIUM (re-enables disabled strategy)

**Problem:**
- Contrarian disabled after Jan 14 incident
- Historical data shows 70% WR for contrarian trades
- Missing cheap entry opportunities (<$0.20)

**Implementation:**
1. Read `reports/jimmy_martinez/contrarian_performance.md`
2. Update `config/agent_config.py`:
   - `ENABLE_CONTRARIAN_TRADES = True`
   - Raise threshold: `CONTRARIAN_MIN_CONFIDENCE = 0.85` (very high bar)
   - Entry limit: `CONTRARIAN_MAX_ENTRY = 0.15` (cheap only)
3. Add safeguard: Only in SIDEWAYS/CHOPPY regime (not BULL/BEAR)

**Files Changed:**
- `config/agent_config.py` (contrarian settings)
- `bot/momentum_bot_v12.py` (regime check)

**Success Metrics:**
- Contrarian trades: 2-5/day (not dominant)
- Contrarian WR: ≥65% (validate historical performance)
- Average entry: <$0.15 (cheap entries)

**Rollback Plan:**
- Set `ENABLE_CONTRARIAN_TRADES = False` if WR <60%

**Testing:**
- Shadow test contrarian logic for 3 days
- Require 20+ contrarian trades before production
- Compare WR: contrarian vs momentum

---

## Week 4: Monitoring & Automation (Feb 9-13)

**Focus:** Alerts and performance tracking

### Milestone 4.1: Add Performance Degradation Alerts
**Priority:** LOW
**Owner:** Colonel Rita "The Guardian" Stevens (Risk Management)
**Effort:** 4 hours
**Risk Level:** LOW (monitoring only)

**Problem:**
- No automated alerts for performance issues
- Slow to detect regime shifts or strategy degradation
- Manual monitoring required (time-intensive)

**Implementation:**
1. Create `utils/performance_monitor.py`
2. Track rolling metrics (last 50 trades):
   - Win rate
   - Average entry price
   - Directional balance (UP vs DOWN)
   - Drawdown level
3. Define alert thresholds:
   - Win rate <55% for 20+ trades
   - Directional bias >70% (20+ trades)
   - Drawdown >25%
   - Consecutive losses ≥5
4. Send alerts via:
   - Log file (bot.log)
   - Email (optional)
   - Telegram bot (optional)

**Files Changed:**
- `utils/performance_monitor.py` (new file)
- `bot/momentum_bot_v12.py` (call monitor after each trade)

**Success Metrics:**
- Alerts triggered correctly in test scenarios
- No false positives (alert when no actual issue)
- Alerts visible in dashboard

**Rollback Plan:**
- Disable monitoring if alerts are too noisy

**Testing:**
- Simulate degradation scenarios (inject fake bad trades)
- Verify alerts fire correctly
- Test email/Telegram integration (if enabled)

---

### Milestone 4.2: Shadow Strategy Auto-Promotion
**Priority:** LOW
**Owner:** Victor "Vic" Ramanujan (Quantitative Strategist)
**Effort:** 6 hours
**Risk Level:** MEDIUM (automates strategy changes)

**Problem:**
- Shadow strategies collect data but require manual review
- Best-performing shadows should auto-promote to production
- Continuous optimization requires human intervention

**Implementation:**
1. Create `scripts/auto_promote_strategy.py`
2. Query `simulation/trade_journal.db` daily
3. Compare shadow strategies to live strategy:
   - Win rate difference (must be ≥+3%)
   - Sample size (min 50 trades)
   - Statistical significance (p < 0.05)
4. If shadow wins, generate promotion PR:
   - Update `config/agent_config.py` with shadow params
   - Create git commit with performance comparison
   - Notify for approval (don't auto-merge)

**Files Changed:**
- `scripts/auto_promote_strategy.py` (new file)
- Cron job: Run daily at 00:00 UTC

**Success Metrics:**
- Script identifies outperforming strategies
- Promotion PRs generated automatically
- Human approval still required (safety)

**Rollback Plan:**
- Disable auto-promotion cron job
- Manual strategy updates only

**Testing:**
- Manually inject high-performing shadow data
- Verify script generates correct promotion PR
- Test git commit and notification flow

---

## Success Metrics & Validation

### Global Metrics (Measured After Roadmap Completion)

**Win Rate:**
- Current: ~58%
- Target: 63-65%
- Minimum acceptable: 60%
- Measurement: Rolling 100 trades

**System Complexity:**
- Current: 11 agents, 1600 lines, 50+ config params
- Target: 5 agents, 1200 lines, <30 config params
- Measurement: Code audit, LOC count

**Trade Quality:**
- Entry price: <$0.20 average (from $0.24)
- Late trades: ≥60% of total (from ~40%)
- Cheap entries (<$0.15): ≥40% of trades

**Risk Metrics:**
- Drawdown protection: No false halts
- Directional balance: 40-60% range
- State corruption: 0 incidents

### Validation Plan

**After Each Milestone:**
1. Deploy to shadow environment (24-48 hours)
2. Measure impact on WR, trade frequency, entry quality
3. Compare to baseline (pre-milestone metrics)
4. If WR drops >1%, investigate and rollback
5. If WR improves or neutral, deploy to production

**After Week 2:**
- Checkpoint: Should have 60%+ WR on 100+ trades
- If not, pause Week 3 and debug Week 1-2 changes

**After Week 4:**
- Final validation: 100 trades at 63-65% WR
- If target not met, re-run analysis (markets may have changed)
- Adjust expectations if structural market shifts detected

---

## Risk Management

### Rollback Strategy

**Each milestone includes:**
- Git commit per change (easy to revert)
- Shadow testing before production
- Rollback plan documented
- Success metrics defined (objective go/no-go)

**Escalation Procedure:**
1. Minor issue (WR drop <1%): Monitor for 24h
2. Moderate issue (WR drop 1-2%): Rollback single milestone
3. Major issue (WR drop >2%): Rollback entire week
4. Critical issue (drawdown >20%): HALT bot, full audit

### Dependencies

**Milestones with dependencies:**
- 2.1 (Raise threshold) depends on 1.3 (Disable agents) - consensus quality improves first
- 3.1 (Reduce agents) depends on 1.3 (Identify underperformers) - data-driven removal
- 3.2 (Re-enable contrarian) depends on 2.3 (Lower entry threshold) - cheap entries validated

**Critical path:**
- Week 1 must complete before Week 2 (fixes before optimizations)
- Week 3 can overlap with Week 2 (architecture cleanup is independent)

### Resource Requirements

**Development Time:**
- Week 1: 11 hours (fixes and quick wins)
- Week 2: 9 hours (optimization tuning)
- Week 3: 9 hours (architecture simplification)
- Week 4: 10 hours (monitoring and automation)
- **Total:** ~40 hours over 4 weeks

**Testing Time:**
- Shadow testing: 2-5 days per milestone
- Validation: 100+ trades post-roadmap (~2 weeks)
- **Total:** ~6 weeks including validation

**Infrastructure:**
- VPS remains same (no hardware changes)
- Git branch: `research-implementation` (merge to main after validation)
- Backups: Daily state file snapshots during roadmap

---

## Communication Plan

### Stakeholder Updates

**Weekly Report (every Monday):**
- Milestones completed
- Win rate trend (rolling average)
- Issues encountered
- Next week priorities

**Milestone Alerts (immediate):**
- Milestone deployed to production
- Win rate change (±2%)
- Rollback triggered
- Critical issues (drawdown >25%)

### Documentation Updates

**After Roadmap Completion:**
- Update `CLAUDE.md` with new architecture (5 agents)
- Update `docs/STRATEGY.md` with optimized thresholds
- Archive old configs in `config/archived/`
- Create `CHANGELOG.md` entry for v13.0

---

## Post-Roadmap: Continuous Improvement

**After achieving 63-65% WR:**

1. **Monitor for 1 month** - Ensure stability (no regime-dependent results)
2. **Scale up position sizing** - Gradually increase from 5% to 7%
3. **Add new cryptos** - Test strategy on XRP, DOGE (if 15-min markets exist)
4. **Explore longer timeframes** - 30-min, 1-hour epochs (if edge persists)
5. **Open-source shadow system** - Share learnings with community

**Exit Conditions:**
- **Scale up:** WR >65% for 200+ trades, balance >$500
- **Pause:** WR drops <55% for 50+ trades (regime shift?)
- **Shutdown:** Drawdown exceeds 40% (strategy no longer viable)

---

## Conclusion

This roadmap transforms research insights into executable milestones, balancing risk and reward with clear success metrics and rollback plans.

**Key Principle:** Simplify first (remove what hurts), then optimize (improve what works).

**Expected Timeline:** 4 weeks implementation + 2 weeks validation = 6 weeks total

**Confidence Level:** HIGH (based on 48 research reports, statistical validation, and shadow testing framework)

**Next Step:** Begin Week 1 - Milestone 1.1 (Fix State Tracking Bugs)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-16
**Status:** APPROVED - Ready for implementation
