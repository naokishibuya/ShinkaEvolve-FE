"""
Financial domain knowledge - instrument definitions.
Simplified for POC - uses realistic approximations.
"""

# Instrument definitions
# Each instrument has:
# - cost_pct: Cost as percentage of notional (simplified)
# - protection_factor: Protection effectiveness (0-1 scale)

INSTRUMENTS = {
    'put_otm': {
        'name': 'Out-of-the-Money Put (95% strike)',
        'cost_pct': 0.5,         # 0.5% of notional
        'protection_factor': 0.70,  # Covers 70% of downside
        'description': 'Cheap protection, partial coverage'
    },
    
    'put_atm': {
        'name': 'At-the-Money Put (100% strike)',
        'cost_pct': 1.2,         # 1.2% of notional
        'protection_factor': 0.95,  # Covers 95% of downside
        'description': 'Expensive but comprehensive protection'
    },
    
    'collar': {
        'name': 'Collar (95% put, 105% call)',
        'cost_pct': 0.3,         # Net cost (put - call premium)
        'protection_factor': 0.65,  # Limited protection
        'description': 'Cost-efficient but caps upside'
    },
    
    'put_deep_otm': {
        'name': 'Deep Out-of-the-Money Put (90% strike)',
        'cost_pct': 0.2,         # Very cheap
        'protection_factor': 0.50,  # Tail risk only
        'description': 'Very cheap, only covers crashes'
    }
}


# Simplified cost model (for POC)
# In production, would use Black-Scholes or market data
def get_instrument_cost(instrument_name: str, notional: float) -> float:
    """Get cost of one unit of instrument."""
    if instrument_name not in INSTRUMENTS:
        return 0.0
    
    cost_pct = INSTRUMENTS[instrument_name]['cost_pct']
    return notional * cost_pct / 100.0