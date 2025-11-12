"""Helper utilities for generating and persisting Nikkei hedging scenarios."""
import numpy as np
from dataclasses import asdict
from pathlib import Path
from typing import Iterable
from simulator import MarketParams, Scenario, SimulationConfig, simulate_scenarios


def save_scenario(scenario: Scenario, path: str | Path) -> None:
    target = Path(path)
    data = {
        "spots": scenario.spots,
        "vols": scenario.vols,
        "times": scenario.times,
        "rate": scenario.rate,
    }
    np.savez(target, **data)


def load_scenario(path: str | Path) -> Scenario:
    src = Path(path)
    with np.load(src) as data:
        spots = data["spots"]
        vols = data["vols"]
        times = data["times"]
        rate = float(data["rate"])
    return Scenario(spots=spots, vols=vols, times=times, rate=rate)


def generate_and_save_batch(
    out_dir: str | Path,
    market: MarketParams,
    config: SimulationConfig,
    batches: int,
    seeds: Iterable[int] | None = None,
) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if seeds is None:
        seeds = range(batches)
    for idx, seed in zip(range(batches), seeds):
        cfg = SimulationConfig(**{**asdict(config), "seed": seed})
        scenario = simulate_scenarios(market, cfg)
        target = out / f"scenario_{idx:03d}.npz"
        save_scenario(scenario, target)
        paths.append(target)
    return paths


if __name__ == "__main__":
    import os
    from simulator import MarketParams, SimulationConfig
    from scenarios import generate_and_save_batch

    # get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scenario_dir = os.path.join(script_dir, ".scenarios")
    train_dir = os.path.join(scenario_dir, "nikkei_day21")
    val_dir = os.path.join(scenario_dir, "nikkei_day21_holdout")

    market = MarketParams()
    config = SimulationConfig(paths=64, maturity_days=21, seed=42)
    generate_and_save_batch(train_dir, market, config, batches=10, seeds=range(10))
    generate_and_save_batch(val_dir, market, config, batches=10, seeds=range(100, 110))  # different seeds
