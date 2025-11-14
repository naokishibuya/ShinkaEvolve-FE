import numpy as np
from dataclasses import dataclass


@dataclass
class ScenarioParameters:
    """
    Each field is a move in 'sigma units', where sigma = daily volatility of that factor.
    Actual shock applied is: shock = sigmas * daily_vol * sqrt(horizon_days)
    """
    eq_sigmas: float           # Equity (i.e Nikkei 225) move in sigmas (negative = down)
    vol_sigmas: float          # vol change in sigmas
    fx_sigmas: float           # USDJPY move in sigmas
    ir_sigmas: float           # JGB yield move in sigmas
    crisis_intensity: float    # 0 = normal corr, 1 = crisis corr, in between
    horizon_days: int          # 1–10, say


@dataclass
class Instrument:
    name: str
    mtm_value: float           # current MTM value in JPY

    # factor sensitivities
    eq_delta: float = 0.0      # dV/d(eq_shock)  , ratio scaled by mtm_value
    eq_gamma: float = 0.0      # d²V/d(eq_shock)², ratio scaled by mtm_value
    eq_vega: float = 0.0       # dV/d(vol_shock) , ratio scaled by mtm_value
    fx_delta: float = 0.0      # dV/d(fx_shock)  , ratio scaled by mtm_value
    ir_dv01: float = 0.0       # dV/d(ir_shock)  , absolute JPY


@dataclass
class HistoricalStats:
    """Derived from time series offline."""
    eq_vol: float        # daily vol of NKY log returns
    vol_of_vol: float    # daily vol of implied vol changes
    fx_vol: float        # daily vol of USDJPY log returns
    ir_vol: float        # daily vol of 10Y JGB yield changes

    corr_normal: np.ndarray   # 4x4 correlation matrix (eq, vol, fx, ir)
    corr_crisis: np.ndarray   # 4x4 correlation matrix in crisis regime


# EVOLVE-BLOCK-START
def propose_scenario(instruments: list[Instrument], stats: HistoricalStats, config: dict = None) -> ScenarioParameters:
    """
    THIS is the function ShinkaEvolve will mutate.
    Initial version: simple hand-crafted rule.
    Later generations: AI will change this code.

    Args:
        instruments: Portfolio instruments (can inspect greeks, exposures)
        stats: Historical statistics (volatilities, correlations)
        config: Optional configuration dict
    """
    # Very simple baseline: 5σ equity crash, 3σ vol spike, etc.
    # (Future evolved versions can use instruments, stats, config to be smarter)
    return ScenarioParameters(
        eq_sigmas=-5.0,
        vol_sigmas=+3.0,
        fx_sigmas=+2.0,
        ir_sigmas=+1.0,
        crisis_intensity=0.8,
        horizon_days=5,
    )
# EVOLVE-BLOCK-END

def run_experiment(run_id: int = 0) -> dict:
    from scenario import evaluate_scenario
    return evaluate_scenario(run_id, propose_scenario)