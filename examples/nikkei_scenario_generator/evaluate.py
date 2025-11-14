import argparse
import numpy as np
import os
from shinka.core import run_shinka_eval


def aggregate_results(metrics_list: list[dict]) -> dict:
    """Aggregate results from multiple scenario runs."""
    fitnesses = []
    hedge_losses = []
    base_losses = []
    hedge_effectivenesses = []
    plausibility_penalties = []
    for metrics in metrics_list:
        fitnesses.append(metrics['fitness'])
        hedge_losses.append(metrics['hedge_loss'])
        base_losses.append(metrics['base_loss'])
        hedge_effectivenesses.append(metrics['hedge_effectiveness'])
        plausibility_penalties.append(metrics['plausibility_penalty'])

    # Average metrics
    avg_fitness = np.mean(fitnesses)
    std_fitness = np.std(fitnesses)
    avg_hedge_loss = np.mean(hedge_losses)
    avg_base_loss = np.mean(base_losses)
    avg_hedge_effectiveness = np.mean(hedge_effectivenesses)
    avg_penalty = np.mean(plausibility_penalties)

    # Find best and worst runs
    best_idx = np.argmax(fitnesses)
    worst_idx = np.argmin(fitnesses)

    # Combined score (what evolution optimizes)
    # Prioritize high fitness, but penalize high variance
    penalty_factor = 0.1  # TODO tune this
    combined_score = avg_fitness - penalty_factor * std_fitness

    # Generate textual feedback for LLM
    def format_feedback_for_llm():
        feedback = "SCENARIO DISCOVERY PERFORMANCE:\n\n"

        for i, metrics in enumerate(metrics_list):
            marker = "✓" if i == best_idx else ("✗" if i == worst_idx else " ")
            feedback += f"{marker} Run {i+1}:\n"
            feedback += f"   Fitness: {metrics['fitness']:.2e}\n"
            feedback += f"   Hedge Loss: ¥{metrics['hedge_loss']:,.0f}\n"
            feedback += f"   Base Loss: ¥{metrics['base_loss']:,.0f}\n"
            feedback += f"   Hedge Effectiveness: ¥{metrics['hedge_effectiveness']:,.0f}\n"
            feedback += f"   Plausibility Penalty: {metrics['plausibility_penalty']:.4f}\n"
            feedback += f"   Scenario: eq={metrics['eq_sigmas']:.1f}σ, vol={metrics['vol_sigmas']:.1f}σ, "
            feedback += f"fx={metrics['fx_sigmas']:.1f}σ, ir={metrics['ir_sigmas']:.1f}σ\n\n"

        feedback += "ANALYSIS:\n"
        feedback += f"Best fitness: Run {best_idx + 1}\n"
        feedback += f"Worst fitness: Run {worst_idx + 1}\n\n"

        # Provide specific suggestions
        feedback += "SUGGESTIONS FOR IMPROVEMENT:\n"

        if avg_penalty > 1.0:
            feedback += "• Plausibility penalty is high - scenarios may be too extreme\n"
            feedback += "  Try: Reduce sigma magnitudes or ensure economic coherence\n"

        if avg_hedge_effectiveness > 0:
            feedback += "• Hedge is working TOO WELL - not stressful enough\n"
            feedback += "  Try: Find scenarios where hedge backfires or fails\n"
            feedback += "  Ideas: Vol crush, correlation breakdown, gamma/vega mismatches\n"

        if avg_penalty < 0.1 and avg_hedge_effectiveness > -1e9:
            feedback += "• Good plausibility but hedge still protecting adequately\n"
            feedback += "  Try: More asymmetric scenarios (slow grind vs fast crash)\n"
            feedback += "  Try: Vary horizon_days and crisis_intensity more\n"

        # Check for diversity
        eq_sigmas = [m['eq_sigmas'] for m in metrics_list]
        if max(eq_sigmas) - min(eq_sigmas) < 2.0:
            feedback += "• Low diversity in eq_sigmas - explore wider range\n"
        return feedback

    return {
        # Primary fitness (what ShinkaEvolve maximizes)
        'combined_score': combined_score,

        # Public metrics (visible to LLM for generating mutations)
        'public': {
            'avg_fitness': float(avg_fitness),
            'avg_hedge_loss': float(avg_hedge_loss),
            'avg_base_loss': float(avg_base_loss),
            'avg_hedge_effectiveness': float(avg_hedge_effectiveness),
            'avg_plausibility_penalty': float(avg_penalty),
            'std_fitness': float(std_fitness),
            'best_run': int(best_idx + 1),
            'worst_run': int(worst_idx + 1),
        },

        # Private metrics (not shown to LLM, for your analysis)
        'private': {
            'all_metrics': metrics_list,
            'individual_fitness': fitnesses,
        },

        # Extra data (saved as pickle)
        'extra_data': {
            'all_metrics': metrics_list,
        },

        # Text feedback (shown to LLM to guide evolution)
        'text_feedback': format_feedback_for_llm(),
    }


def main(program_path: str, results_dir: str) -> tuple[dict, bool, str]:
    print(f"Evaluating program: {program_path}")
    print(f"Saving results to: {results_dir}")
    os.makedirs(results_dir, exist_ok=True)

    num_runs = 1

    def get_scenario_kwargs(run_idx: int) -> dict:
        return {'run_id': run_idx}

    def validate_solution(metrics: dict) -> tuple[bool, str]:
        if metrics is None:
            return False, "No metrics returned"
        return True, None

    """Main evaluation function called by ShinkaEvolve."""
    metrics, correct, err = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_experiment",
        num_runs=num_runs,
        get_experiment_kwargs=get_scenario_kwargs,
        validate_fn=validate_solution,
        aggregate_metrics_fn=aggregate_results,
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
        print(f"\nPublic metrics:")
        for key, value in metrics['public'].items():
            print(f"  {key}: {value}")
    else:
        print(f"Evaluation failed: {err}")
