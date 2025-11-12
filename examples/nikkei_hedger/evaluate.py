"""Shinka-compatible evaluator for Nikkei-225 hedging strategies."""
import argparse
import json
import numpy as np
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRA_PATHS = [REPO_ROOT / "src", REPO_ROOT / "ShinkaEvolve", REPO_ROOT / "examples"]
for extra in EXTRA_PATHS:
    if extra.exists() and str(extra) not in sys.path:
        sys.path.append(str(extra))

from shinka.core.wrap_eval import run_shinka_eval  # type: ignore  # noqa: E402


def _validate_result(result: Dict[str, Any]) -> tuple[bool, str | None]:
    try:
        pnl = np.asarray(result.get("final_pnl"), dtype=float)
        if pnl.size == 0:
            return False, "Missing PnL vector"
        if not np.isfinite(pnl).all():
            return False, "Non-finite PnL values"
        return True, None
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def _aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Nikkei hedging programs via run_shinka_eval")
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    parser.add_argument("--scenario_dir", required=True)
    parser.add_argument("--runs", type=int, default=None, help="Number of evaluation runs (defaults to #scenarios)")
    parser.add_argument("--strike", type=float, default=33000.0)
    parser.add_argument("--maturity_days", type=int, default=21)
    parser.add_argument("--option_type", choices=["call", "put"], default="call")
    parser.add_argument("--hedge_ratio", type=float, default=1.0)
    parser.add_argument("--rebalance_steps", type=int, default=1)
    parser.add_argument("--transaction_cost_bps", type=float, default=5.0)
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir)
    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario dir not found: {scenario_dir}")
    scenario_files = sorted(scenario_dir.glob("*.npz"))
    if not scenario_files:
        raise FileNotFoundError(f"No .npz scenarios in {scenario_dir}")

    run_total = args.runs if args.runs is not None else len(scenario_files)

    def _kwargs_builder(run_idx: int) -> Dict[str, Any]:
        scenario_path = scenario_files[run_idx % len(scenario_files)]
        return {
            "scenario_path": str(scenario_path),
            "strike": args.strike,
            "maturity_days": args.maturity_days,
            "option_type": args.option_type,
            "hedge_ratio": args.hedge_ratio,
            "rebalance_steps": args.rebalance_steps,
            "transaction_cost_bps": args.transaction_cost_bps,
        }

    metrics, correct, error_msg = run_shinka_eval(
        program_path=args.program_path,
        results_dir=args.results_dir,
        experiment_fn_name="run_strategy",
        num_runs=run_total,
        get_experiment_kwargs=_kwargs_builder,
        validate_fn=_validate_result,
        aggregate_metrics_fn=_aggregate,
    )

    Path(args.results_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.results_dir) / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (Path(args.results_dir) / "correct.json").write_text(
        json.dumps({"correct": bool(correct), "error": error_msg}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
