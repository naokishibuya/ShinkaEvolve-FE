
""" Load scenarios.yaml → normalized dicts + YAML strings """
import numpy as np
import yaml
from pathlib import Path
from typing import Any


def load_scenarios(path: str | Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Load scenarios.yaml → ready-to-run scenario dicts."""
    path = Path(path or Path(__file__).parent / "scenarios.yaml")
    data = yaml.safe_load(path.read_text())

    stats = load_stats(data["stats"])
    config = load_config(data["config"])

    scenarios: list[dict[str, Any]] = []
    for s in data["scenarios"]:
        name = s["name"]
        desc = s["description"]

        exposure = normalize_instruments(s["exposure"])
        hedge = normalize_instruments(s["hedge"])

        scenarios.append({
            "name": name,
            "description": desc,
            "exposure": exposure,
            "hedge": hedge,
        })
    return scenarios, stats, config


def load_stats(stats_cfg: dict[str, Any]) -> dict[str, Any]:
    """Convert YAML stats section into runtime stats."""
    return {
        "eq_vol": float(stats_cfg["eq_vol"]),
        "vol_of_vol": float(stats_cfg["vol_of_vol"]),
        "fx_vol": float(stats_cfg["fx_vol"]),
        "ir_vol": float(stats_cfg["ir_vol"]),
        "corr_normal": np.array(stats_cfg["corr_normal"], float),
        "corr_crisis": np.array(stats_cfg["corr_crisis"], float),
    }


def load_config(config_cfg: dict[str, Any]) -> dict[str, Any]:
    """Convert YAML config section into runtime config."""
    return {
        "max_sigma_ratio": float(config_cfg["max_sigma_ratio"]),
        "max_horizon_days": int(config_cfg["max_horizon_days"]),
    }


def normalize_instruments(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_instrument(inst) for inst in raw]


def normalize_instrument(inst: dict[str, Any]) -> dict[str, Any]:
    """Ensure all instrument fields exist and are numeric."""
    keys = ["name", "mtm_value", "eq_linear", "eq_quad",
            "vol_linear", "fx_linear", "ir_dv01"]

    # assert fields are not something we don't expect
    for k in inst.keys():
        if k not in keys:
            raise ValueError(f"Unexpected instrument field: {k}")

    out = {k: 0.0 for k in keys}
    out["name"] = inst["name"]
    out["mtm_value"] = float(inst["mtm_value"])

    for k in keys:
        if k in inst and k != "name":
            out[k] = float(inst[k])

    return out
