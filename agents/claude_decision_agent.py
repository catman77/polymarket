#!/usr/bin/env python3
"""
Claude-Powered Decision Agent

Uses Claude API to make real-time trading decisions with full market context.
More intelligent than rule-based agents - can reason about complex patterns.
"""

import os
import json
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Check if Anthropic SDK is available
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    log.warning("Anthropic SDK not installed - ClaudeAgent unavailable")


@dataclass
class ClaudeDecision:
    """Decision from Claude API"""
    direction: str  # "Up", "Down", or "Skip"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    raw_response: str


class ClaudeDecisionAgent:
    """
    Real-time AI decision agent using Claude API.
    
    Calls Claude Haiku (fast, cheap) or Sonnet (smarter) to make
    trading decisions based on compressed market data.
    """
    
    def __init__(self, 
                 model: str = "claude-3-5-haiku-20241022",  # Fast & cheap
                 max_tokens: int = 300):
        """
        Initialize Claude decision agent.
        
        Args:
            model: Claude model to use (haiku = fast/cheap, sonnet = smart/expensive)
            max_tokens: Max tokens for response (keep low for speed/cost)
        """
        self.model = model
        self.max_tokens = max_tokens
        
        if not CLAUDE_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # Load API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        
        log.info(f"ClaudeDecisionAgent initialized with {model}")
    
    def decide(self, 
               crypto: str,
               epoch_data: Dict) -> ClaudeDecision:
        """
        Make trading decision using Claude API.
        
        Args:
            crypto: BTC, ETH, SOL, or XRP
            epoch_data: Compressed market data
            
        Returns:
            ClaudeDecision with direction, confidence, reasoning
        """
        
        # Build compressed prompt
        prompt = self._build_decision_prompt(crypto, epoch_data)
        
        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower = more consistent
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse response
            raw_text = response.content[0].text
            decision = self._parse_response(raw_text)
            
            log.info(f"Claude decision: {decision.direction} @ {decision.confidence:.0%}")
            log.debug(f"Reasoning: {decision.reasoning}")
            
            return decision
            
        except Exception as e:
            log.error(f"Claude API error: {e}")
            # Return neutral on error
            return ClaudeDecision(
                direction="Skip",
                confidence=0.0,
                reasoning=f"API error: {e}",
                raw_response=""
            )
    
    def _build_decision_prompt(self, crypto: str, data: Dict) -> str:
        """
        Build token-efficient prompt with all relevant data.
        
        Optimized to be <1000 tokens while including everything Claude needs.
        """
        
        # Extract data
        epoch_time = data.get('time_in_epoch', 0)
        epoch_phase = "EARLY" if epoch_time < 300 else "MID" if epoch_time < 720 else "LATE"
        
        prices = data.get('prices', {})
        poly = data.get('polymarket', {})
        tech = data.get('technicals', {})
        ctx = data.get('context', {})
        
        prompt = f"""You are an expert crypto binary options trader on Polymarket. 
Make a decision for this 15-minute Up/Down market.

MARKET: {crypto} Up or Down
TIME: {epoch_time}s / 900s ({epoch_phase} phase)

EXCHANGE PRICES (last 5min):
{json.dumps(prices.get('exchanges', {}), indent=2)}
Changes: 5m={prices.get('5m_change', 'N/A')}, 15m={prices.get('15m_change', 'N/A')}, 1h={prices.get('1h_change', 'N/A')}

POLYMARKET PRICES:
Up: ${poly.get('up', 0.50):.2f} (pay this to win $1.00 if Up)
Down: ${poly.get('down', 0.50):.2f} (pay this to win $1.00 if Down)

TECHNICALS:
RSI (15m): {tech.get('rsi_15m', 'N/A')}
RSI (1h): {tech.get('rsi_1h', 'N/A')}  
Trend: {tech.get('trend', 'unknown')}

CONTEXT:
Recent performance: {ctx.get('recent_trades', 'N/A')}
Balance: {ctx.get('balance', 'N/A')}
Open positions: {ctx.get('open_positions', 'N/A')}

RESPOND IN THIS EXACT FORMAT:
DIRECTION: [Up/Down/Skip]
CONFIDENCE: [0-100]%
REASONING: [One concise sentence explaining your decision]

Key principles:
1. In bull trends, favor Up (don't fight momentum)
2. High confidence at any price beats low confidence cheap
3. Consider ALL exchange prices for confluence
4. Skip if unclear or conflicting signals
5. RSI >70 or <30 suggests reversal opportunity"""

        return prompt
    
    def _parse_response(self, response: str) -> ClaudeDecision:
        """
        Parse Claude's response into structured decision.
        
        Expected format:
        DIRECTION: Up
        CONFIDENCE: 75%
        REASONING: All 3 exchanges showing upward momentum, bull trend confirmed
        """
        
        lines = response.strip().split('\n')
        
        direction = "Skip"
        confidence = 0.0
        reasoning = "Unable to parse response"
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("DIRECTION:"):
                direction = line.split(":", 1)[1].strip()
                
            elif line.startswith("CONFIDENCE:"):
                conf_str = line.split(":", 1)[1].strip()
                # Extract percentage
                conf_str = conf_str.replace('%', '').strip()
                try:
                    confidence = float(conf_str) / 100.0
                except:
                    confidence = 0.0
                    
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
        
        return ClaudeDecision(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            raw_response=response
        )


# Example usage
if __name__ == "__main__":
    # Test the agent
    import time
    
    logging.basicConfig(level=logging.INFO)
    
    # Mock data
    test_data = {
        'time_in_epoch': 134,
        'prices': {
            'exchanges': {
                'binance': 95450,
                'kraken': 95440,
                'coinbase': 95460
            },
            '5m_change': '+0.16%',
            '15m_change': '+0.42%',
            '1h_change': '+1.2%'
        },
        'polymarket': {
            'up': 0.55,
            'down': 0.48
        },
        'technicals': {
            'rsi_15m': 58,
            'rsi_1h': 62,
            'trend': 'bull +0.45'
        },
        'context': {
            'recent_trades': '2W 1L (67% WR)',
            'balance': '$51.31',
            'open_positions': '0/4'
        }
    }
    
    try:
        agent = ClaudeDecisionAgent()
        decision = agent.decide("BTC", test_data)
        
        print(f"\n{'='*60}")
        print(f"CLAUDE DECISION:")
        print(f"  Direction: {decision.direction}")
        print(f"  Confidence: {decision.confidence:.0%}")
        print(f"  Reasoning: {decision.reasoning}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ANTHROPIC_API_KEY is set in environment")
