"""
Initial scenario generator for ShinkaEvolve. The propose_scenario function will be evolved by the LLM.
"""
import copy
import math
import numpy as np


# Helper functions available to the evolvable code
def calculate_factor_shock(params: dict, stats: dict) -> dict:
    """
    Generate correlated factor shocks using Cholesky decomposition.

    Maps AI-proposed sigmas → actual market moves, applying:
    1. Correlation interpolation based on crisis_intensity
    2. Time scaling by sqrt(horizon_days)
    """
    # Interpolate correlation matrix based on crisis intensity
    corr = ((1 - params['crisis_intensity']) * stats['corr_normal'] +
            params['crisis_intensity'] * stats['corr_crisis'])

    # Build covariance matrix
    vols = np.array([stats['eq_vol'], stats['vol_of_vol'], stats['fx_vol'], stats['ir_vol']])
    cov = np.diag(vols) @ corr @ np.diag(vols)

    # Cholesky decomposition for correlated shocks
    L = np.linalg.cholesky(cov)

    # AI-proposed sigma vector
    sigma_ratios = np.array([
        params['eq_sigmas'],
        params['vol_sigmas'],
        params['fx_sigmas'],
        params['ir_sigmas']
    ])

    # Apply correlation and time scaling
    sqrtT = math.sqrt(max(1, params['horizon_days']))
    correlated_shocks = L @ sigma_ratios * sqrtT

    return {
        'eq_shock': float(correlated_shocks[0]),
        'vol_shock': float(correlated_shocks[1]),
        'fx_shock': float(correlated_shocks[2]),
        'ir_shock': float(correlated_shocks[3]),
    }


def instrument_pnl(inst: dict, shock: dict) -> float:
    """
    Calculate instrument P&L using Taylor expansion.

    Equity/Vol/FX sensitivities are ratios scaled by mtm_value.
    IR sensitivity (DV01) is absolute JPY, not scaled.

    dV ≈ base_value*(eq_linear*eq + 0.5*eq_quad*eq^2 + vega*vol + fx_linear*fx) + ir_dv01*ir
    """
    mtm = inst['mtm_value']

    eq  = shock['eq_shock']
    vol = shock['vol_shock']
    fx  = shock['fx_shock']
    ir  = shock['ir_shock']

    eq_linear  = inst['eq_linear']
    eq_quad    = inst['eq_quad']
    vol_linear = inst['vol_linear']
    fx_linear  = inst['fx_linear']
    ir_dv01    = inst['ir_dv01']

    dV_eq  = mtm * (eq_linear * eq + 0.5 * eq_quad * eq * eq)
    dV_vol = mtm * vol_linear  * vol
    dV_fx  = mtm * fx_linear * fx
    dV_ir  = ir_dv01 * ir
    return dV_eq + dV_vol + dV_fx + dV_ir


def sigma_penalty(params: dict, max_sigma_ratio: float) -> float:
    """Calculate plausibility penalty for extreme scenarios."""
    sigma_ratios = np.array([
        params['eq_sigmas'],
        params['vol_sigmas'],
        params['fx_sigmas'],
        params['ir_sigmas']
    ])
    # elementwise excess above max_sigma_ratio
    excess = np.maximum(np.abs(sigma_ratios) - max_sigma_ratio, 0.0)
    return float(np.sum(excess ** 2))


def horizon_penalty(params: dict, max_horizon_days: int) -> float:
    """Calculate penalty for long horizon_days to avoid sqrt(T) blowup."""
    extra = max(0.0, params["horizon_days"] - max_horizon_days)
    horizon_penalty = extra * extra
    return float(horizon_penalty)


# EVOLVE-BLOCK-START
def propose_scenario(
    exposure: list[dict],
    hedge: list[dict],
    stats: dict,
    total_mtm: float,
    max_sigma_ratio: float,
    max_horizon_days: int,
    lambda_penalty: float,
) -> dict:
    """
    Propose a stress scenario in sigma space.

    Heuristic baseline:
    - Compute net factor exposures (equity, vol, FX, rates).
    - Push each factor in the direction that hurts the hedge the most.
    - Keep magnitudes within a reasonable sigma band.
    """
    # Aggregate net exposures of the *hedged* portfolio
    def net_factor_exposure(instruments: list[dict]):
        eq_lin  = sum(inst.get("mtm_value", 0.0) * inst.get("eq_linear", 0.0) for inst in instruments)
        vol_lin = sum(inst.get("mtm_value", 0.0) * inst.get("vol_linear", 0.0) for inst in instruments)
        fx_lin  = sum(inst.get("mtm_value", 0.0) * inst.get("fx_linear", 0.0) for inst in instruments)
        ir_dv01 = sum(inst.get("ir_dv01", 0.0) for inst in instruments)
        return eq_lin, vol_lin, fx_lin, ir_dv01

    # Portfolio with hedge applied
    full_portfolio = exposure + hedge
    eq_net, vol_net, fx_net, ir_net = net_factor_exposure(full_portfolio)

    # Choose directions that worsen net exposure
    # (if we are net long eq, push eq down; if net short eq, push eq up, etc.)
    def direction(x: float) -> float:
        return -1.0 if x > 0 else (1.0 if x < 0 else 0.0)

    eq_dir  = direction(eq_net)
    vol_dir = direction(vol_net)
    fx_dir  = direction(fx_net)
    ir_dir  = direction(ir_net)

    # Magnitudes: start with moderate 3–5σ moves
    eq_sigmas  = eq_dir  * 4.0
    vol_sigmas = vol_dir * 3.0
    fx_sigmas  = fx_dir  * 3.0
    ir_sigmas  = ir_dir  * 2.0

    # If some net exposure is basically zero, still allow a generic equity crash
    if eq_dir == 0.0:
        eq_sigmas = -3.0

    # Keep sigmas within max_sigma_ratio
    def clamp(x: float, bound: float) -> float:
        if x > bound:
            return bound
        if x < -bound:
            return -bound
        return x

    eq_sigmas  = clamp(eq_sigmas,  max_sigma_ratio)
    vol_sigmas = clamp(vol_sigmas, max_sigma_ratio)
    fx_sigmas  = clamp(fx_sigmas,  max_sigma_ratio)
    ir_sigmas  = clamp(ir_sigmas,  max_sigma_ratio)

    # Use a short horizon to avoid artificially massive √T scaling
    horizon_days = 5

    # Start from moderately crisis-like regime
    crisis_intensity = 1.0  # raw value; will be squashed by sigmoid in run_experiment

    return {
        "eq_sigmas": eq_sigmas,
        "vol_sigmas": vol_sigmas,
        "fx_sigmas": fx_sigmas,
        "ir_sigmas": ir_sigmas,
        "crisis_intensity": crisis_intensity,
        "horizon_days": horizon_days,
    }
# EVOLVE-BLOCK-END


def run_experiment(
    scenario_name: str,
    description: str,
    exposure: list[dict],
    hedge: list[dict],
    stats: dict,
    max_sigma_ratio: float,
    max_horizon_days: int,
    lambda_penalty: float,
) -> dict:
    """Entry point for ShinkaEvolve evaluation."""
    # Call the evolving function
    total_mtm = sum(abs(inst['mtm_value']) for inst in exposure)
    params = propose_scenario(
        copy.deepcopy(exposure),
        copy.deepcopy(hedge),
        copy.deepcopy(stats),
        total_mtm,
        max_sigma_ratio,
        max_horizon_days,
        lambda_penalty,
    )

    # Normalize crisis_intensity to [0,1]
    if 'crisis_intensity' in params:
        crisis_intensity = 1.0 / (1.0 + math.exp(-params['crisis_intensity']))  # Sigmoid to [0,1]
    else:
        crisis_intensity = 0.0  # Default value (no crisis)
    params['crisis_intensity'] = crisis_intensity

    # Generate correlated factor shocks
    shock = calculate_factor_shock(params, stats)

    # Calculate P&L for both portfolios with per-instrument breakdown
    exposure_pnls = {inst['name']: instrument_pnl(inst, shock) for inst in exposure}
    hedge_pnls = {inst['name']: instrument_pnl(inst, shock) for inst in hedge}

    exposure_pnl = sum(pnl for pnl in exposure_pnls.values())
    hedge_pnl = sum(pnl for pnl in hedge_pnls.values())

    # Calculate fitness (normalized by base portfolio size for interpretability)
    plausibility_penalty = sigma_penalty(params, max_sigma_ratio) + horizon_penalty(params, max_horizon_days)
    exposure_value = max(abs(total_mtm), 1.0) # Avoid division by zero
    total_pnl = exposure_pnl + hedge_pnl
    raw_rel_loss = - total_pnl / exposure_value       # relative loss of hedged portfolio
    penalty_factor = math.exp(-lambda_penalty * plausibility_penalty)
    fitness = raw_rel_loss * penalty_factor

    # Return comprehensive metrics
    return {
        # Overall metrics
        'fitness': float(fitness),
        'exposure_pnl': float(exposure_pnl),
        'hedge_pnl': float(hedge_pnl),
        'plausibility_penalty': float(plausibility_penalty),
        # Scenario metadata
        'scenario_name': scenario_name,
        'scenario_description': description,
        # Scenario parameters
        'eq_sigmas': float(params['eq_sigmas']),
        'vol_sigmas': float(params['vol_sigmas']),
        'fx_sigmas': float(params['fx_sigmas']),
        'ir_sigmas': float(params['ir_sigmas']),
        'crisis_intensity': float(params['crisis_intensity']),
        'horizon_days': int(params['horizon_days']),
        # Factor shocks
        'eq_shock': float(shock['eq_shock']),
        'vol_shock': float(shock['vol_shock']),
        'fx_shock': float(shock['fx_shock']),
        'ir_shock': float(shock['ir_shock']),
        # Per-instrument breakdown
        'exposure_instruments': exposure_pnls,
        'hedge_instruments': hedge_pnls,
    }
