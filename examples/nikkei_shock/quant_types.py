import numpy as np
from dataclasses import dataclass


Number = float | int


@dataclass
class Instrument:
    # Single exposure or hedge instrument with sensitivities.
    name: str           # Instrument name
    mtm_value: float    # mark-to-market value in JPY
    eq_linear: float    # equity delta-like sensitivity per 1σ equity move (scaled by mtm)
    eq_quad: float      # equity convexity (gamma-like) per (1σ move)^2 (scaled by mtm)
    vol_linear: float   # volatility sensitivity (vega-like) per 1σ vol move (scaled by mtm)
    fx_linear: float    # FX sensitivity per 1σ FX move (scaled by mtm)
    ir_dv01: float      # DV01: JPY P&L per +1bp parallel rate move


@dataclass
class Greeks:
    # Greeks for a portfolio block.
    delta: float        # equity delta (JPY / 1σ equity)
    gamma: float        # equity gamma (JPY / σ² equity)
    vega: float         # vol sensitivity (JPY / 1σ vol)
    fx: float           # FX sensitivity (JPY / 1σ FX)
    dv01: float         # rate DV01 (JPY per +1bp move


@dataclass
class Scenario:
    # Portfolio scenario: description + exposure and hedge legs + Greeks.
    name: str
    description: str
    exposure: list[Instrument]
    hedge: list[Instrument]
    greeks: Greeks


@dataclass
class RiskStats:
    # Daily 1σ vols and correlation matrices (eq, vol, fx, ir order).
    eq_vol: float            # Daily equity volatility (1σ) as a decimal, e.g. 0.012 = 1.2%
    vol_of_vol: float        # Daily volatility-of-volatility (1σ) as a decimal
    fx_vol: float            # Daily FX volatility (1σ) as a decimal
    ir_vol: float            # Daily interest rate volatility (1σ) as a decimal (on yield in decimal units)
    corr_crisis: np.ndarray  # shape (4, 4); Crisis-regime correlation matrix: order [equity, vol, fx, ir]
    horizon_days: int        # crisis horizon in days for √T scaling
    max_factor_sigma: float  # maximum allowed per-factor shock in σ units
    max_joint_sigma: float   # maximum allowed joint shock in σ units (Mahalanobis distance)


@dataclass
class ShockParams:
    # Final per-factor shocks in sigma units (1-day volatility) before time scaling
    # and macro knobs. 
    eq_shock_sigma: float    # equity shock in σ units (signed), e.g. -10.0 for -10σ equity
    vol_shock_sigma: float   # volatility shock in σ units (signed), e.g. +10.0 for +10σ vol
    fx_shock_sigma: float    # FX shock in σ units (signed), e.g. +8.0  for +8σ FX
    ir_shock_sigma: float    # rate shock in σ units (signed), e.g. +5.0 for +5σ move on decimal yields
    # Mahalanobis distance and related info
    joint_sigma: float = 0.0  # joint sigma of the shock (Mahalanobis distance)


@dataclass
class FactorMoves:
    """Factor moves in absolute units after applying vols and horizon scaling."""
    # Final per-factor shocks in sigma units (1-day vols)
    eq_move: float
    vol_move: float
    fx_move: float
    ir_move: float


@dataclass
class PnL:
    total: float
    equity: float
    vol: float
    fx: float
    rates: float


@dataclass
class PnLSummary:
    net: PnL
    exposure: PnL
    hedge: PnL
    exposure_pnls: dict[str, PnL]
    hedge_pnls: dict[str, PnL]
    # Loss metrics
    loss: float        # e.g. max(0, -net.total)
    notional: float
    loss_ratio: float  # loss / reference_notional
