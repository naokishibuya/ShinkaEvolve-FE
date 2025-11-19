import math
import numpy as np
from dataclasses import dataclass
from scenario import Instrument, RiskStats, SearchConds, ShockParams


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
    hint: str
    total_pnl: float
    exposure_amount: float
    loss_ratio: float
    joint_sigma: float


def calculate_factor_moves(
    shock: ShockParams,
    stats: RiskStats,
    conds: SearchConds,
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

    sqrt_t = math.sqrt(conds.horizon_days)

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


def total_net_pnl(
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
    exposure_totals, exposure_details = total_net_pnl(exposure, factor_moves)
    hedge_totals, hedge_details = total_net_pnl(hedge, factor_moves)

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
    exposure: list[Instrument],
    factor_moves: FactorMoves,
    net_pnl: PnLTotals,
    conds: SearchConds,
) -> ScenarioMetrics:

    # If loss_ratio <= 0 : hedges help too much.
    exposure_amount = sum(abs(inst.mtm_value) for inst in exposure)
    if exposure_amount != 0.0:
        loss_ratio = -net_pnl.total / exposure_amount
    else:
        loss_ratio = 0.0

    joint_sigma = factor_moves.joint_sigma

    # scoring
    if loss_ratio <= 0.0:
        score = 0.0
        hint = (
            f"No loss incurred: loss_ratio={loss_ratio:.2f} (≤ 0.0). "
            "Increase the adversarial impact of your shocks on net exposures. "
            "Consider increasing shock magnitudes or directions to amplify losses."
        )
    elif loss_ratio < conds.loss_ratio:
        # Give partial credit since we are only talking about loss_ratio here
        score = 0.5 * loss_ratio / conds.loss_ratio
        hint = (
            f"Loss is too small: loss_ratio={loss_ratio:.2f} (< required {conds.loss_ratio:.2f}). "
            "Increase the adversarial impact of your shocks on net exposures. "
            "Do not worry about keeping severity low until you reach the required loss level."
        )
    elif joint_sigma > conds.joint_sigma:
        # Penalize excessive severity smoothly
        excess = joint_sigma - conds.joint_sigma
        score = 1.0 / (1.0 + math.exp(excess)) + 0.5  # (0.5, 1.0]
        hint = (
            f"Loss meets the condition: loss_ratio={loss_ratio:.2f} (≥ required {conds.loss_ratio:.2f}), "
            f"but severity is high: sigma={joint_sigma:.2f} (> configured {conds.joint_sigma:.2f}). "
            "Try reducing the overall joint sigma while keeping the loss above the required level."
        )
    else:
        score = 1.0
        hint = (
            f"Loss meets the condition: loss_ratio={loss_ratio:.2f} (≥ required {conds.loss_ratio:.2f}), "
            f"and severity is efficient: sigma={joint_sigma:.2f} (≤ allowed {conds.joint_sigma:.2f}). "
            "Further improvements are marginal; focus on refining the qualitative analysis."
        )

    return ScenarioMetrics(
        quantitative_score=score,
        hint=hint,
        total_pnl=net_pnl.total,
        exposure_amount=exposure_amount,
        loss_ratio=loss_ratio,
        joint_sigma=joint_sigma,
    )