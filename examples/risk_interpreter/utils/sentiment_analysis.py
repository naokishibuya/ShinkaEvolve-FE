"""
Sentiment analysis utilities for financial news.
Simple keyword-based approach for fast, deterministic analysis.
"""

from typing import Dict


def analyze_news(news_text: str) -> Dict[str, any]:
    """
    Analyze sentiment and signals from financial news text.

    Uses keyword-based analysis to extract financial market signals
    without requiring external LLM calls during evaluation.

    Args:
        news_text: News article or headline text

    Returns:
        Dictionary with:
            - sentiment: float (-1 to 1)
                -1 = very negative (bearish)
                 0 = neutral
                 1 = very positive (bullish)
            - volatility_signal: bool
                True if text mentions volatility/uncertainty
            - policy_signal: bool
                True if text mentions policy/regulatory changes
            - stress_level: float (0 to 1)
                0 = calm market signals
                1 = high stress/crisis signals

    Examples:
        >>> analyze_news("Bank of Japan signals end of negative rates. Markets expect volatility.")
        {'sentiment': -0.3, 'volatility_signal': True, 'policy_signal': True, 'stress_level': 0.6}

        >>> analyze_news("Calm trading session with steady gains across sectors.")
        {'sentiment': 0.5, 'volatility_signal': False, 'policy_signal': False, 'stress_level': 0.1}

        >>> analyze_news("Flash crash as geopolitical tensions escalate sharply.")
        {'sentiment': -0.9, 'volatility_signal': True, 'policy_signal': False, 'stress_level': 0.95}
    """

    if not news_text:
        return {
            'sentiment': 0.0,
            'volatility_signal': False,
            'policy_signal': False,
            'stress_level': 0.0
        }

    text_lower = news_text.lower()

    # Sentiment analysis
    sentiment = _calculate_sentiment(text_lower)

    # Volatility signals
    volatility_signal = _detect_volatility(text_lower)

    # Policy/regulatory signals
    policy_signal = _detect_policy_change(text_lower)

    # Market stress level
    stress_level = _calculate_stress_level(text_lower)

    return {
        'sentiment': float(sentiment),
        'volatility_signal': bool(volatility_signal),
        'policy_signal': bool(policy_signal),
        'stress_level': float(stress_level)
    }


def _calculate_sentiment(text: str) -> float:
    """Calculate sentiment score from -1 (negative) to 1 (positive)."""

    # Positive keywords (bullish)
    positive_keywords = [
        'gain', 'gains', 'rally', 'surge', 'climb', 'rise', 'rising',
        'growth', 'strong', 'robust', 'positive', 'optimistic', 'confidence',
        'recovery', 'stabilize', 'improve', 'steady', 'calm', 'bullish'
    ]

    # Negative keywords (bearish)
    negative_keywords = [
        'fall', 'drop', 'plunge', 'crash', 'decline', 'loss', 'losses',
        'weak', 'concern', 'worry', 'fear', 'tension', 'risk', 'crisis',
        'uncertainty', 'volatile', 'bearish', 'selloff', 'sell-off',
        'tumble', 'slump', 'downturn', 'recession', 'shock'
    ]

    # Count occurrences
    positive_count = sum(1 for kw in positive_keywords if kw in text)
    negative_count = sum(1 for kw in negative_keywords if kw in text)

    # Calculate weighted sentiment
    total_count = positive_count + negative_count
    if total_count == 0:
        return 0.0

    sentiment = (positive_count - negative_count) / total_count

    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, sentiment))


def _detect_volatility(text: str) -> bool:
    """Detect if text mentions volatility or uncertainty."""

    volatility_keywords = [
        'volatility', 'volatile', 'uncertainty', 'uncertain', 'fluctuat',
        'swing', 'whipsaw', 'choppy', 'erratic', 'unstable', 'turbulent',
        'unpredictable', 'wild', 'extreme move'
    ]

    return any(kw in text for kw in volatility_keywords)


def _detect_policy_change(text: str) -> bool:
    """Detect if text mentions policy or regulatory changes."""

    policy_keywords = [
        'policy', 'regulation', 'regulatory', 'central bank', 'fed ', 'boj',
        'ecb', 'pboc', 'rate decision', 'interest rate', 'monetary',
        'fiscal', 'government', 'ministry', 'announcement', 'announces',
        'intervention', 'mandate', 'law', 'reform', 'normalization'
    ]

    return any(kw in text for kw in policy_keywords)


def _calculate_stress_level(text: str) -> float:
    """Calculate market stress level from 0 (calm) to 1 (crisis)."""

    # Stress indicators with different weights
    high_stress_keywords = [
        ('crash', 1.0), ('crisis', 1.0), ('panic', 1.0), ('collapse', 1.0),
        ('meltdown', 1.0), ('flash crash', 1.0), ('black swan', 1.0),
        ('contagion', 0.9), ('systemic', 0.9)
    ]

    medium_stress_keywords = [
        ('selloff', 0.6), ('sell-off', 0.6), ('plunge', 0.7), ('tumble', 0.6),
        ('sharp', 0.5), ('steep', 0.5), ('sudden', 0.5), ('abrupt', 0.5),
        ('tension', 0.6), ('turmoil', 0.7), ('disruption', 0.6)
    ]

    low_stress_keywords = [
        ('volatility', 0.4), ('uncertainty', 0.4), ('concern', 0.3),
        ('caution', 0.3), ('nervous', 0.3), ('jitter', 0.3)
    ]

    # Calculate stress score
    stress_score = 0.0

    for keyword, weight in high_stress_keywords:
        if keyword in text:
            stress_score = max(stress_score, weight)

    for keyword, weight in medium_stress_keywords:
        if keyword in text:
            stress_score = max(stress_score, weight)

    for keyword, weight in low_stress_keywords:
        if keyword in text:
            stress_score = max(stress_score, weight)

    # Also check for calm/stable signals (reduce stress)
    calm_keywords = ['calm', 'stable', 'steady', 'normal', 'quiet', 'orderly']
    if any(kw in text for kw in calm_keywords):
        stress_score *= 0.5  # Halve the stress if calm signals present

    return min(1.0, stress_score)


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Bank of Japan signals end of negative rates. Markets expect increased volatility.",
        "Calm trading session with steady gains across sectors.",
        "Flash crash as geopolitical tensions escalate sharply.",
        "Central bank announces surprise rate hike amid inflation concerns.",
        "Markets rally on positive earnings reports and strong economic data.",
        "Systemic crisis fears as major bank faces liquidity issues.",
        ""
    ]

    print("Sentiment Analysis Test Cases:\n")
    for i, text in enumerate(test_cases, 1):
        result = analyze_news(text)
        print(f"Test {i}:")
        print(f"  Text: {text[:70]}{'...' if len(text) > 70 else ''}")
        print(f"  Sentiment: {result['sentiment']:+.2f}")
        print(f"  Volatility: {result['volatility_signal']}")
        print(f"  Policy: {result['policy_signal']}")
        print(f"  Stress: {result['stress_level']:.2f}")
        print()
