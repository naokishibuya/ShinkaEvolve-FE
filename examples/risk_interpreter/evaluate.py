"""
Evaluation harness for risk_interpreter variant.
Tests strategies across multiple scenarios.
"""

import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from shinka.core import run_shinka_eval


def main(program_path: str, results_dir: str):
    """
    Main evaluation function called by ShinkaEvolve.
    
    Args:
        program_path: Path to the program being evaluated (initial.py or evolved variant)
        results_dir: Directory to save results
    """
    
    metrics, correct, err = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_experiment",
        num_runs=3,  # Test on 3 scenarios
        get_experiment_kwargs=get_scenario_kwargs,
        aggregate_metrics_fn=aggregate_results,
        validate_fn=validate_solution,
    )
    
    return metrics, correct, err


def get_scenario_kwargs(run_idx: int) -> dict:
    """
    Return kwargs for each evaluation run.
    Each run uses a different test scenario.
    """
    
    script_dir = Path(__file__).parent
    scenarios_dir = script_dir / 'scenarios'
    
    scenario_files = [
        'boj_policy.json',
        'market_stress.json',
        'calm_market.json'
    ]
    
    scenario_path = scenarios_dir / scenario_files[run_idx % len(scenario_files)]
    
    return {
        'scenario_path': str(scenario_path)
    }


def aggregate_results(results: List[Tuple[Dict, str]]) -> Dict:
    """
    Aggregate results from multiple scenario runs.
    
    Args:
        results: List of (metrics_dict, feedback_text) tuples from each run
    
    Returns:
        Aggregated metrics dictionary with structure:
        - combined_score: float (primary fitness for evolution)
        - public: dict (metrics visible to LLM)
        - private: dict (metrics for analysis only)
        - extra_data: dict (additional data saved as pickle)
        - text_feedback: str (feedback shown to LLM)
    """
    
    metrics_list = [r[0] for r in results]
    feedback_list = [r[1] for r in results]
    
    # Calculate aggregate statistics
    avg_score = sum(m['score'] for m in metrics_list) / len(metrics_list)
    avg_cost = sum(m['cost_pct'] for m in metrics_list) / len(metrics_list)
    avg_protection = sum(m['protection'] for m in metrics_list) / len(metrics_list)
    min_constraints = min(m['constraints_satisfied'] for m in metrics_list)
    
    # Calculate robustness (consistency across scenarios)
    scores = [m['score'] for m in metrics_list]
    score_variance = sum((s - avg_score)**2 for s in scores) / len(scores)
    score_std = score_variance ** 0.5
    robustness_score = 100.0 / (1.0 + score_std)  # Higher = more consistent
    
    # Combined fitness (what evolution optimizes)
    combined_score = avg_score + robustness_score * 5
    
    # Identify best and worst scenarios
    best_idx = max(range(len(metrics_list)), key=lambda i: metrics_list[i]['score'])
    worst_idx = min(range(len(metrics_list)), key=lambda i: metrics_list[i]['score'])
    
    scenario_names = ['BOJ Policy', 'Market Stress', 'Calm Market']
    
    return {
        # Primary fitness (what ShinkaEvolve maximizes)
        'combined_score': float(combined_score),
        
        # Public metrics (visible to LLM for generating mutations)
        'public': {
            'avg_score': float(avg_score),
            'avg_cost_pct': float(avg_cost),
            'avg_protection': float(avg_protection),
            'robustness': float(robustness_score),
            'min_constraints': int(min_constraints),
            'best_scenario': scenario_names[best_idx],
            'worst_scenario': scenario_names[worst_idx],
            'scenario_scores': {
                name: float(metrics_list[i]['score'])
                for i, name in enumerate(scenario_names)
            }
        },
        
        # Private metrics (not shown to LLM, for your analysis)
        'private': {
            'all_metrics': metrics_list,
            'score_std': float(score_std),
            'score_variance': float(score_variance)
        },
        
        # Extra data (saved as pickle)
        'extra_data': {
            'feedbacks': feedback_list,
            'detailed_results': results
        },
        
        # Text feedback (shown to LLM to guide evolution)
        'text_feedback': format_feedback_for_llm(
            metrics_list, 
            scenario_names,
            best_idx,
            worst_idx,
            avg_cost,
            avg_protection
        )
    }


def validate_solution(result: Tuple[Dict, str]) -> Tuple[bool, str]:
    """
    Validate that solution is reasonable.

    Args:
        result: (metrics_dict, feedback_text) tuple

    Returns:
        (is_valid, error_message) tuple
    """

    metrics, feedback = result

    # Check if we got valid metrics
    if metrics is None:
        return False, "Evaluation returned None"

    # Check if solution is feasible
    if not metrics.get('feasible', False):
        reason = metrics.get('infeasibility_reason', 'Unknown reason')
        error_msg = f"Infeasible solution - constraints violated:\n{reason}"
        return False, error_msg

    # Check if cost is reasonable (shouldn't be too high)
    if metrics['cost_pct'] > 0.10:  # More than 10% is unrealistic
        return False, f"Cost too high: {metrics['cost_pct']:.2%}"

    # Check if providing some protection
    if metrics['protection'] < 0.30:  # Less than 30% is too low
        return False, f"Protection too low: {metrics['protection']:.2%}"

    # Check if score is reasonable (not NaN or infinite)
    if not (0 <= metrics['score'] <= 300):
        return False, f"Score out of range: {metrics['score']}"

    return True, None


def format_feedback_for_llm(
    metrics_list: List[Dict],
    scenario_names: List[str],
    best_idx: int,
    worst_idx: int,
    avg_cost: float,
    avg_protection: float
) -> str:
    """
    Format feedback text that LLM will see.
    This guides the LLM on how to improve the strategy.
    """
    
    feedback = "PERFORMANCE ACROSS SCENARIOS:\n\n"
    
    for i, (metrics, name) in enumerate(zip(metrics_list, scenario_names)):
        marker = "✓" if i == best_idx else ("✗" if i == worst_idx else " ")
        feedback += f"{marker} {name}:\n"
        feedback += f"   Score: {metrics['score']:.1f}\n"
        feedback += f"   Cost: {metrics['cost_pct']:.2%}\n"
        feedback += f"   Protection: {metrics['protection']:.2%}\n"
        feedback += f"   Constraints: {metrics['constraints_satisfied']}/3\n\n"
    
    feedback += "ANALYSIS:\n"
    feedback += f"Best performance: {scenario_names[best_idx]}\n"
    feedback += f"Weakest performance: {scenario_names[worst_idx]}\n\n"
    
    # Provide specific suggestions
    feedback += "SUGGESTIONS FOR IMPROVEMENT:\n"
    
    if avg_cost > 0.025:
        feedback += "• Cost is high - consider adjusting cost_weight or using cheaper instruments\n"
    
    if avg_protection < 0.80:
        feedback += "• Protection is low - consider increasing risk_weight or protection_level\n"
    
    if metrics_list[worst_idx]['constraints_satisfied'] < 2:
        feedback += f"• Many constraints violated in {scenario_names[worst_idx]} - check constraint handling\n"
    
    # Check for scenario-specific issues
    worst_protection = min(m['protection'] for m in metrics_list)
    worst_cost = max(m['cost_pct'] for m in metrics_list)
    
    if worst_protection < 0.70:
        idx = [m['protection'] for m in metrics_list].index(worst_protection)
        feedback += f"• Very low protection in {scenario_names[idx]} - strategy may not adapt well to this scenario\n"
    
    if worst_cost > 0.035:
        idx = [m['cost_pct'] for m in metrics_list].index(worst_cost)
        feedback += f"• High cost in {scenario_names[idx]} - could be more cost-efficient\n"
    
    return feedback


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate risk interpreter strategy")
    parser.add_argument("--program_path", type=str, required=True,
                       help="Path to program being evaluated")
    parser.add_argument("--results_dir", type=str, required=True,
                       help="Directory to save results")
    
    args = parser.parse_args()
    
    metrics, correct, err = main(args.program_path, args.results_dir)
    
    if correct:
        print(f"Evaluation successful! Combined score: {metrics['combined_score']:.2f}")
    else:
        print(f"Evaluation failed: {err}")
