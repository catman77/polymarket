#!/usr/bin/env python3
"""
Strategy Configuration Library

Defines strategy configurations for shadow trading simulation.
Each configuration represents a different approach to trading decisions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional
import json


@dataclass
class StrategyConfig:
    """
    Configuration for a trading strategy.
    
    Attributes:
        name: Unique strategy identifier
        description: Human-readable description
        consensus_threshold: Minimum weighted score to trade (0-1)
        min_confidence: Minimum average agent confidence (0-1)
        min_individual_confidence: Minimum per-agent confidence (0-1)
        agent_weights: Base weights for each agent
        adaptive_weights: Enable performance-based weight adjustment
        regime_adjustment_enabled: Enable regime-based weight adjustments
        tech_config: Override TECH_* config settings
        sentiment_config: Override SENTIMENT_* config settings
        regime_config: Override REGIME_* config settings
        risk_config: Override RISK_* config settings
        max_position_pct: Max position size as % of balance
        max_same_direction: Max positions in same direction
        mode: Deployment mode (log_only, conservative, moderate, aggressive)
        created: Creation timestamp
        is_live: True if this strategy controls real bot, False if shadow
    """
    name: str
    description: str

    # Core thresholds
    consensus_threshold: float = 0.40
    min_confidence: float = 0.40
    min_individual_confidence: float = 0.30

    # Agent weights (base multipliers before adaptive adjustment)
    agent_weights: Dict[str, float] = field(default_factory=lambda: {
        'TechAgent': 1.0,
        'SentimentAgent': 1.0,
        'RegimeAgent': 1.0,
        'CandlestickAgent': 1.0
    })

    # Features
    adaptive_weights: bool = True
    regime_adjustment_enabled: bool = True

    # Agent-specific config overrides
    tech_config: Optional[Dict] = None
    sentiment_config: Optional[Dict] = None
    regime_config: Optional[Dict] = None
    risk_config: Optional[Dict] = None

    # Risk management
    max_position_pct: float = 0.15
    max_same_direction: int = 3

    # Deployment mode
    mode: str = 'moderate'

    # Metadata
    created: datetime = field(default_factory=datetime.now)
    is_live: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        # Convert datetime to ISO format
        data['created'] = data['created'].isoformat() if isinstance(data['created'], datetime) else data['created']
        return json.dumps(data, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyConfig':
        """Create from dictionary."""
        # Convert ISO string back to datetime
        if isinstance(data.get('created'), str):
            data['created'] = datetime.fromisoformat(data['created'])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'StrategyConfig':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Pre-defined strategy templates
STRATEGY_LIBRARY = {
    'default': StrategyConfig(
        name='default',
        description='Current production strategy (moderate thresholds)',
        consensus_threshold=0.40,
        min_confidence=0.40,
        min_individual_confidence=0.30,
        is_live=True  # This is the live bot's config
    ),

    'conservative': StrategyConfig(
        name='conservative',
        description='High thresholds - fewer, higher-quality trades',
        consensus_threshold=0.75,
        min_confidence=0.60,
        min_individual_confidence=0.40,
        max_position_pct=0.10,
        agent_weights={
            'TechAgent': 1.0,
            'SentimentAgent': 1.0,
            'RegimeAgent': 1.2,  # Boost regime awareness
            'CandlestickAgent': 1.0
        }
    ),

    'aggressive': StrategyConfig(
        name='aggressive',
        description='Lower thresholds - more trades, higher risk',
        consensus_threshold=0.55,
        min_confidence=0.45,
        min_individual_confidence=0.25,
        max_position_pct=0.20,
        agent_weights={
            'TechAgent': 1.2,
            'SentimentAgent': 1.2,
            'RegimeAgent': 0.8,  # Less regime caution
            'CandlestickAgent': 1.0
        }
    ),

    'contrarian_focused': StrategyConfig(
        name='contrarian_focused',
        description='Boost sentiment agent for contrarian signals',
        consensus_threshold=0.40,
        min_confidence=0.40,
        min_individual_confidence=0.30,
        agent_weights={
            'TechAgent': 0.7,
            'SentimentAgent': 1.5,  # Boost contrarian
            'RegimeAgent': 1.0,
            'CandlestickAgent': 0.8
        },
        sentiment_config={
            'SENTIMENT_CONTRARIAN_MAX_ENTRY': 0.25,  # Allow more expensive entries
            'SENTIMENT_CONTRARIAN_PRICE_THRESHOLD': 0.65  # Lower threshold (>65% = contrarian)
        }
    ),

    'momentum_focused': StrategyConfig(
        name='momentum_focused',
        description='Boost tech agent for momentum signals',
        consensus_threshold=0.40,
        min_confidence=0.40,
        min_individual_confidence=0.30,
        agent_weights={
            'TechAgent': 1.5,  # Boost momentum
            'SentimentAgent': 0.7,
            'RegimeAgent': 1.2,
            'CandlestickAgent': 1.0
        },
        tech_config={
            'TECH_CONFLUENCE_THRESHOLD': 0.0010,  # Lower bar (0.10% instead of 0.15%)
            'TECH_MIN_EXCHANGES_AGREE': 2  # Keep at 2
        }
    ),

    'no_regime_adjustment': StrategyConfig(
        name='no_regime_adjustment',
        description='Disable regime-based weight adjustments',
        consensus_threshold=0.40,
        min_confidence=0.40,
        min_individual_confidence=0.30,
        regime_adjustment_enabled=False,
        agent_weights={
            'TechAgent': 1.0,
            'SentimentAgent': 1.0,
            'RegimeAgent': 1.0,
            'CandlestickAgent': 1.0
        }
    ),

    'equal_weights_static': StrategyConfig(
        name='equal_weights_static',
        description='All agents equal weight, no adaptive adjustments',
        consensus_threshold=0.40,
        min_confidence=0.40,
        min_individual_confidence=0.30,
        adaptive_weights=False,
        regime_adjustment_enabled=False,
        agent_weights={
            'TechAgent': 1.0,
            'SentimentAgent': 1.0,
            'RegimeAgent': 1.0,
            'CandlestickAgent': 1.0
        }
    ),

    'high_confidence_only': StrategyConfig(
        name='high_confidence_only',
        description='Extreme quality filter - only highest confidence trades',
        consensus_threshold=0.80,
        min_confidence=0.70,
        min_individual_confidence=0.50,
        max_position_pct=0.20,  # Larger bets when confident
        agent_weights={
            'TechAgent': 1.0,
            'SentimentAgent': 1.0,
            'RegimeAgent': 1.5,  # Boost regime alignment
            'CandlestickAgent': 1.0
        }
    ),

    'low_barrier': StrategyConfig(
        name='low_barrier',
        description='Lower thresholds to capture more opportunities',
        consensus_threshold=0.35,
        min_confidence=0.35,
        min_individual_confidence=0.20,
        max_position_pct=0.10,  # Smaller bets due to lower confidence
        agent_weights={
            'TechAgent': 1.0,
            'SentimentAgent': 1.0,
            'RegimeAgent': 1.0,
            'CandlestickAgent': 1.0
        }
    )
}


def get_strategy(name: str) -> StrategyConfig:
    """
    Get strategy config by name.
    
    Args:
        name: Strategy name from STRATEGY_LIBRARY
        
    Returns:
        StrategyConfig instance
        
    Raises:
        KeyError: If strategy not found
    """
    if name not in STRATEGY_LIBRARY:
        available = ', '.join(STRATEGY_LIBRARY.keys())
        raise KeyError(f"Strategy '{name}' not found. Available: {available}")
    
    return STRATEGY_LIBRARY[name]


def list_strategies() -> list:
    """
    List all available strategy names.
    
    Returns:
        List of strategy names
    """
    return list(STRATEGY_LIBRARY.keys())


def save_strategy(config: StrategyConfig, filepath: str):
    """
    Save strategy config to JSON file.
    
    Args:
        config: StrategyConfig to save
        filepath: Path to save JSON file
    """
    with open(filepath, 'w') as f:
        f.write(config.to_json())


def load_strategy(filepath: str) -> StrategyConfig:
    """
    Load strategy config from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        StrategyConfig instance
    """
    with open(filepath, 'r') as f:
        return StrategyConfig.from_json(f.read())
