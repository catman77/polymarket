# Strategy Performance by Market Regime

**Status:** ⚠️ Insufficient Data

## Issue

No trades could be matched with regime classifications. Possible reasons:

1. **RegimeAgent not enabled** - Check `config/agent_config.py`
2. **No regime classifications in logs** - Bot may not be logging regime decisions
3. **Shadow trading database empty** - No resolved trades yet
4. **Timestamp mismatch** - Regime logs and trade timestamps don't overlap

## Next Steps

1. Verify RegimeAgent is enabled and logging classifications
2. Wait for 20+ resolved trades in shadow database
3. Re-run this analysis: `python3 scripts/research/strategy_by_regime.py`
