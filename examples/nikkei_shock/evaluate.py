import argparse
import os
from typing import Any
from scenario import load_scenarios, ScenarioResponse
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

    scenarios, stats, conds = load_scenarios()
    num_runs = len(scenarios)

    def get_experiment_kwargs(run_idx: int) -> dict:
        scenario = scenarios[run_idx]

        return {
            "scenario": scenario,
            "stats": stats,
            "conds": conds,
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

    def validate_fn(response: ScenarioResponse) -> tuple[bool, str | None]:
        if not isinstance(response, ScenarioResponse):
            return False, f"Response is not of type ScenarioResponse: {type(response)}"
        if response.analysis is None or response.analysis.strip() == "" :
            return False, "Analysis is empty."
        return True, None

    def aggregate_metrics_fn(responses: list[ScenarioResponse]) -> dict:
        return generate_feedback(scenarios, stats, conds, responses, llm_judge)

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
