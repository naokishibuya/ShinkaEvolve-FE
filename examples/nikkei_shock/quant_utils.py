import math
import re
import numpy as np
from scipy.optimize import minimize
from quant_types import (
    Scenario,
    Instrument,
    RiskStats,
    ShockParams,
    PnL,
    PnLSummary,
    FactorMoves,
)


def optimize_worst_case_shock(
    scenario: Scenario,
    stats: RiskStats,
) -> tuple[ShockParams, FactorMoves, PnLSummary]:

    # Precompute inverse correlation matrix
    corr_inv = np.linalg.inv(stats.corr_crisis)

    def calculate_joint_sigma(x: np.ndarray) -> float:
        # Calculate joint sigma radius based on Mahalanobis distance
        try:
            r2 = float(x.T @ corr_inv @ x)
            joint_sigma = math.sqrt(max(r2, 0.0))
        except np.linalg.LinAlgError:
            # In case of singular matrix (no inversion possible)
            joint_sigma = float(np.linalg.norm(x))
        return joint_sigma

    def calculate_shock_results(x: np.ndarray) -> tuple[ShockParams, FactorMoves, PnLSummary]:
        shock = ShockParams(*x)
        factor_moves = calculate_factor_moves(shock=shock, stats=stats)
        pnl_summary = calculate_portfolio_pnl(scenario.exposure, scenario.hedge, factor_moves)
        return shock, factor_moves, pnl_summary

    def objective(x: np.ndarray) -> float:
        # x = [eq_sigma, vol_sigma, fx_sigma, ir_sigma]
        _, _, pnl_summary = calculate_shock_results(x)
        # We want to maximise loss (negative P&L), so we minimise total pnl.
        return pnl_summary.net.total

    def constraint(x):
        return 0 if stats.max_joint_sigma > calculate_joint_sigma(x) else -1

    result = minimize(
        objective,
        x0=np.array([0.0, 0.0, 0.0, 0.0], dtype=float),
        method='COBYLA',
        bounds=[(-stats.max_factor_sigma, stats.max_factor_sigma)] * 4,
        constraints=[{'type': 'eq', 'fun': constraint}],
        options={
            'maxiter': 5000,
            'disp': True,
            'rhobeg': 1.0,        # controls initial search radius
            'tol': 1e-4,          # when to stop improving (looser = faster convergence)
            'catol': 1e-4,        # how strictly to enforce constraints
        },
    )
    if not result.success:
        print(f"Optimization failed: {result.message}")

    shock, factor_moves, pnl_summary = calculate_shock_results(result.x)
    print(result)
    shock.joint_sigma = calculate_joint_sigma(result.x)
    return shock, factor_moves, pnl_summary



def calculate_factor_moves(
    shock: ShockParams,
    stats: RiskStats,
) -> FactorMoves:
    # Calculate factor moves based on shock parameters
    sigma_vec_arr = np.array(
        [
            shock.eq_shock_sigma,
            shock.vol_shock_sigma,
            shock.fx_shock_sigma,
            shock.ir_shock_sigma,
        ],
        dtype=float,
    )

    sqrt_t = math.sqrt(stats.horizon_days)

    vols = np.array(
        [
            stats.eq_vol,
            stats.vol_of_vol,
            stats.fx_vol,
            stats.ir_vol,
        ],
        dtype=float,
    )

    # This gives the absolute moves as per shock sigmas for the horizon
    moves = vols * sigma_vec_arr * sqrt_t

    return FactorMoves(
        eq_move=float(moves[0]),
        vol_move=float(moves[1]),
        fx_move=float(moves[2]),
        ir_move=float(moves[3]),
    )


def instrument_pnl(
    instrument: Instrument,
    factor_moves: FactorMoves,
) -> PnL:
    # Calculate PnL contribution of a single instrument given factor moves
    mtm = instrument.mtm_value

    eq = factor_moves.eq_move
    vol = factor_moves.vol_move
    fx = factor_moves.fx_move
    ir = factor_moves.ir_move

    dV_eq = mtm * (instrument.eq_linear * eq + 0.5 * instrument.eq_quad * eq * eq)
    dV_vol = mtm * instrument.vol_linear * vol
    dV_fx = mtm * instrument.fx_linear * fx
    dV_ir = instrument.ir_dv01 * ir * 10_000.0

    return PnL(
        total=dV_eq + dV_vol + dV_fx + dV_ir,
        equity=dV_eq,
        vol=dV_vol,
        fx=dV_fx,
        rates=dV_ir,
    )


def total_net_pnl(
    instruments: list[Instrument],
    factor_moves: FactorMoves,
) -> tuple[PnL, dict[str, PnL]]:
    # Calculate total PnL for a list of instruments
    pnls: dict[str, PnL] = {}
    for inst in instruments:
        pnls[inst.name] = instrument_pnl(inst, factor_moves)

    totals = PnL(
        total=sum(d.total for d in pnls.values()),
        equity=sum(d.equity for d in pnls.values()),
        vol=sum(d.vol for d in pnls.values()),
        fx=sum(d.fx for d in pnls.values()),
        rates=sum(d.rates for d in pnls.values()),
    )
    return totals, pnls


def calculate_portfolio_pnl(
    exposure: list[Instrument],
    hedge: list[Instrument],
    factor_moves: FactorMoves,
) -> PnLSummary:
    total_exposure, exposure_details = total_net_pnl(exposure, factor_moves)
    total_hedge, hedge_details = total_net_pnl(hedge, factor_moves)

    total_net = PnL(
        total=total_exposure.total + total_hedge.total,
        equity=total_exposure.equity + total_hedge.equity,
        vol=total_exposure.vol + total_hedge.vol,
        fx=total_exposure.fx + total_hedge.fx,
        rates=total_exposure.rates + total_hedge.rates,
    )

    # If loss_ratio <= 0 : hedges help too much.
    exposure_amount = sum(abs(inst.mtm_value) for inst in exposure)
    if exposure_amount != 0.0:
        loss_ratio = -total_net.total / exposure_amount
    else:
        loss_ratio = 0.0

    return PnLSummary(
        net=total_net,
        exposure=total_exposure,
        hedge=total_hedge,
        exposure_pnls=exposure_details,
        hedge_pnls=hedge_details,
        loss=max(0.0, -total_net.total),
        notional=exposure_amount,
        loss_ratio=loss_ratio,
    )
