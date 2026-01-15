# Analytics Tools

Tools for monitoring and analyzing trading performance.

## Phase 1 Monitor

Tracks OrderBookAgent and FundingRateAgent performance to validate Phase 1 success criteria.

### Usage

```bash
# Monitor Phase 1 agent performance
python3 analytics/phase1_monitor.py

# Custom database path
python3 analytics/phase1_monitor.py --db path/to/trade_journal.db
```

### Success Criteria

The monitor checks Phase 1 agents against these criteria:

1. **50+ trades each** - Both OrderBook and FundingRate agents must participate in 50+ decisions
2. **+3-5% win rate improvement** - Phase 1 strategies must outperform baseline by 3-5%
3. **Valid votes** - All agents must be returning valid vote data
4. **No degradation** - Win rate must remain above 45%

### Output Example

```
====================================================================================================
                                   PHASE 1 AGENT MONITOR
                         OrderBookAgent + FundingRateAgent Performance
====================================================================================================

Agent Performance:
----------------------------------------------------------------------------------------------------
Agent                Votes    Conf     Quality  Up/Down      Resolved     Win Rate   Impact
----------------------------------------------------------------------------------------------------
OrderBookAgent       ✅ 75    68.5  % 82.3  % 42/33        60 (15p)     ✅ 63.3  %     +0.42
FundingRateAgent     ✅ 68    71.2  % 78.9  % 38/30        55 (13p)     ✅ 61.8  %     +0.38

Strategy Comparison (Baseline vs Phase 1):
----------------------------------------------------------------------------------------------------
Strategy Type             Trades     Win Rate        Avg P&L         Improvement
----------------------------------------------------------------------------------------------------
Baseline (no Phase 1)     120        54.2%           $+0.12          --
Phase 1 Strategies        95         58.9%           $+0.18          🟢 +4.7% WR

Win Rate Improvement: +4.7% (target: +3-5%)
P&L Improvement: $+0.06 per trade

Success Criteria:
----------------------------------------------------------------------------------------------------
✅ Both agents have 50+ votes (OrderBook: 75, FundingRate: 68)
✅ Win rate improvement +3-5% (actual: +4.7%)
✅ All agents returning valid votes
✅ No performance degradation (win rate 58.9% >= 45%)

====================================================================================================
```

### Metrics Explained

**Agent Performance:**
- **Votes** - Total number of decisions agent participated in
- **Conf** - Average confidence score (0-100%)
- **Quality** - Average quality score (0-100%)
- **Up/Down** - Number of Up vs Down votes
- **Resolved** - Completed trades (pending in parentheses)
- **Win Rate** - Percentage of correct predictions
- **Impact** - Weighted contribution to wins (positive = helpful, negative = harmful)

**Strategy Comparison:**
- **Baseline** - Strategies without Phase 1 agents (default, conservative, aggressive)
- **Phase 1** - Strategies with Phase 1 agents (orderbook_focused, funding_rate_focused, etc.)

**Success Status:**
- ✅ Criterion met
- ⏳ In progress / pending data
- ⚠️ Warning / marginally acceptable
- 🔴 Criterion not met

### Integration

Phase 1 monitor uses the same database as shadow trading system:

```python
from config import agent_config
db_path = agent_config.SHADOW_DB_PATH  # simulation/trade_journal.db
```

Data is automatically logged during live and shadow trading. No manual data entry required.

### Scheduling

For automated monitoring, add to cron:

```bash
# Monitor every hour
0 * * * * cd /opt/polymarket-autotrader && python3 analytics/phase1_monitor.py >> logs/phase1_monitor.log 2>&1
```

Or use systemd timer (recommended for production).
