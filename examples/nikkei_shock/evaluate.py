import argparse
import copy
import os
from typing import Any
from scenario import load_scenarios
from feedback import generate_feedback
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

    scenarios = load_scenarios()
    num_runs = len(scenarios)

    def get_experiment_kwargs(run_idx: int) -> dict:
        return {"scenario": copy.deepcopy(scenarios[run_idx])}

    def validate_fn(analysis: Any) -> tuple[bool, str | None]:
        if analysis is None:
            return False, "The returned analysis is None"
        if not isinstance(analysis, str):
            return False, f"The returned analysis is not a string (got {type(analysis).__name__})"
        return True, None

    if llm_judge is None:
        llm_judge = {
            "model_names": "ollama::llama3.1:8b",
            "temperatures": 0.0,
            "max_tokens": 4096,
            "reasoning_efforts": "low",
            "verbose": True,
        }

    llm_judge = LLMClient(**llm_judge)

    def aggregate_metrics_fn(analyses: list[str]) -> dict:
        return generate_feedback(scenarios, analyses, llm_judge)

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
