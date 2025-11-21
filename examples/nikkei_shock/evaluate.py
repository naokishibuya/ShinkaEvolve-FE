import argparse
import os
from typing import Any
from scenario import load_scenarios
from quant_utils import optimize_worst_case_shock
from examples.nikkei_shock.review import generate_feedback
from shinka.core import run_shinka_eval
from shinka.llm import LLMClient


def main(
    program_path: str,
    results_dir: str,
    llm_analyst: dict[str, Any] | None = None,
    llm_reviewer: dict[str, Any] | None = None,
    llm_summarizer: dict[str, Any] | None = None,
) -> tuple[dict, bool, str]:
    """Orchestrate evaluation of prompt-builder function.

    Runs the evaluation flow: load scenarios → optimize shocks → generate prompts
    → invoke analyst LLM → review analyses → return metrics.

    Args:
        program_path: Path to prompt-builder function (initial.py or evolved version)
        results_dir: Directory to save evaluation results
        llm_analyst: Optional analyst LLM config (defaults to local Ollama)
        llm_reviewer: Optional reviewer LLM config (defaults to local Ollama)
        llm_summarizer: Optional summarizer LLM config for difficulty weighting
                       (defaults to llm_reviewer). For faster local testing, use a
                       lighter model like {"model_names": "ollama::qwen2.5:3b"}

    Returns:
        Tuple of (metrics dict, success flag, error message)
    """
    print(f"Evaluating program: {program_path}")
    print(f"Saving results to: {results_dir}")
    os.makedirs(results_dir, exist_ok=True)

    scenarios, stats = load_scenarios()
    num_runs = len(scenarios)

    opt_results = [optimize_worst_case_shock(scenario, stats) for scenario in scenarios]
    shock_list, factor_moves_list, pnl_summary_list = zip(*opt_results)

    def get_experiment_kwargs(run_idx: int) -> dict:
        scenario     = scenarios[run_idx]
        shock        = shock_list[run_idx]
        factor_moves = factor_moves_list[run_idx]
        pnl_summary  = pnl_summary_list[run_idx]
        print("-" * 50)
        print(f"Run {run_idx+1}/{num_runs}")
        print(f"  scenario={scenario.name}")
        print(f"  shock={shock}")
        print(f"  factor_moves={factor_moves}")
        print(f"  pnl_summary={pnl_summary}")
        return dict(
            scenario=scenario,
            stats=stats,
            shock=shock,
            factor_moves=factor_moves,
            pnl_summary=pnl_summary,
        )

    def validate_fn(prompt: str) -> tuple[bool, str | None]:
        if not isinstance(prompt, str):
            return False, f"Returned prompt is not of string: {type(prompt)}"
        if prompt is None or prompt.strip() == "":
            return False, "Prompt is empty."
        return True, None

    if llm_analyst is None:
        llm_analyst = {
            "model_names": "ollama::llama3.1:8b",
            "temperatures": 0.0,
            "max_tokens": 4096,
            "reasoning_efforts": "low",
            "verbose": True,
        }

    if llm_reviewer is None:
        llm_reviewer = llm_analyst

    if llm_summarizer is None:
        llm_summarizer = llm_reviewer

    llm_analyst = LLMClient(**llm_analyst)
    llm_reviewer = LLMClient(**llm_reviewer)
    llm_summarizer = LLMClient(**llm_summarizer)

    def aggregate_metrics_fn(prompt_list: list[str]) -> dict:
        # Invoke analyst LLM for each prompt to generate analyses
        analysis_list = []
        for i, prompt in enumerate(prompt_list):
            print("-" * 50)
            print(f"Generating analysis {i+1}/{len(prompt_list)} with analyst LLM...")
            response = llm_analyst.query(
                msg=prompt,
                system_msg=(
                    "You are an expert financial risk analyst. "
                    "Provide a professional analysis report. "
                    "DO NOT use conversational language like 'Certainly...', 'Sure...', 'Here is...'. "
                    "DO NOT end with phrases like 'please let me know', 'if you need', 'feel free to ask'. "
                    "Write as a direct, technical analysis report."
                ),
                llm_kwargs=llm_analyst.get_kwargs(),
            )
            print(response.content)
            analysis_list.append(response.content)

        # Now evaluate the analyses with reviewer LLM
        return generate_feedback(
            scenarios,
            stats=stats,
            shock_params_list=shock_list,
            factor_moves_list=factor_moves_list,
            pnl_summary_list=pnl_summary_list,
            prompt_list=prompt_list,
            analysis_list=analysis_list,
            llm_reviewer=llm_reviewer,
            llm_summarizer=llm_summarizer,
            results_dir=results_dir)

    metrics, correct, error = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="build_analysis_prompt",
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
