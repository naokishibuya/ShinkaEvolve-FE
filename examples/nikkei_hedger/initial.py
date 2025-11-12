"""Baseline hedging policy for Nikkei-225 options."""
import math
import numpy as np
from dataclasses import dataclass
from typing import Any
from types import SimpleNamespace


@dataclass
class OptionContract:
    strike: float
    maturity_years: float
    option_type: str = "call"  # or "put"


@dataclass
class PolicyConfig:
    hedge_ratio: float = 1.0  # scale delta hedge
    rebalance_steps: int = 1  # hedge every step
    transaction_cost_bps: float = 5.0  # cost per trade in basis points


def _black_scholes_delta(spot: float, strike: float, ttm: float, vol: float, rate: float, opt_type: str) -> float:
    if ttm <= 0:
        intrinsic = 1.0 if (spot > strike and opt_type == "call") else -1.0 if (spot < strike and opt_type == "put") else 0.0
        return intrinsic
    if vol <= 0:
        return 0.0
    denom = vol * np.sqrt(ttm)
    d1 = (np.log(spot / strike) + (rate + 0.5 * vol * vol) * ttm) / denom
    if opt_type == "call":
        return 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    return -0.5 * (1 + math.erf(-d1 / math.sqrt(2)))


# EVOLVE-BLOCK-START
def decide_trade(option: OptionContract, policy: PolicyConfig, state: dict[str, float]) -> float:
    target = state["delta"] * policy.hedge_ratio
    return target - state["hedge_inventory"]
# EVOLVE-BLOCK-END

def run_strategy(
    *,
    scenario_path: str,
    strike: float = 33000.0,
    maturity_days: int = 21,
    option_type: str = "call",
    hedge_ratio: float = 1.0,
    rebalance_steps: int = 1,
    transaction_cost_bps: float = 5.0,
) -> dict[str, Any]:
    scenario = _load_scenario(scenario_path)
    spots = scenario.spots
    vols = scenario.vols
    times = scenario.times
    steps, paths = spots.shape
    option = OptionContract(strike=strike, maturity_years=maturity_days / 252.0, option_type=option_type)
    policy = PolicyConfig(
        hedge_ratio=hedge_ratio,
        rebalance_steps=rebalance_steps,
        transaction_cost_bps=transaction_cost_bps,
    )
    hedge_inventory = np.zeros(paths)
    cash = np.zeros(paths)
    prev_trade = np.zeros(paths)
    trade_log: list[dict[str, float]] = []
    for step in range(steps - 1):
        if step % policy.rebalance_steps != 0:
            continue
        spot_vec = spots[step]
        vol_vec = vols[step]
        ttm_vec = times[step]
        deltas = np.array([
            _black_scholes_delta(
                spot_vec[i],
                option.strike,
                max(ttm_vec[i], 1e-6),
                max(vol_vec[i], 1e-4),
                scenario.rate,
                option.option_type,
            )
            for i in range(paths)
        ])
        prices = np.array([
            _black_scholes_price(
                spot_vec[i],
                option.strike,
                max(ttm_vec[i], 1e-6),
                max(vol_vec[i], 1e-4),
                scenario.rate,
                option.option_type,
            )
            for i in range(paths)
        ])
        for i in range(paths):
            state = {
                "step": step,
                "total_steps": steps,
                "spot": float(spot_vec[i]),
                "vol": float(vol_vec[i]),
                "ttm": float(ttm_vec[i]),
                "delta": float(deltas[i]),
                "bs_price": float(prices[i]),
                "hedge_inventory": float(hedge_inventory[i]),
                "cash": float(cash[i]),
                "prev_trade": float(prev_trade[i]),
                "transaction_cost_bps": transaction_cost_bps,
            }
            trade = float(decide_trade(option, policy, state))
            hedge_inventory[i] += trade
            prev_trade[i] = trade
            trade_cost = abs(trade) * spot_vec[i] * (transaction_cost_bps / 1e4)
            cash[i] -= trade_cost
        trade_log.append(
            {
                "step": float(step),
                "avg_abs_trade": float(np.mean(np.abs(prev_trade))),
                "avg_delta": float(np.mean(deltas)),
            }
        )

    final_spot = spots[-1]
    payoff = _option_payoff(final_spot, option)
    final_pnl = payoff - hedge_inventory * final_spot + cash
    return {
        "scenario_path": scenario_path,
        "final_pnl": final_pnl.tolist(),
        "avg_pnl": float(final_pnl.mean()),
        "trade_log": trade_log,
    }


if __name__ == "__main__":
    result = run_strategy(scenario_path="demo_scenario.npz")
    print(result["avg_pnl"])


def _load_scenario(path: str):
    with np.load(path) as data:
        return SimpleNamespace(
            spots=data["spots"],
            vols=data["vols"],
            times=data["times"],
            rate=float(data["rate"]),
        )


def _black_scholes_price(spot: float, strike: float, ttm: float, vol: float, rate: float, opt_type: str) -> float:
    if ttm <= 0:
        payoff = max(spot - strike, 0.0) if opt_type == "call" else max(strike - spot, 0.0)
        return payoff
    std = vol * math.sqrt(ttm)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * ttm) / std
    d2 = d1 - std
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    if opt_type == "call":
        return spot * N(d1) - strike * math.exp(-rate * ttm) * N(d2)
    return strike * math.exp(-rate * ttm) * N(-d2) - spot * N(-d1)


def _option_payoff(spot: np.ndarray, option: OptionContract) -> np.ndarray:
    if option.option_type == "call":
        return np.maximum(spot - option.strike, 0.0)
    return np.maximum(option.strike - spot, 0.0)
