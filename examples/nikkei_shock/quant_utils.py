import math
import numpy as np
from dataclasses import dataclass
from scenario import Instrument, RiskStats, ScenarioConfig, ShockParams


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
    norm_loss: float
    norm_sigma: float


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
    config: ScenarioConfig,
) -> ScenarioMetrics:

    # If loss_ratio <= 0 : hedges help too much.
    exposure_amount = sum(abs(inst.mtm_value) for inst in exposure)
    if exposure_amount != 0.0:
        loss_ratio = -net_pnl.total / exposure_amount
    else:
        loss_ratio = 0.0

    joint_sigma = factor_moves.joint_sigma

    def normalize(value: float, target: float = 1.0) -> float:
        raw = value / target # Raw normalization using target
        return raw / (1.0 + abs(raw))  # Rational squash each (maps ℝ to (-1,1))

    norm_loss  = normalize(loss_ratio, config.target_loss_ratio)    # 0.5 at target loss
    norm_sigma = normalize(joint_sigma, config.target_joint_sigma)  # 0.5 at target severity

    score = normalize(norm_loss - norm_sigma)  # (-1, 1), 0.0 at balanced targets

    hint = _quant_hint(score, norm_loss, norm_sigma)

    return ScenarioMetrics(
        quantitative_score=score,
        hint=hint,
        total_pnl=net_pnl.total,
        exposure_amount=exposure_amount,
        loss_ratio=loss_ratio,
        joint_sigma=joint_sigma,
        norm_loss=norm_loss,
        norm_sigma=norm_sigma,
    )


def _quant_hint(score: float, norm_loss: float, norm_sigma: float) -> str:
    """
    norm_loss:  (-1,1), 0.5 at target loss
    norm_sigma: (-1,1), 0.5 at target severity
    score:      (-1,1), loss-minus-severity balance
    """

    # Loss message
    if norm_loss <= 0:
        loss_msg = "Loss is absent; adjust shock directions so they hit the main net exposures."
    elif norm_loss < 0.5:
        loss_msg = "Loss is below the desired scale; point factor shocks more directly at strongest delta/gamma/vega/FX/DV01."
    else:
        loss_msg = "Loss is on or above the desired scale."

    # Severity message
    if norm_sigma < 0.3:
        sigma_msg = "Shock magnitudes are mild; increase sigmas while keeping directions crisis-consistent."
    elif norm_sigma < 0.7:
        sigma_msg = "Shock magnitudes are crisis-like."
    else:
        sigma_msg = "Shock magnitudes are large; reduce sigmas while preserving loss."

    # Balance (loss vs severity) message
    if score < -0.3:
        bal_msg = "Shocks are oversized relative to the loss; refine directions or scale down sigmas."
    elif score < 0.3:
        bal_msg = "Loss and shock size are roughly aligned; small directional adjustments may improve impact."
    else:
        bal_msg = "Loss and shock size are well-balanced."

    return f"{loss_msg} {sigma_msg} {bal_msg}"

