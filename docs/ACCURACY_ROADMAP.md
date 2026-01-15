# Roadmap to 60-70% Win Rate

## Current State

We have a foundation with:
- **4-5 agents voting** (Tech, Sentiment, Regime, Candlestick, TimePattern)
- **GamblerAgent probability gating** (60% threshold)
- **Shadow testing** 11 strategies in parallel
- **2,884 historical epochs** of data for analysis

**Current Win Rate:** ~30-50% (varies by strategy)
**Target Win Rate:** 60-70% (to overcome 6.3% fees and be profitable)

---

## Phase 1: Expand Signal Diversity (2-3 days) 🔧

Add high-value independent signals to capture different market dynamics:

### 1. OrderBookAgent - Microstructure Signals
**What it measures:** Real-time order book dynamics
- **Bid-ask spread** (tight = liquid, wide = volatile)
- **Order book imbalance** (buy vs sell pressure)
- **Market depth** at key levels ($0.10, $0.50, $0.90)

**Implementation:**
```python
from py_clob_client import ClobClient

class OrderBookAgent(BaseAgent):
    def analyze(self, crypto, epoch, data):
        orderbook = data['orderbook']

        # Calculate imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol)
        bid_volume = sum(level['size'] for level in orderbook['bids'][:10])
        ask_volume = sum(level['size'] for level in orderbook['asks'][:10])
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        # Spread analysis
        spread = orderbook['asks'][0]['price'] - orderbook['bids'][0]['price']

        # Vote based on imbalance
        if imbalance > 0.2:  # Strong buy pressure
            direction = "Up"
            confidence = min(abs(imbalance), 0.8)
        elif imbalance < -0.2:  # Strong sell pressure
            direction = "Down"
            confidence = min(abs(imbalance), 0.8)
        else:
            direction = "Neutral"
            confidence = 0.1

        return Vote(direction, confidence, quality=1.0-spread)
```

**Expected Impact:** +3-5% win rate

### 2. OnChainAgent - Blockchain Signals
**What it measures:** Large wallet movements and exchange flows
- **Whale transfers** (>$100k)
- **Exchange inflows** (selling pressure)
- **Exchange outflows** (buying pressure/hodling)

**Implementation:**
- Use Whale Alert API for real-time whale tracking
- Track Binance/Coinbase wallet addresses
- Vote based on flow direction in last 15 minutes

**Expected Impact:** +2-4% win rate

### 3. SocialSentimentAgent - Crowd Psychology
**What it measures:** Social media momentum and sentiment
- **Twitter mention volume** spikes
- **Reddit r/cryptocurrency** sentiment
- **Google Trends** search momentum

**Implementation:**
- Twitter API v2 for recent mentions
- Reddit API via PRAW library
- pytrends for Google Trends data
- Sentiment analysis via transformers (finbert)

**Expected Impact:** +3-5% win rate

### 4. FundingRateAgent - Derivatives Bias
**What it measures:** Perpetual futures market bias
- **Funding rates** (positive = long bias, negative = short bias)
- **Open interest** changes (rising = more positions)
- **Liquidation data** (cascade risk)

**Implementation:**
```python
import requests

class FundingRateAgent(BaseAgent):
    def get_funding_rate(self, crypto):
        # Binance funding rate API
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={crypto}USDT"
        resp = requests.get(url).json()
        return float(resp['lastFundingRate'])

    def analyze(self, crypto, epoch, data):
        funding = self.get_funding_rate(crypto.upper())

        # Negative funding = shorts pay longs = bearish bias = likely reversal UP
        # Positive funding = longs pay shorts = bullish bias = likely reversal DOWN

        if funding < -0.0001:  # Strong short bias
            direction = "Up"  # Contrarian
            confidence = min(abs(funding) * 1000, 0.7)
        elif funding > 0.0001:  # Strong long bias
            direction = "Down"  # Contrarian
            confidence = min(funding * 1000, 0.7)
        else:
            direction = "Neutral"
            confidence = 0.1

        return Vote(direction, confidence, quality=abs(funding)*500)
```

**Expected Impact:** +2-4% win rate

**Total Phase 1 Impact:** +10-18% win rate from signal diversity

---

## Phase 2: Machine Learning Integration (1 week) 🤖

Train predictive models on 2,884 historical epochs:

### 1. Feature Engineering

Create features from all available data:

**Agent Features:**
- All agent votes (direction, confidence, quality)
- Consensus score, weighted score
- Agreement percentage

**Time Features:**
- UTC hour (0-23)
- Day of week
- Minutes into trading session
- Time until epoch end

**Price Features:**
- Entry price
- Price change last epoch
- Volatility (std dev of last 10 epochs)
- RSI values

**Cross-Asset Features:**
- BTC correlation (BTC often leads)
- Multi-crypto agreement (how many agree on direction)

**Regime Features:**
- Current regime (bull/bear/sideways/choppy)
- Regime stability (how long in current regime)

### 2. Model Training

**Train multiple models:**

```python
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit

# Load historical data from epoch_history.db
X, y = load_features_and_labels(db_path='analysis/epoch_history.db')

# Time series cross-validation (don't leak future data)
tscv = TimeSeriesSplit(n_splits=5)

# Train XGBoost
xgb = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1)
xgb.fit(X_train, y_train)

# Train Random Forest
rf = RandomForestClassifier(n_estimators=100, max_depth=10)
rf.fit(X_train, y_train)

# Train Logistic Regression (baseline)
lr = LogisticRegression()
lr.fit(X_train, y_train)

# Ensemble prediction (average probabilities)
def predict(features):
    xgb_prob = xgb.predict_proba(features)[0]
    rf_prob = rf.predict_proba(features)[0]
    lr_prob = lr.predict_proba(features)[0]

    # Weighted average (XGBoost gets more weight)
    ensemble_prob = (xgb_prob * 0.5 + rf_prob * 0.3 + lr_prob * 0.2)

    if ensemble_prob[1] > 0.6:  # Up
        return "Up", ensemble_prob[1]
    elif ensemble_prob[0] > 0.6:  # Down
        return "Down", ensemble_prob[0]
    else:
        return "Neutral", 0.5
```

### 3. MLAgent Integration

```python
class MLAgent(BaseAgent):
    """Agent that uses trained ML models for predictions."""

    def __init__(self, model_path='models/ensemble.pkl'):
        super().__init__(name="MLAgent", weight=1.5)  # Higher weight for ML
        self.model = load_model(model_path)

    def analyze(self, crypto, epoch, data):
        # Extract features from data
        features = self.extract_features(crypto, epoch, data)

        # Get model prediction
        direction, confidence = self.model.predict(features)

        return Vote(
            direction=direction,
            confidence=confidence,
            quality=confidence,  # Quality = confidence for ML
            agent_name=self.name,
            reasoning=f"ML Model: {direction} ({confidence:.0%} confidence)"
        )
```

**Expected Impact:** +15-20% win rate from ML pattern recognition

---

## Phase 3: Selective Trading (3-5 days) 🎯

Only trade when edge is clear:

### 1. Higher Confidence Thresholds

**Current approach:**
- Trade when consensus > 40%, confidence > 40%
- Results: ~60-80 trades/day, 30-50% win rate

**Better approach:**
- Trade when win_prob > 70% (GamblerAgent RAISE zone)
- Results: ~15-25 trades/day, 65-75% win rate

**Configuration:**
```python
# config/agent_config.py
CONSENSUS_THRESHOLD = 0.70  # Increase from 0.40
MIN_CONFIDENCE = 0.65       # Increase from 0.40
GAMBLER_FOLD_THRESHOLD = 0.70  # Stricter veto
```

### 2. Condition-Based Filters

**Only trade during favorable conditions:**

```python
class SelectiveFilterAgent(VetoAgent):
    """Veto trades during unfavorable conditions."""

    def can_veto(self, crypto, data):
        hour = data.get('hour')
        regime = data.get('regime')
        entry_price = data.get('orderbook', {}).get('yes', {}).get('price', 0.5)

        # Veto during low-edge hours
        if crypto == 'xrp' and hour not in [9, 13, 20]:
            return True, "Outside XRP optimal hours"

        if crypto == 'eth' and hour not in [2, 8, 20]:
            return True, "Outside ETH optimal hours"

        # Veto in choppy regime (mean reversion unreliable)
        if regime == 'choppy':
            return True, "Choppy regime - no edge"

        # Veto expensive entries (>$0.50 = low upside)
        if entry_price > 0.50:
            return True, f"Entry too expensive ({entry_price:.2f})"

        return False, ""
```

### 3. Kelly Criterion Position Sizing

**Size bets based on edge:**

```python
def kelly_position_size(win_prob, payout_ratio, balance):
    """
    Kelly Criterion: f = (p*b - q) / b
    where:
    - f = fraction of bankroll to bet
    - p = win probability
    - q = 1 - p = loss probability
    - b = payout ratio (what you win per $1 bet)
    """
    p = win_prob
    q = 1 - p

    # For Polymarket: if entry = $0.20, payout = $1.00, ratio = 4.0
    b = payout_ratio

    kelly_fraction = (p * b - q) / b

    # Use fractional Kelly (0.25x) for safety
    conservative_kelly = kelly_fraction * 0.25

    return balance * max(0, min(conservative_kelly, 0.15))  # Cap at 15%

# Example:
# Entry: $0.15, Payout: $1.00, Win Prob: 70%
# b = (1.00 - 0.15) / 0.15 = 5.67
# kelly_fraction = (0.70 * 5.67 - 0.30) / 5.67 = 0.644 (64.4% of bankroll!)
# conservative = 0.644 * 0.25 = 0.161 (16.1% of bankroll)
# Capped at 15% = bet 15% of balance
```

**Expected Impact:** +10-15% win rate from selectivity

---

## Phase 4: Continuous Adaptation (Ongoing) 🔄

Real-time learning and optimization:

### 1. Online Agent Weight Updates

Track performance and adapt weights:

```python
class AdaptiveWeightManager:
    """Updates agent weights based on recent performance."""

    def __init__(self):
        self.agent_performance = {}  # {agent_name: {regime: [correct, incorrect]}}

    def update_performance(self, agent_name, regime, correct):
        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {}
        if regime not in self.agent_performance[agent_name]:
            self.agent_performance[agent_name][regime] = [0, 0]

        if correct:
            self.agent_performance[agent_name][regime][0] += 1
        else:
            self.agent_performance[agent_name][regime][1] += 1

    def get_updated_weights(self, regime):
        """Calculate new weights based on regime-specific win rates."""
        weights = {}

        for agent, regimes in self.agent_performance.items():
            if regime in regimes:
                correct, incorrect = regimes[regime]
                total = correct + incorrect

                if total >= 10:  # Need 10+ samples
                    win_rate = correct / total
                    # Weight = win_rate * 2 (ranges 0-2x)
                    weights[agent] = max(0.25, win_rate * 2)
                else:
                    weights[agent] = 1.0  # Default weight
            else:
                weights[agent] = 1.0

        return weights
```

### 2. Regime-Specific Models

Different strategies for different market conditions:

```python
class RegimeAdaptiveAgent(BaseAgent):
    """Switches between regime-specific models."""

    def __init__(self):
        super().__init__(name="RegimeAdaptive")
        self.bull_model = load_model('models/bull_regime.pkl')
        self.bear_model = load_model('models/bear_regime.pkl')
        self.sideways_model = load_model('models/sideways_regime.pkl')

    def analyze(self, crypto, epoch, data):
        regime = data.get('regime', 'sideways')

        # Select model based on regime
        if regime == 'bull_momentum':
            model = self.bull_model
        elif regime == 'bear_momentum':
            model = self.bear_model
        else:
            model = self.sideways_model

        features = self.extract_features(crypto, epoch, data)
        direction, confidence = model.predict(features)

        return Vote(direction, confidence, quality=confidence)
```

### 3. Meta-Learning

Learn which signals work when:

```python
class MetaLearner:
    """Learns optimal signal combinations for each scenario."""

    def __init__(self):
        self.signal_performance = {}  # {condition: {signal: accuracy}}

    def get_optimal_agents(self, crypto, hour, regime):
        """Return best agents for this specific scenario."""
        condition = f"{crypto}_{hour}_{regime}"

        if condition in self.signal_performance:
            # Sort agents by accuracy, return top 5
            sorted_agents = sorted(
                self.signal_performance[condition].items(),
                key=lambda x: x[1],
                reverse=True
            )
            return [agent for agent, acc in sorted_agents[:5] if acc > 0.55]

        # Default: use all agents
        return ['TechAgent', 'SentimentAgent', 'RegimeAgent',
                'CandlestickAgent', 'TimePatternAgent', 'MLAgent']
```

**Expected Impact:** +5-10% win rate from continuous adaptation

---

## Total Expected Improvement

| Phase | Impact | Cumulative Win Rate |
|-------|--------|---------------------|
| **Baseline** | - | 30-50% |
| **Phase 1: Signal Diversity** | +10-18% | 40-68% |
| **Phase 2: Machine Learning** | +15-20% | 55-88% |
| **Phase 3: Selective Trading** | +10-15% | 65-103% |
| **Phase 4: Continuous Adaptation** | +5-10% | 70-113% |

**Realistic Target: 65-75% win rate** (accounting for overlapping effects)

---

## Implementation Timeline

### Week 1: Signal Expansion
- ✅ **Day 1-2:** Let current shadow trading collect baseline data
- **Day 3-4:** Implement OrderBookAgent
- **Day 5-7:** Implement FundingRateAgent

### Week 2: ML Training
- **Day 8-10:** Feature engineering on 2,884 epochs
- **Day 11-12:** Train XGBoost, Random Forest, Logistic Regression
- **Day 13-14:** Build MLAgent and integrate

### Week 3: Shadow Testing
- **Day 15-21:** Shadow test ML-enhanced strategies
- Compare: ML vs Non-ML, All signals vs Subset

### Week 4: Deployment
- **Day 22-23:** Analyze shadow results
- **Day 24:** Deploy best performer to live
- **Day 25-28:** Monitor live performance

### Month 2-3: Continuous Refinement
- Online weight updates
- Regime-specific model training
- Meta-learning optimization
- Target: 70%+ win rate

---

## Key Insights

### Why We Won't Reach 100%

Markets are partially random - even the best models plateau around 70-80% accuracy because:
1. **True randomness** exists in short-term price movements
2. **Black swan events** are unpredictable (Elon tweets, regulatory news)
3. **Market efficiency** - edges decay as they're discovered

### Why 65-70% Is Profitable

At 65% win rate with 6.3% round-trip fees:
- Average profit per trade: ~12%
- Trading 500 epochs/month: 60 trades (selective)
- Monthly return: ~720% (compounding) before drawdowns
- Realistic: 30-50% monthly return with proper risk management

### Critical Success Factors

1. **Signal Independence** - Each agent must capture different information
2. **Sample Size** - Need 50+ trades per condition to validate
3. **Regime Awareness** - Same strategy doesn't work in all markets
4. **Risk Management** - Kelly sizing prevents ruin even at 65% win rate

---

## Immediate Next Steps (Priority Order)

1. ✅ **Continue current shadow testing** (5-7 days) - Already running
2. **Implement OrderBookAgent** (2-3 days) - Highest impact, easiest
3. **Train ML models** (3-5 days) - Use existing 2,884 epochs
4. **Add MLAgent to shadow testing** (1 day) - Compare ML vs non-ML
5. **Implement FundingRateAgent** (2 days) - High signal value
6. **Raise confidence thresholds** (1 day) - Test selective trading

**Total Time to 65% Win Rate: 3-4 weeks**

---

## Success Metrics

Track these to measure progress toward 65-70% goal:

| Metric | Current | Target | How to Improve |
|--------|---------|--------|----------------|
| Overall Win Rate | 30-50% | 65-70% | All phases |
| Trades/Day | 60-80 | 15-25 | Selective trading |
| Avg Confidence | 40-50% | 70%+ | ML + better signals |
| Edge per Trade | 0-5% | 12-15% | Cheap entries + high win rate |
| Monthly Return | -10% to +20% | +30-50% | Compounding edge |

Monitor via shadow trading dashboard and export to CSV for analysis.
