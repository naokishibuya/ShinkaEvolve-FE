import numpy as np
from dataclasses import dataclass


@dataclass
class ScenarioParameters:
    eq_sigmas: float       # NKY move in sigmas (negative = down)
    vol_sigmas: float      # vol change in sigmas
    fx_sigmas: float       # USDJPY move in sigmas
    ir_sigmas: float       # JGB yield move in sigmas
    crisis_intensity: float  # 0 = normal corr, 1 = crisis corr
    horizon_days: int      # 1–10, say


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
def propose_scenario(stats: HistoricalStats, config: dict) -> ScenarioParameters:
    """
    THIS is the function ShinkaEvolve will mutate.
    Initial version: simple hand-crafted rule.
    Later generations: AI will change this code.
    """
    # Very simple baseline: 5σ equity crash, 3σ vol spike, etc.
    horizon_days = config.get("horizon_days", 5)

    return ScenarioParameters(
        eq_sigmas=-5.0,
        vol_sigmas=+3.0,
        fx_sigmas=+2.0,
        ir_sigmas=+1.0,
        crisis_intensity=0.8,
        horizon_days=horizon_days,
    )
# EVOLVE-BLOCK-END


def run_experiment(stats: HistoricalStats = None, config: dict = None) -> tuple[dict, str]:
    """
    Run experiment - called by evaluate.py during evolution.

    Args:
        stats: Historical statistics for volatilities and correlations
        config: Configuration dict (e.g., horizon_days)

    Returns:
        (metrics_dict, feedback_text) tuple
    """
    from portfolio import make_base_nikkei_portfolio, make_hedged_portfolio
    from evaluate import evaluate_scenario

    # Use default config if not provided
    if config is None:
        config = {"horizon_days": 5}

    # Use default stats if not provided (for standalone testing)
    if stats is None:
        stats = HistoricalStats(
            eq_vol=0.012,
            vol_of_vol=0.02,
            fx_vol=0.006,
            ir_vol=0.0005,
            corr_normal=np.eye(4),
            corr_crisis=np.eye(4),
        )

    # Generate scenario using the evolving function
    params = propose_scenario(stats, config)

    # Create portfolios
    base_portfolio = make_base_nikkei_portfolio()
    hedged_portfolio = make_hedged_portfolio()

    # Evaluate the scenario
    fitness, result = evaluate_scenario(
        params, stats, base_portfolio, hedged_portfolio
    )

    # Build metrics dictionary
    metrics = {
        'fitness': float(fitness),
        'hedge_loss': float(result.hedge_loss),
        'base_loss': float(result.base_loss),
        'hedge_effectiveness': float(result.hedge_effectiveness),
        'plausibility_penalty': float(result.plaus_penalty),
        'eq_sigmas': float(params.eq_sigmas),
        'vol_sigmas': float(params.vol_sigmas),
        'fx_sigmas': float(params.fx_sigmas),
        'ir_sigmas': float(params.ir_sigmas),
        'crisis_intensity': float(params.crisis_intensity),
        'horizon_days': int(params.horizon_days),
    }

    # Generate feedback text
    from report import render_report
    feedback = render_report(result)

    return metrics, feedback


if __name__ == "__main__":
    # Test run
    metrics, feedback = run_experiment()
    print(feedback)
    print(f"\nMetrics: {metrics}")
