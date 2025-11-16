import argparse
import os
from typing import Any
from scenario import load_scenarios
from feedback import generate_feedback
from shinka import llm
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
        return {"scenario": scenarios[run_idx]}

    def validate_fn(run_result: dict) -> tuple[bool, str]:
        if run_result is None:
            return False, "No run_result returned"
        if "scenario" not in run_result:
            return False, "Missing 'scenario' in run_result"
        if "analysis" not in run_result:
            return False, "Missing 'analysis' in run_result"
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

    def aggregate_metrics_fn(all_run_results: list[dict]) -> dict:
        return generate_feedback(all_run_results, llm_judge)

    metrics, correct, err = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_experiment",
        num_runs=num_runs,
        get_experiment_kwargs=get_experiment_kwargs,
        validate_fn=validate_fn,
        aggregate_metrics_fn=aggregate_metrics_fn,
    )
    return metrics, correct, err


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
