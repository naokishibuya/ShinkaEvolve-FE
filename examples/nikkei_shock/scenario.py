"""Load scenarios.yaml → normalized dicts + YAML strings.

This module handles loading and parsing of portfolio scenarios from YAML
configuration files, including instrument normalization and Greek computation.
"""
import yaml
import numpy as np
from pathlib import Path
from quant_types import Scenario, Instrument, Greeks, RiskStats


def load_scenarios(path: str | Path | None = None) -> tuple[list[Scenario], RiskStats]:
    """Load scenarios and risk stats from YAML file.

    Args:
        path: Path to scenarios.yaml file (defaults to same directory)

    Returns:
        Tuple of (list of scenarios, risk statistics)
    """
    path = Path(path or Path(__file__).parent / "scenarios.yaml")
    data = yaml.safe_load(path.read_text())

    scenarios = []
    for s in data["scenarios"]:
        exposure = [normalize_instrument(i) for i in s["exposure"]]
        hedge = [normalize_instrument(i) for i in s["hedge"]]
        greeks = compute_greeks(exposure, hedge)
        scenarios.append(
            Scenario(
                name=s["name"],
                description=s["description"],
                exposure=exposure,
                hedge=hedge,
                greeks=greeks,
            )
        )

    stats = load_stats(data["stats"])

    return scenarios, stats


def normalize_instrument(d: dict) -> Instrument:
    """Convert raw YAML dict to Instrument dataclass.

    Args:
        d: Dictionary with instrument fields from YAML

    Returns:
        Instrument with normalized field types
    """
    return Instrument(
        name=d["name"],
        mtm_value=float(d["mtm_value"]),
        eq_linear=float(d.get("eq_linear", 0.0)),
        eq_quad=float(d.get("eq_quad", 0.0)),
        vol_linear=float(d.get("vol_linear", 0.0)),
        fx_linear=float(d.get("fx_linear", 0.0)),
        ir_dv01=float(d.get("ir_dv01", 0.0)),
    )


def compute_greeks(exposure: list[Instrument], hedge: list[Instrument]) -> Greeks:
    """Compute aggregate Greeks for combined exposure and hedge portfolios.

    Args:
        exposure: List of exposure instruments
        hedge: List of hedge instruments

    Returns:
        Greeks representing total portfolio sensitivities
    """
    instruments = exposure + hedge
    delta = sum(inst.mtm_value * inst.eq_linear  for inst in instruments)
    gamma = sum(inst.mtm_value * inst.eq_quad    for inst in instruments)
    vega  = sum(inst.mtm_value * inst.vol_linear for inst in instruments)
    fx    = sum(inst.mtm_value * inst.fx_linear  for inst in instruments)
    dv01  = sum(inst.ir_dv01 for inst in instruments)

    return Greeks(
        delta=delta,
        gamma=gamma,
        vega=vega,
        fx=fx,
        dv01=dv01,
    )


def load_stats(cfg: dict) -> RiskStats:
    """Parse risk statistics from YAML config dict.

    Args:
        cfg: Dictionary with stats configuration from YAML

    Returns:
        RiskStats with validated volatilities and correlations
    """
    eq_vol     = float(cfg["eq_vol"])
    vol_of_vol = float(cfg["vol_of_vol"])
    fx_vol     = float(cfg["fx_vol"])
    ir_vol     = float(cfg["ir_vol"])

    horizon_days     = int(cfg["horizon_days"])
    corr_crisis      = np.array(cfg["corr_crisis"], float)
    max_factor_sigma = float(cfg["max_factor_sigma"])
    max_joint_sigma  = float(cfg["max_joint_sigma"])

    assert eq_vol > 0, "eq_vol must be positive"
    assert vol_of_vol > 0, "vol_of_vol must be positive"
    assert fx_vol > 0, "fx_vol must be positive"
    assert ir_vol > 0, "ir_vol must be positive"

    assert horizon_days > 0, "horizon_days must be positive"
    assert corr_crisis.shape == (4, 4), "corr_crisis must be 4x4 matrix"
    assert max_factor_sigma > 0, "max_factor_sigma must be positive"
    assert max_joint_sigma > 0, "max_joint_sigma must be positive"

    return RiskStats(
        eq_vol=eq_vol,
        vol_of_vol=vol_of_vol,
        fx_vol=fx_vol,
        ir_vol=ir_vol,
        corr_crisis=corr_crisis,
        horizon_days=horizon_days,
        max_factor_sigma=max_factor_sigma,
        max_joint_sigma=max_joint_sigma,
    )
