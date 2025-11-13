import argparse
import math
import numpy as np
from dataclasses import dataclass
from initial import ScenarioParameters, HistoricalStats, propose_scenario
from portfolio import Portfolio, FactorShock
from shinka.core import run_shinka_eval


@dataclass
class ScenarioResult:
    params: ScenarioParameters
    shock: FactorShock
    base_pnl: float
    hedge_pnl: float
    plaus_penalty: float

    @property
    def base_loss(self) -> float:
        return -self.base_pnl

    @property
    def hedge_loss(self) -> float:
        return -self.hedge_pnl

    @property
    def hedge_effectiveness(self) -> float:
        """How much loss was reduced by hedging (positive = good)."""
        return self.base_loss - self.hedge_loss


def evaluate_scenario(
    params: ScenarioParameters,
    stats: HistoricalStats,
    base_portfolio: Portfolio,
    hedged_portfolio: Portfolio,
    lam: float = 1e9,
) -> tuple[float, ScenarioResult]:
    """
    Returns:
        fitness (float)
        result (ScenarioResult)
    """
    shock = generate_factor_shock(params, stats)
    base_pnl = base_portfolio.pnl(shock)
    hedge_pnl = hedged_portfolio.pnl(shock)

    penalty = sigma_penalty(params)

    result = ScenarioResult(
        params=params,
        shock=shock,
        base_pnl=base_pnl,
        hedge_pnl=hedge_pnl,
        plaus_penalty=penalty,
    )

    # For scenario discovery, we might want:
    #   - big loss on hedged portfolio (interesting scenario)
    #   - but penalize implausibility
    fitness = result.hedge_loss - lam * penalty

    return fitness, result


def generate_factor_shock(params: ScenarioParameters, stats: HistoricalStats) -> FactorShock:
    """
    Map sigmas → actual moves, scaled by sqrt(horizon).
    For now we ignore correlation in generation (use it only for plausibility later).
    """
    T = max(1, params.horizon_days)
    sqrtT = math.sqrt(T)

    eq_ret = params.eq_sigmas * stats.eq_vol * sqrtT
    vol_change = params.vol_sigmas * stats.vol_of_vol * sqrtT
    fx_ret = params.fx_sigmas * stats.fx_vol * sqrtT
    ir_change = params.ir_sigmas * stats.ir_vol * sqrtT

    return FactorShock(
        eq_ret=eq_ret,
        vol_change=vol_change,
        fx_ret=fx_ret,
        ir_change=ir_change,
    )


def sigma_penalty(params: ScenarioParameters, per_factor_cap=8.0, joint_cap=10.0) -> float:
    sigs = np.array([params.eq_sigmas, params.vol_sigmas,
                     params.fx_sigmas, params.ir_sigmas])

    # per-factor penalty if |sigma| exceeds cap
    per_factor_excess = np.maximum(np.abs(sigs) - per_factor_cap, 0.0)
    per_factor_pen = float(np.sum(per_factor_excess ** 2))

    # joint extremeness penalty (norm beyond joint_cap)
    dist = float(np.linalg.norm(sigs))
    joint_excess = max(0.0, dist - joint_cap)
    joint_pen = joint_excess ** 2

    return per_factor_pen + joint_pen


def main(program_path: str, results_dir: str) -> tuple[dict, bool, str]:
    """
    Main evaluation function called by ShinkaEvolve.

    Args:
        program_path: Path to the program being evaluated (initial.py or evolved variant)
        results_dir: Directory to save results

    Returns:
        (metrics, correct, err) tuple
    """
    metrics, correct, err = run_shinka_eval(
        program_path=program_path,
        results_dir=results_dir,
        experiment_fn_name="run_experiment",
        num_runs=3,  # Test on 3 different configurations
        get_experiment_kwargs=get_scenario_kwargs,
        validate_fn=validate_solution,
        aggregate_metrics_fn=aggregate_results,
    )

    return metrics, correct, err


def get_scenario_kwargs(run_idx: int) -> dict:
    """
    Return kwargs for each evaluation run.
    Each run uses a different test scenario.
    """
    # Dummy stats
    stats = HistoricalStats(
        eq_vol=0.012,        # 1.2% daily
        vol_of_vol=0.02,     # 2 vol pts per day
        fx_vol=0.006,        # 0.6% daily
        ir_vol=0.0005,       # 5bp per day
        corr_normal=np.eye(4),
        corr_crisis=np.eye(4),
    )

    return {
        'stats': stats,
    }


def validate_solution(result: tuple[dict, str]) -> tuple[bool, str]:
    """
    Validate that a scenario result is reasonable.

    Args:
        result: (metrics_dict, feedback_text) tuple

    Returns:
        (is_valid, error_message) tuple
    """
    metrics, feedback = result

    # Check if we got valid metrics
    if metrics is None:
        return False, "Evaluation returned None"

    # Check for required fields
    required_fields = ['fitness', 'hedge_loss', 'base_loss', 'plausibility_penalty']
    for field in required_fields:
        if field not in metrics:
            return False, f"Missing required field: {field}"

    # Check for NaN or infinite values
    for field in required_fields:
        value = metrics[field]
        if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
            return False, f"Invalid value for {field}: {value}"

    # Check plausibility - scenarios should have low penalty
    penalty = metrics['plausibility_penalty']
    if penalty > 100.0:  # Very high penalty means implausible
        return False, f"Scenario too implausible: penalty={penalty:.2f}"

    # All checks passed
    return True, None


def aggregate_results(results: list[tuple[dict, str]]) -> dict:
    """
    Aggregate results from multiple scenario runs.

    Args:
        results: List of (metrics_dict, feedback_text) tuples from each run

    Returns:
        Aggregated metrics dictionary with structure:
        - combined_score: float (primary fitness for evolution)
        - public: dict (metrics visible to LLM)
        - private: dict (metrics for analysis only)
        - extra_data: dict (additional data saved)
        - text_feedback: str (feedback shown to LLM)
    """
    metrics_list = [r[0] for r in results]
    feedback_list = [r[1] for r in results]

    # Calculate aggregate statistics
    avg_fitness = sum(m['fitness'] for m in metrics_list) / len(metrics_list)
    avg_hedge_loss = sum(m['hedge_loss'] for m in metrics_list) / len(metrics_list)
    avg_base_loss = sum(m['base_loss'] for m in metrics_list) / len(metrics_list)
    avg_hedge_effectiveness = sum(m['hedge_effectiveness'] for m in metrics_list) / len(metrics_list)
    avg_penalty = sum(m['plausibility_penalty'] for m in metrics_list) / len(metrics_list)

    # Calculate robustness (consistency across runs)
    fitness_values = [m['fitness'] for m in metrics_list]
    fitness_std = float(np.std(fitness_values))

    # Find best and worst runs
    best_idx = max(range(len(metrics_list)), key=lambda i: metrics_list[i]['fitness'])
    worst_idx = min(range(len(metrics_list)), key=lambda i: metrics_list[i]['fitness'])

    # Combined score (what evolution optimizes)
    # Prioritize high fitness, but penalize high variance
    combined_score = avg_fitness - 0.1 * fitness_std

    aggregated = {
        # Primary fitness (what ShinkaEvolve maximizes)
        'combined_score': float(combined_score),

        # Public metrics (visible to LLM for generating mutations)
        'public': {
            'avg_fitness': float(avg_fitness),
            'avg_hedge_loss': float(avg_hedge_loss),
            'avg_base_loss': float(avg_base_loss),
            'avg_hedge_effectiveness': float(avg_hedge_effectiveness),
            'avg_plausibility_penalty': float(avg_penalty),
            'fitness_std': float(fitness_std),
            'best_run': int(best_idx + 1),
            'worst_run': int(worst_idx + 1),
        },

        # Private metrics (not shown to LLM, for your analysis)
        'private': {
            'all_metrics': metrics_list,
            'individual_fitness': fitness_values,
        },

        # Extra data (saved as pickle)
        'extra_data': {
            'feedbacks': feedback_list,
            'detailed_results': results,
        },

        # Text feedback (shown to LLM to guide evolution)
        'text_feedback': format_feedback_for_llm(
            metrics_list,
            best_idx,
            worst_idx,
            avg_hedge_effectiveness,
            avg_penalty,
        ),
    }

    return aggregated


def format_feedback_for_llm(
    metrics_list: list[dict],
    best_idx: int,
    worst_idx: int,
    avg_hedge_effectiveness: float,
    avg_penalty: float,
) -> str:
    """
    Format feedback text that LLM will see.
    This guides the LLM on how to improve the scenario.
    """
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
