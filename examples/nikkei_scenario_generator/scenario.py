"""
Scenario loading, portfolio construction, and evaluation infrastructure.
Contains all fixed code that the AI should not mutate.
"""
import json
import math
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from initial import ScenarioParameters, Instrument, HistoricalStats


@dataclass
class FactorShock:
    """One-step shock in our factor space."""
    eq_shock: float      # Nikkei return (e.g., -0.1 = -10%)
    vol_shock: float     # IV change (e.g., +0.10 = +10%)
    fx_shock: float      # USDJPY return (e.g., +0.05 = +5%)
    ir_shock: float      # JGB yield change (e.g., +0.01 = +1% or +100 bps)


@dataclass
class Portfolio:
    """Portfolio containing multiple instruments."""
    name: str
    instruments: list[Instrument]


def evaluate_scenario(run_id: int, propose_fn) -> dict:
    """Main entry point: load scenario, generate params, evaluate."""
    # Load scenario configuration
    portfolio_base, portfolio_hedged, stats, config = load_scenario(run_id)

    # Call the evolving function
    params = propose_fn(portfolio_hedged.instruments, stats, config)

    # Generate correlated factor shocks
    shock = generate_factor_shock(params, stats)

    # Calculate P&L for both portfolios
    base_pnl = calculate_portfolio_pnl(portfolio_base, shock)
    hedge_pnl = calculate_portfolio_pnl(portfolio_hedged, shock)

    # Calculate fitness
    plaus_penalty = sigma_penalty(params)
    base_loss = -base_pnl
    hedge_loss = -hedge_pnl
    hedge_effectiveness = base_loss - hedge_loss
    lam = config.get('lambda_penalty', 1e9)
    fitness = hedge_loss - lam * plaus_penalty

    # Return comprehensive metrics
    return {
        'fitness': float(fitness),
        'hedge_loss': float(hedge_loss),
        'base_loss': float(base_loss),
        'hedge_effectiveness': float(hedge_effectiveness),
        'plausibility_penalty': float(plaus_penalty),
        'eq_sigmas': float(params.eq_sigmas),
        'vol_sigmas': float(params.vol_sigmas),
        'fx_sigmas': float(params.fx_sigmas),
        'ir_sigmas': float(params.ir_sigmas),
        'crisis_intensity': float(params.crisis_intensity),
        'horizon_days': int(params.horizon_days),
        'eq_shock': float(shock.eq_shock),
        'vol_shock': float(shock.vol_shock),
        'fx_shock': float(shock.fx_shock),
        'ir_shock': float(shock.ir_shock),
        'base_pnl': float(base_pnl),
        'hedge_pnl': float(hedge_pnl),
    }


def load_scenario(run_id: int) -> tuple:
    """Load scenario configuration from JSON file."""
    scenario_file = str(Path(__file__).parent / "scenarios.json")

    try:
        with open(scenario_file) as f:
            scenarios = json.load(f)  # Load as array
        data = scenarios[run_id]  # Direct array access
    except Exception as e:
        raise Exception(f"Error loading scenarios.json: {e}") from e

    # Parse HistoricalStats
    stats_data = data['stats']
    stats = HistoricalStats(
        eq_vol=stats_data['eq_vol'],
        vol_of_vol=stats_data['vol_of_vol'],
        fx_vol=stats_data['fx_vol'],
        ir_vol=stats_data['ir_vol'],
        corr_normal=np.array(stats_data['corr_normal']),
        corr_crisis=np.array(stats_data['corr_crisis']),
    )

    # Parse portfolios
    portfolio_base = build_portfolio(data['portfolio']['base'])
    portfolio_hedged = build_portfolio(data['portfolio']['hedged'])

    # Config
    config = data.get('config', {'lambda_penalty': 1e9})

    return portfolio_base, portfolio_hedged, stats, config


def build_portfolio(port_data: dict) -> Portfolio:
    """Build Portfolio from JSON data."""
    instruments = [
        Instrument(
            name=inst['name'],
            mtm_value=inst['mtm_value'],
            eq_delta=inst.get('eq_delta', 0.0),
            eq_gamma=inst.get('eq_gamma', 0.0),
            eq_vega=inst.get('eq_vega', 0.0),
            fx_delta=inst.get('fx_delta', 0.0),
            ir_dv01=inst.get('ir_dv01', 0.0),
        )
        for inst in port_data['instruments']
    ]
    return Portfolio(name=port_data['name'], instruments=instruments)


def generate_factor_shock(params: ScenarioParameters, stats: HistoricalStats) -> FactorShock:
    """
    Generate correlated factor shocks using Cholesky decomposition.

    Maps AI-proposed sigmas → actual market moves, applying:
    1. Correlation interpolation based on crisis_intensity
    2. Time scaling by sqrt(horizon_days)
    """
    # Interpolate correlation matrix based on crisis intensity
    corr = ((1 - params.crisis_intensity) * stats.corr_normal +
            params.crisis_intensity * stats.corr_crisis)

    # Build covariance matrix
    vols = np.array([stats.eq_vol, stats.vol_of_vol, stats.fx_vol, stats.ir_vol])
    cov = np.diag(vols) @ corr @ np.diag(vols)

    # Cholesky decomposition for correlated shocks
    L = np.linalg.cholesky(cov)

    # AI-proposed sigma vector
    sigma_vec = np.array([params.eq_sigmas, params.vol_sigmas,
                          params.fx_sigmas, params.ir_sigmas])

    # Apply correlation and time scaling
    sqrtT = math.sqrt(max(1, params.horizon_days))
    correlated_shocks = L @ sigma_vec * sqrtT

    return FactorShock(
        eq_shock=float(correlated_shocks[0]),
        vol_shock=float(correlated_shocks[1]),
        fx_shock=float(correlated_shocks[2]),
        ir_shock=float(correlated_shocks[3]),
    )


def calculate_portfolio_pnl(portfolio: Portfolio, shock: FactorShock) -> float:
    """Calculate total portfolio P&L under given shock."""
    return sum(instrument_pnl(inst, shock) for inst in portfolio.instruments)


def instrument_pnl(inst: Instrument, shock: FactorShock) -> float:
    """
    Calculate instrument P&L using Taylor expansion.

    Equity/Vol/FX sensitivities are ratios scaled by mtm_value.
    IR sensitivity (DV01) is absolute JPY, not scaled.

    dV ≈ base_value*(eq_delta*eq + 0.5*eq_gamma*eq^2 + vega*vol + fx_delta*fx) + ir_dv01*ir
    """
    eq = shock.eq_shock
    dV_eq = inst.mtm_value * (inst.eq_delta * eq + 0.5 * inst.eq_gamma * eq * eq)
    dV_vol = inst.mtm_value * inst.eq_vega * shock.vol_shock
    dV_fx = inst.mtm_value * inst.fx_delta * shock.fx_shock
    dV_ir = inst.ir_dv01 * shock.ir_shock
    return dV_eq + dV_vol + dV_fx + dV_ir


def sigma_penalty(params: ScenarioParameters, per_factor_cap=8.0, joint_cap=10.0) -> float:
    """
    Calculate plausibility penalty for extreme scenarios.

    Penalizes:
    1. Individual factors beyond ±8 sigma (per_factor_cap)
    2. Joint extremeness beyond 10 sigma norm (joint_cap)
    """
    sigs = np.array([params.eq_sigmas, params.vol_sigmas,
                     params.fx_sigmas, params.ir_sigmas])

    # Per-factor penalty if |sigma| exceeds cap
    per_factor_excess = np.maximum(np.abs(sigs) - per_factor_cap, 0.0)
    per_factor_pen = float(np.sum(per_factor_excess ** 2))

    # Joint extremeness penalty (L2 norm beyond joint_cap)
    dist = float(np.linalg.norm(sigs))
    joint_excess = max(0.0, dist - joint_cap)
    joint_pen = joint_excess ** 2

    return per_factor_pen + joint_pen
