"""Shinka-compatible evaluator for Nikkei-225 hedging strategies."""
import argparse
import numpy as np
import os
from pathlib import Path
from typing import Any
from shinka.core.wrap_eval import run_shinka_eval


def _validate_result(result: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        pnl = np.asarray(result.get("final_pnl"), dtype=float)
        if pnl.size == 0:
            return False, "Missing PnL vector"
        if not np.isfinite(pnl).all():
            return False, "Non-finite PnL values"
        return True, None
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "combined_score": 0.0,
            "avg_pnl": 0.0,
            "pnl_std": 0.0,
            "tail_pnl_5pct": 0.0,
            "runs": 0,
        }
    pnl_matrix = np.stack([np.asarray(r["final_pnl"], dtype=float) for r in results])
    mean_per_path = pnl_matrix.mean(axis=1)
    avg_pnl = float(mean_per_path.mean())
    std_pnl = float(mean_per_path.std())
    tail = float(np.percentile(mean_per_path, 5))
    score = avg_pnl - std_pnl
    return {
        "combined_score": score,
        "avg_pnl": avg_pnl,
        "pnl_std": std_pnl,
        "tail_pnl_5pct": tail,
        "runs": len(results),
    }


def main(
    program_path: str,
    results_dir: str,
    strike: float,
    maturity_days: int,
    option_type: str,
    hedge_ratio: float,
    rebalance_steps: int,
    transaction_cost_bps: float,
    scenario_dir: str,
):
    """Runs the Nikkei hedger evaluation using shinka.eval."""
    print(f"Evaluating program: {program_path}")
    print(f"Saving results to: {results_dir}")
    print(f"Using scenarios from: {scenario_dir}")
    print(f"Option strike: {strike}")
    print(f"Option maturity (days): {maturity_days}")
    print(f"Option type: {option_type}")
    print(f"Hedge ratio: {hedge_ratio}")
    print(f"Rebalance steps: {rebalance_steps}")
    print(f"Transaction cost (bps): {transaction_cost_bps}")

    os.makedirs(results_dir, exist_ok=True)

    num_experiment_runs = 1

    # get the script dir
    script_dir = Path(__file__).parent.resolve()
    scenario_dir_path = (script_dir / scenario_dir).resolve()
    scenario_files = sorted(scenario_dir_path.glob("*.npz"))
    if not scenario_files:
        raise ValueError(f"No scenario files found in {scenario_dir}")
    print(f"Found {len(scenario_files)} scenario files in {scenario_dir}")

    # Define a nested function to build kwargs for each experiment run
    def _kwargs_builder(run_idx: int) -> dict[str, Any]:
        scenario_path = scenario_files[run_idx % len(scenario_files)]
        return {
            "scenario_path": str(scenario_path),
            "strike": strike,
            "maturity_days": maturity_days,
            "option_type": option_type,
            "hedge_ratio": hedge_ratio,
            "rebalance_steps": rebalance_steps,
            "transaction_cost_bps": transaction_cost_bps,
        }

    # invoke run_shinka_eval
    metrics, correct, error_msg = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_strategy",
        num_runs=num_experiment_runs,
        get_experiment_kwargs=_kwargs_builder,
        validate_fn=_validate_result,
        aggregate_metrics_fn=_aggregate,
    )

    if correct:
        print("Evaluation and Validation completed successfully.")
    else:
        print(f"Evaluation or Validation failed: {error_msg}")

    print("Metrics:")
    for key, value in metrics.items():
        if isinstance(value, str) and len(value) > 100:
            print(f"  {key}: <string_too_long_to_display>")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nikkei hedger evaluator using shinka.eval"
    )
    parser.add_argument(
        "--program_path",
        type=str,
        default="initial.py",
        help="Path to program to evaluate (must contain 'run_strategy' function)",
    )
    parser.add_argument(
        "--results_dir",
        type=str,
        default="results",
        help="Dir to save results (metrics.json, correct.json, extra.npz)",
    )
    parser.add_argument(
        "--strike",
        type=float,
        default=50000.0,
        help="Option strike price",
    )
    parser.add_argument(
        "--maturity_days",
        type=int,
        default=21,
        help="Option maturity in days",
    )
    parser.add_argument(
        "--option_type",
        type=str,
        default="call",
        help="Option type: call or put",
    )
    parser.add_argument(
        "--hedge_ratio",
        type=float,
        default=1.0,
        help="Hedge ratio",
    )
    parser.add_argument(
        "--rebalance_steps",
        type=int,
        default=1,
        help="Number of rebalance steps",
    )
    parser.add_argument(
        "--transaction_cost_bps",
        type=float,
        default=5.0,
        help="Transaction cost in basis points",
    )
    parser.add_argument(
        "--scenario_dir",
        type=str,
        default=".scenarios/nikkei_day21",
        help="Directory containing scenario .npz files",
    )
    args = parser.parse_args()
    main(
        args.program_path,
        args.results_dir,
        args.strike,
        args.maturity_days,
        args.option_type,
        args.hedge_ratio,
        args.rebalance_steps,
        args.transaction_cost_bps,
        args.scenario_dir,
    )
