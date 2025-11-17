"""
Helper utilities for hedge weakness analysis.

These functions are pre-implemented and available for the evolving AI to orchestrate.
They handle common calculations so the AI can focus on high-level strategy and reasoning.
"""

import math
import numpy as np
from typing import Any


def compute_net_greeks(
    exposure: list[dict[str, Any]],
    hedge: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute MTM-weighted net greeks (delta, gamma, vega, FX, DV01)."""

    def scaled(insts: list[dict[str, Any]], key: str, *, is_dv01: bool = False) -> float:
        total = 0.0
        for inst in insts:
            sens = inst.get(key, 0.0)  # sensitivity per 1σ or per 1bp
            if is_dv01:
                total += sens  # DV01 is already absolute JPY per bp, no mtm scaling
            else:
                total += inst.get("mtm_value", 0.0) * sens
        return total

    exp_delta = scaled(exposure, "eq_linear")
    exp_gamma = scaled(exposure, "eq_quad")
    exp_vega  = scaled(exposure, "vol_linear")
    exp_fx    = scaled(exposure, "fx_linear")
    exp_dv01  = scaled(exposure, "ir_dv01", is_dv01=True)

    hdg_delta = scaled(hedge, "eq_linear")
    hdg_gamma = scaled(hedge, "eq_quad")
    hdg_vega  = scaled(hedge, "vol_linear")
    hdg_fx    = scaled(hedge, "fx_linear")
    hdg_dv01  = scaled(hedge, "ir_dv01", is_dv01=True)

    return {
        "net_delta": exp_delta + hdg_delta,      # JPY / 1σ
        "net_gamma": exp_gamma + hdg_gamma,      # JPY / σ²
        "net_vega":  exp_vega  + hdg_vega,       # JPY / 1σ (vol)
        "net_fx":    exp_fx    + hdg_fx,         # JPY / 1σ (FX)
        "net_dv01":  exp_dv01  + hdg_dv01,       # JPY / bp

        "exposure_delta": exp_delta,
        "exposure_gamma": exp_gamma,
        "exposure_vega":  exp_vega,
        "exposure_fx":    exp_fx,
        "exposure_dv01":  exp_dv01,

        "hedge_delta": hdg_delta,
        "hedge_gamma": hdg_gamma,
        "hedge_vega":  hdg_vega,
        "hedge_fx":    hdg_fx,
        "hedge_dv01":  hdg_dv01,
    }


def calculate_factor_moves(shock_params: dict, stats: dict) -> dict:
    """
    Generate correlated factor shocks using Cholesky decomposition.

    Maps AI-proposed sigmas → actual market moves, applying:
    1. Correlation interpolation based on crisis_intensity
    2. Time scaling by sqrt(horizon_days)
    """
    # Interpolate correlation matrix based on crisis intensity
    crisis_intensity = float(shock_params["crisis_intensity"])
    corr = (
        (1.0 - crisis_intensity) * stats["corr_normal"]
        + crisis_intensity * stats["corr_crisis"]
    )

    # Build covariance matrix
    vols = np.array([
        stats["eq_vol"],
        stats["vol_of_vol"],
        stats["fx_vol"],
        stats["ir_vol"],
    ])
    cov = np.diag(vols) @ corr @ np.diag(vols)

    # Cholesky decomposition for correlated shocks
    L = np.linalg.cholesky(cov)

    # AI-proposed sigma vector
    sigma_vec = np.array([
        shock_params["eq_shock_sigma"],
        shock_params["vol_shock_sigma"],
        shock_params["fx_shock_sigma"],
        shock_params["ir_shock_sigma"],
    ], dtype=float)

    # Apply correlation and time scaling
    horizon_days = max(1, int(shock_params["horizon_days"]))
    sqrtT = math.sqrt(horizon_days)

    correlated_moves = L @ sigma_vec * sqrtT

    return {
        "eq_move":  float(correlated_moves[0]),
        "vol_move": float(correlated_moves[1]),
        "fx_move":  float(correlated_moves[2]),
        "ir_move":  float(correlated_moves[3]),
    }


def calculate_portfolio_pnl(
    exposure: list[dict],
    hedge: list[dict],
    factor_moves: dict[str, float],
) -> dict[str, Any]:
    """Calculate total portfolio P&L and breakdown by risk factor."""
    exposure_totals, exposure_details = total_pnl(exposure, factor_moves)
    hedge_totals, hedge_details = total_pnl(hedge, factor_moves)
    net_totals = {
        k: exposure_totals[k] + hedge_totals[k]
        for k in ["total", "equity", "vol", "fx", "rates"]
    }

    return {
        "net_totals": net_totals,
        "exposure_totals": exposure_totals,
        "hedge_totals": hedge_totals,
        "exposure_details": exposure_details,
        "hedge_details": hedge_details,
    }


def total_pnl(instruments: list[dict], factor_moves: dict) -> dict[str, float]:
    details = []
    for instrument in instruments:
        comp = instrument_pnl(instrument, factor_moves)
        details.append(comp)
    totals = {
        "total":  sum(d["total"]  for d in details),
        "equity": sum(d["equity"] for d in details),
        "vol":    sum(d["vol"]    for d in details),
        "fx":     sum(d["fx"]     for d in details),
        "rates":  sum(d["rates"]  for d in details),
    }
    return totals, details


def instrument_pnl(instrument: dict, factor_moves: dict) -> dict[str, Any]:
    """
    Calculate instrument P&L using Taylor expansion.

    Equity/Vol/FX sensitivities are ratios scaled by mtm_value.
    IR sensitivity (ir_dv01) is absolute JPY per 1bp rate move (DV01), not scaled.

    dV ≈ base_value*(eq_linear*eq + 0.5*eq_quad*eq^2 + vol_linear*vol + fx_linear*fx)
         + ir_dv01 * (ir_move_in_decimal * 10_000)
    """
    mtm = instrument['mtm_value']

    eq  = factor_moves['eq_move']
    vol = factor_moves['vol_move']
    fx  = factor_moves['fx_move']
    ir  = factor_moves['ir_move']  # decimal yield move, e.g. 0.01 = 1% = 100bp

    eq_linear  = instrument['eq_linear']
    eq_quad    = instrument['eq_quad']
    vol_linear = instrument['vol_linear']
    fx_linear  = instrument['fx_linear']
    ir_dv01    = instrument['ir_dv01']

    dV_eq  = mtm * (eq_linear * eq + 0.5 * eq_quad * eq * eq)
    dV_vol = mtm * vol_linear * vol
    dV_fx  = mtm * fx_linear * fx
    dV_ir  = ir_dv01 * ir * 10_000  # convert decimal move to bp

    return {
        "name": instrument['name'],
        "total": dV_eq + dV_vol + dV_fx + dV_ir,
        "equity": dV_eq,
        "vol": dV_vol,
        "fx": dV_fx,
        "rates": dV_ir,
    }

