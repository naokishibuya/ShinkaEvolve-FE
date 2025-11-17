import argparse
import copy
import os
from typing import Any
from scenario import load_scenarios
from feedback import generate_feedback
from utils import compute_net_greeks
from shinka.core import run_shinka_eval
from shinka.llm import LLMClient


def main(
    program_path: str,
    results_dir: str,
    llm_judge: dict[str, Any] | None = None,
) -> tuple[dict, bool, str]:
    print(f"Evaluating program: {program_path}")
    print(f"Saving results to: {results_dir}")
    os.makedirs(results_dir, exist_ok=True)

    scenarios, stats, config = load_scenarios()
    num_runs = len(scenarios)

    def get_experiment_kwargs(run_idx: int) -> dict:
        scenario = copy.deepcopy(scenarios[run_idx])
        name = scenario["name"]
        description = scenario["description"]
        exposure = scenario["exposure"]
        hedge = scenario["hedge"]
        net_greeks = compute_net_greeks(exposure, hedge)
        return {
            "name": name,
            "description": description,
            "exposure": exposure,
            "hedge": hedge,
            "net_greeks": net_greeks,
            "stats": stats,
            "config": config,
        }

    if llm_judge is None:
        llm_judge = {
            "model_names": "ollama::llama3.1:8b",
            "temperatures": 0.0,
            "max_tokens": 4096,
            "reasoning_efforts": "low",
            "verbose": True,
        }

    llm_judge = LLMClient(**llm_judge)

    def validate_fn(response: dict[str, Any]) -> tuple[bool, str | None]:
        return validate_response(response, config)

    def aggregate_metrics_fn(responses: list[dict[str, Any]]) -> dict:

        return generate_feedback(scenarios, stats, config, responses, llm_judge)

    metrics, correct, error = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="analyze_hedge_weakness",
        num_runs=num_runs,
        get_experiment_kwargs=get_experiment_kwargs,
        validate_fn=validate_fn,
        aggregate_metrics_fn=aggregate_metrics_fn,
    )
    return metrics, correct, error


def validate_response(response: dict[str, Any], config: dict) -> tuple[bool, str | None]:
    try:
        _assert_response_value(response, "analysis", str)
        shock_params = _assert_response_value(response, "shock_params", dict)

        max_sigma_ratio = float(config["max_sigma_ratio"])
        sigma_ratio_range = (-max_sigma_ratio, max_sigma_ratio)
        _assert_response_value(shock_params, "eq_shock_sigma",  (float, int), sigma_ratio_range)
        _assert_response_value(shock_params, "vol_shock_sigma", (float, int), sigma_ratio_range)
        _assert_response_value(shock_params, "fx_shock_sigma",  (float, int), sigma_ratio_range)
        _assert_response_value(shock_params, "ir_shock_sigma",  (float, int), sigma_ratio_range)

        max_horizon_days = int(config["max_horizon_days"])
        _assert_response_value(shock_params, "horizon_days", int, (1, max_horizon_days))
        _assert_response_value(shock_params, "crisis_intensity", (float, int), (0.0, 1.0))

        rationale = _assert_response_value(shock_params, "rationale", dict)

        # Allow None or str for each rationale field, per spec
        optional_str_type = (str, type(None))
        _assert_response_value(rationale, "equity",      optional_str_type)
        _assert_response_value(rationale, "volatility",  optional_str_type)
        _assert_response_value(rationale, "fx",          optional_str_type)
        _assert_response_value(rationale, "rates",       optional_str_type)
        _assert_response_value(rationale, "correlation", optional_str_type)

    except Exception as e:
        print(f"Validation error: {e}")
        return False, str(e)
    return True, None


def _assert_response_value(
    container: dict[str, Any],
    key: str,
    expected_type: type | tuple[type, ...],
    value_range: tuple[float | int, float | int] | None = None,
) -> Any:
    if key not in container:
        raise KeyError(f"'{key}' is missing")
    value = container[key]

    # Type check
    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_names = ", ".join(t.__name__ for t in expected_type)
        else:
            expected_names = expected_type.__name__
        raise TypeError(
            f"'{key}' is not of type(s) {expected_names} "
            f"(got {type(value).__name__})"
        )

    # Optional range check (for numerics)
    if value_range is not None:
        low, high = value_range
        if not (low <= value <= high):
            raise ValueError(
                f"'{key}' is out of range {value_range} (got {value})"
            )
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nikkei scenario generator")
    parser.add_argument("--program_path", type=str, required=True, help="Path to program being evaluated")
    parser.add_argument("--results_dir", type=str, required=True, help="Directory to save results")
    args = parser.parse_args()

    metrics, correct, err = main(args.program_path, args.results_dir)

    if correct:
        print(f"Evaluation successful! Combined score: {metrics['combined_score']:.2e}")
        print("\nText feedback:")
        print(metrics["text_feedback"])
    else:
        print(f"Evaluation failed: {err}")
