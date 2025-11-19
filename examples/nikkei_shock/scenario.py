""" Load scenarios.yaml → normalized dicts + YAML strings """
import yaml
import numpy as np
from dataclasses import dataclass
from pathlib import Path


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
    dv01: float         # rate DV01 (JPY per +1bp move)


@dataclass
class GreeksBreakdown:
    # Greeks for net, exposure-only, and hedge-only.
    net: Greeks         # total portfolio Greeks
    exposure: Greeks    # exposure leg Greeks
    hedge: Greeks       # hedge leg Greeks


@dataclass
class Scenario:
    # Portfolio scenario: description + exposure and hedge legs + Greeks.
    name: str
    description: str
    exposure: list[Instrument]
    hedge: list[Instrument]
    greeks_breakdown: GreeksBreakdown


@dataclass
class RiskStats:
    # Daily 1σ vols and correlation matrices (eq, vol, fx, ir order).
    eq_vol: float            # Daily equity volatility (1σ) as a decimal, e.g. 0.012 = 1.2%
    vol_of_vol: float        # Daily volatility-of-volatility (1σ) as a decimal
    fx_vol: float            # Daily FX volatility (1σ) as a decimal
    ir_vol: float            # Daily interest rate volatility (1σ) as a decimal (on yield in decimal units)
    corr_crisis: np.ndarray  # shape (4, 4); Crisis-regime correlation matrix: order [equity, vol, fx, ir]


@dataclass
class SearchConds:
    horizon_days: int        # crisis horizon in days for √T scaling
    loss_ratio: float        # designated loss ratio vs exposure, e.g. 0.25 for 25%
    joint_sigma: float       # designated overall crisis severity in σ units, e.g. 3.0 for 3σ


@dataclass
class Rationale:
    equity: str | None       # why the equity shock direction/magnitude was chosen
    volatility: str | None   # why the vol shock direction/magnitude was chosen
    fx: str | None           # FX rationale
    rates: str | None        # rates rationale (based on DV01 in JPY per 1bp)


@dataclass
class ShockParams:
    # Final per-factor shocks in sigma units (1-day volatility) before time scaling
    # and macro knobs. 
    eq_shock_sigma: float    # equity shock in σ units (signed), e.g. -10.0 for -10σ equity
    vol_shock_sigma: float   # volatility shock in σ units (signed), e.g. +10.0 for +10σ vol
    fx_shock_sigma: float    # FX shock in σ units (signed), e.g. +8.0  for +8σ FX
    ir_shock_sigma: float    # rate shock in σ units (signed), e.g. +5.0 for +5σ move on decimal yields
    rationale: Rationale     # textual justifications


@dataclass
class ScenarioResponse:
    analysis: str
    shock_params: ShockParams


def load_scenarios(path: str | Path | None = None):
    path = Path(path or Path(__file__).parent / "scenarios.yaml")
    data = yaml.safe_load(path.read_text())

    scenarios = []
    for s in data["scenarios"]:
        exposure = [normalize_instrument(i) for i in s["exposure"]]
        hedge = [normalize_instrument(i) for i in s["hedge"]]
        net_greeks = compute_net_greeks(exposure, hedge)
        scenarios.append(
            Scenario(
                name=s["name"],
                description=s["description"],
                exposure=exposure,
                hedge=hedge,
                greeks_breakdown=net_greeks,
            )
        )

    stats = load_stats(data["stats"])
    conds = load_conds(data["conds"])

    return scenarios, stats, conds


def load_stats(cfg):
    return RiskStats(
        eq_vol=float(cfg["eq_vol"]),
        vol_of_vol=float(cfg["vol_of_vol"]),
        fx_vol=float(cfg["fx_vol"]),
        ir_vol=float(cfg["ir_vol"]),
        corr_crisis=np.array(cfg["corr_crisis"], float),
    )


def load_conds(cfg) -> SearchConds:
    horizon_days = int(cfg["horizon_days"])
    loss_ratio = float(cfg["loss_ratio"])
    joint_sigma = float(cfg["joint_sigma"])
    assert horizon_days > 0, "horizon_days must be positive"
    assert loss_ratio > 0.0, "loss_ratio must be positive"
    assert joint_sigma > 0.0, "joint_sigma must be positive"
    return SearchConds(
        horizon_days=horizon_days,
        loss_ratio=loss_ratio,
        joint_sigma=joint_sigma,
    )


def normalize_instrument(d):
    return Instrument(
        name=d["name"],
        mtm_value=float(d["mtm_value"]),
        eq_linear=float(d.get("eq_linear", 0.0)),
        eq_quad=float(d.get("eq_quad", 0.0)),
        vol_linear=float(d.get("vol_linear", 0.0)),
        fx_linear=float(d.get("fx_linear", 0.0)),
        ir_dv01=float(d.get("ir_dv01", 0.0)),
    )


def compute_net_greeks(exposure: list[Instrument], hedge: list[Instrument]) -> GreeksBreakdown:
    # Compute Greeks for exposure and hedge portfolios
    exp_delta = sum(inst.mtm_value * inst.eq_linear  for inst in exposure)
    exp_gamma = sum(inst.mtm_value * inst.eq_quad    for inst in exposure)
    exp_vega  = sum(inst.mtm_value * inst.vol_linear for inst in exposure)
    exp_fx    = sum(inst.mtm_value * inst.fx_linear  for inst in exposure)
    exp_dv01  = sum(inst.ir_dv01 for inst in exposure)

    hed_delta = sum(inst.mtm_value * inst.eq_linear  for inst in hedge)
    hed_gamma = sum(inst.mtm_value * inst.eq_quad    for inst in hedge)
    hed_vega  = sum(inst.mtm_value * inst.vol_linear for inst in hedge)
    hed_fx    = sum(inst.mtm_value * inst.fx_linear  for inst in hedge)
    hed_dv01  = sum(inst.ir_dv01 for inst in hedge)

    exposure_greeks = Greeks(
        delta=exp_delta,
        gamma=exp_gamma,
        vega=exp_vega,
        fx=exp_fx,
        dv01=exp_dv01,
    )
    hedge_greeks = Greeks(
        delta=hed_delta,
        gamma=hed_gamma,
        vega=hed_vega,
        fx=hed_fx,
        dv01=hed_dv01,
    )
    net_greeks = Greeks(
        delta=exp_delta + hed_delta,
        gamma=exp_gamma + hed_gamma,
        vega=exp_vega + hed_vega,
        fx=exp_fx + hed_fx,
        dv01=exp_dv01 + hed_dv01,
    )

    return GreeksBreakdown(
        net=net_greeks,
        exposure=exposure_greeks,
        hedge=hedge_greeks,
    )
