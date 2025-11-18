import math
import numpy as np
from dataclasses import dataclass
from scenario import Instrument, Scenario, RiskStats, ShockParams


@dataclass
class FactorMoves:
    """ factor moves in absolute units and related info """
    eq_move: float
    vol_move: float
    fx_move: float
    ir_move: float
    # Mahalanobis distance and related info
    joint_sigma: float 


@dataclass
class InstrumentPnl:
    name: str
    total: float
    equity: float
    vol: float
    fx: float
    rates: float


@dataclass
class PnLTotals:
    total: float
    equity: float
    vol: float
    fx: float
    rates: float


@dataclass
class PnLBreakdown:
    net: PnLTotals
    exposure: PnLTotals
    hedge: PnLTotals
    exposure_details: list[InstrumentPnl]
    hedge_details: list[InstrumentPnl]


@dataclass
class ScenarioMetrics:
    quantitative_score: float
    total_pnl: float
    exposure_amount: float
    loss_ratio: float
    joint_sigma: float
    factor_moves: FactorMoves
    pnl_breakdown: PnLBreakdown


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

    # Compute joint sigma radius based on Mahalanobis distance
    try:
        corr_inv = np.linalg.inv(stats.corr_crisis)
        r2 = float(sigma_vec_arr.T @ corr_inv @ sigma_vec_arr)
        joint_sigma = math.sqrt(max(r2, 0.0))
    except np.linalg.LinAlgError:
        # In case of singular matrix (no inversion possible)
        joint_sigma = float(np.linalg.norm(sigma_vec_arr))

    return FactorMoves(
        eq_move=float(moves[0]),
        vol_move=float(moves[1]),
        fx_move=float(moves[2]),
        ir_move=float(moves[3]),
        joint_sigma=joint_sigma,
    )


def instrument_pnl(
    instrument: Instrument,
    factor_moves: FactorMoves,
) -> InstrumentPnl:
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

    return InstrumentPnl(
        name=instrument.name,
        total=dV_eq + dV_vol + dV_fx + dV_ir,
        equity=dV_eq,
        vol=dV_vol,
        fx=dV_fx,
        rates=dV_ir,
    )


def total_pnl(
    instruments: list[Instrument],
    factor_moves: FactorMoves,
) -> tuple[PnLTotals, list[InstrumentPnl]]:
    # Calculate total PnL for a list of instruments
    details: list[InstrumentPnl] = []
    for inst in instruments:
        comp = instrument_pnl(inst, factor_moves)
        details.append(comp)

    totals = PnLTotals(
        total=sum(d.total for d in details),
        equity=sum(d.equity for d in details),
        vol=sum(d.vol for d in details),
        fx=sum(d.fx for d in details),
        rates=sum(d.rates for d in details),
    )
    return totals, details


def calculate_portfolio_pnl(
    exposure: list[Instrument],
    hedge: list[Instrument],
    factor_moves: FactorMoves,
) -> PnLBreakdown:
    exposure_totals, exposure_details = total_pnl(exposure, factor_moves)
    hedge_totals, hedge_details = total_pnl(hedge, factor_moves)

    net_totals = PnLTotals(
        total=exposure_totals.total + hedge_totals.total,
        equity=exposure_totals.equity + hedge_totals.equity,
        vol=exposure_totals.vol + hedge_totals.vol,
        fx=exposure_totals.fx + hedge_totals.fx,
        rates=exposure_totals.rates + hedge_totals.rates,
    )

    return PnLBreakdown(
        net=net_totals,
        exposure=exposure_totals,
        hedge=hedge_totals,
        exposure_details=exposure_details,
        hedge_details=hedge_details,
    )


def evaluate_scenario_metrics(
    scenario: Scenario,
    shock: ShockParams,
    stats: RiskStats,
) -> ScenarioMetrics:
    factor_moves = calculate_factor_moves(shock, stats)
    pnl = calculate_portfolio_pnl(scenario.exposure, scenario.hedge, factor_moves)
    total_pnl = pnl.net.total

    exposure_amount = sum(abs(inst.mtm_value) for inst in scenario.exposure)

    if exposure_amount != 0.0:
        loss_ratio = -total_pnl / exposure_amount
    else:
        loss_ratio = 0.0

    joint_sigma = factor_moves.joint_sigma

    # prohibit too-small joint sigma to avoid gaming the score
    # note: joint_sigma is always a magnitude >= 0.0
    effective_sigma = max(joint_sigma, 1.0) # at least 1σ
    raw_q = loss_ratio / effective_sigma
    quantitative_score = raw_q / (1.0 + abs(raw_q)) # rational squashing to (-1, 1)

    return ScenarioMetrics(
        quantitative_score=quantitative_score,
        total_pnl=total_pnl,
        exposure_amount=exposure_amount,
        loss_ratio=loss_ratio,
        joint_sigma=joint_sigma,
        factor_moves=factor_moves,
        pnl_breakdown=pnl,
    )
