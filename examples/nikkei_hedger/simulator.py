"""Nikkei-225 Monte Carlo simulator for hedging experiments."""
import numpy as np
from dataclasses import dataclass
from typing import Iterable


@dataclass
class MarketParams:
    spot0         : float = 50000.0  # initial Nikkei level
    mu            : float = 0.1      # drift per year
    sigma         : float = 0.2      # annualized volatility
    vol_of_vol    : float = 0.15     # for stochastic vol
    mean_rev      : float = 1.0      # mean reversion speed of variance
    jump_intensity: float = 0.0      # Poisson jumps per year
    jump_mean     : float = -0.02
    jump_std      : float = 0.05
    rate          : float = 0.01     # short rate per year


@dataclass
class SimulationConfig:
    maturity_days    : int = 21           # ~1 trading month
    steps_per_day    : int = 2            # Tokyo day + SGX night
    paths            : int = 64
    seed             : int | None = None
    include_jumps    : bool = False
    include_stoch_vol: bool = True

    @property
    def dt(self) -> float:
        return 1.0 / 252.0 / self.steps_per_day

    @property
    def steps(self) -> int:
        return self.maturity_days * self.steps_per_day


@dataclass
class Scenario:
    spots: np.ndarray  # shape (steps+1, paths)
    vols: np.ndarray   # realized/instantaneous vol per step
    times: np.ndarray  # time-to-maturity per step
    rate: float


def simulate_scenarios(
    market: MarketParams,
    config: SimulationConfig,
) -> Scenario:
    rng = np.random.default_rng(config.seed)
    steps = config.steps
    paths = config.paths
    dt = config.dt

    spots = np.empty((steps + 1, paths), dtype=np.float64)
    vols = np.empty_like(spots)
    times = np.empty_like(spots)

    spots[0, :] = market.spot0
    inst_vol = np.full(paths, market.sigma)
    vols[0, :] = inst_vol
    times[0, :] = config.maturity_days / 252.0

    # Simulate paths
    for t in range(1, steps + 1):
        if config.include_stoch_vol:
            inst_vol += market.mean_rev * (market.sigma - inst_vol) * dt \
                + market.vol_of_vol * np.sqrt(max(inst_vol.mean(), 1e-6)) * np.sqrt(dt) * rng.standard_normal(paths)
            inst_vol = np.clip(inst_vol, 0.05, 0.6)
        dW = rng.standard_normal(paths) * np.sqrt(dt)
        drift = (market.mu - 0.5 * inst_vol**2) * dt
        jump = 0.0
        if config.include_jumps and market.jump_intensity > 0:
            jump_mask = rng.uniform(size=paths) < market.jump_intensity * dt
            if np.any(jump_mask):
                jump = np.zeros(paths)
                jump[jump_mask] = rng.normal(market.jump_mean, market.jump_std, size=jump_mask.sum())
        spots[t, :] = spots[t - 1, :] * np.exp(drift + inst_vol * dW + jump)
        vols[t, :] = inst_vol
        times[t, :] = max(config.maturity_days - t / config.steps_per_day, 0) / 252.0

    return Scenario(spots=spots, vols=vols, times=times, rate=market.rate)


def batched_scenarios(
    market: MarketParams,
    config: SimulationConfig,
    batches: int,
    seeds: Iterable[int] | None = None,
) -> list[Scenario]:
    scenarios: list[Scenario] = []
    if seeds is None:
        seeds = range(batches)
    for i, seed in zip(range(batches), seeds):
        cfg = SimulationConfig(
            maturity_days=config.maturity_days,
            steps_per_day=config.steps_per_day,
            paths=config.paths,
            seed=seed,
            include_jumps=config.include_jumps,
            include_stoch_vol=config.include_stoch_vol,
        )
        scenarios.append(simulate_scenarios(market, cfg))
    return scenarios
