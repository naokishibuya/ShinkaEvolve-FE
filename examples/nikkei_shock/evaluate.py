import argparse
import numpy as np
import os
import yaml
from pathlib import Path
from shinka.core import run_shinka_eval


def load_scenarios() -> list[dict]:
    """Load all scenarios from YAML file.

    Returns:
        List of scenario dicts, each containing:
            - exposure: list of exposure instruments
            - hedge: list of hedge instruments
            - stats: market statistics dict
            - config: scenario config dict (includes name, description)
    """
    scenario_file = str(Path(__file__).parent / "scenarios.yaml")

    try:
        with open(scenario_file) as f:
            yaml_data = yaml.safe_load(f)

        # Load common stats and config
        stats = yaml_data['stats']
        config = yaml_data['config']

        max_sigma_ratio = config['max_sigma_ratio']
        max_horizon_days = config['max_horizon_days']
        lambda_penalty = config['lambda_penalty']

        # Parse stats from common section (reused across all scenarios)
        stats = {
            'eq_vol': stats['eq_vol'],
            'vol_of_vol': stats['vol_of_vol'],
            'fx_vol': stats['fx_vol'],
            'ir_vol': stats['ir_vol'],
            'corr_normal': np.array(stats['corr_normal']),
            'corr_crisis': np.array(stats['corr_crisis']),
        }

        # Load all scenarios
        scenarios = []
        for scenario in yaml_data['scenarios']:
            # Parse portfolios as list of dicts (with defaults for omitted fields)
            scenarios.append({
                'scenario_name': scenario['name'],
                'description': scenario['description'],
                'exposure': check_instruments(scenario['exposure']),
                'hedge': check_instruments(scenario['hedge']),
                'stats': stats,
                'max_sigma_ratio': max_sigma_ratio,
                'max_horizon_days': max_horizon_days,
                'lambda_penalty': lambda_penalty,
            })
        return scenarios

    except Exception as e:
        raise Exception(f"Error loading scenarios.yaml: {e}") from e


def check_instruments(instruments: dict) -> list[dict]:
    """Build portfolio from YAML data as list of instrument dicts."""
    required_keys = ['name', 'mtm_value', 'eq_linear', 'eq_quad', 'vol_linear', 'fx_linear', 'ir_dv01']
    for inst in instruments:
        for key in inst:
            if key not in required_keys:
                raise ValueError(f"Invalid instrument field: {key}")
        inst['name']      = inst['name']
        inst['mtm_value'] = inst['mtm_value']
        inst['eq_linear']  = inst.get('eq_linear', 0.0)
        inst['eq_quad']  = inst.get('eq_quad', 0.0)
        inst['vol_linear']   = inst.get('vol_linear' , 0.0)
        inst['fx_linear']  = inst.get('fx_linear', 0.0)
        inst['ir_dv01']   = inst.get('ir_dv01' , 0.0)
    return instruments


def aggregate_results(metrics_list: list[dict]) -> dict:
    """Aggregate results from multiple scenario runs."""
    avg_fitness = np.mean([m['fitness'] for m in metrics_list])

    # Generate textual feedback for each scenario
    feedback_parts = []
    for i, metrics in enumerate(metrics_list):
        scenario_feedback = format_scenario_feedback(i + 1, metrics, len(metrics_list))
        feedback_parts.append(scenario_feedback)
    feedback = "\n".join(feedback_parts)

    return {
        # Primary fitness (what ShinkaEvolve maximizes)
        'combined_score': avg_fitness,

        # Public metrics (visible to LLM for generating mutations)
        'public': {
            'avg_fitness': avg_fitness,
            'num_scenarios': len(metrics_list),
        },

        # Private metrics (not shown to LLM, for your analysis)
        'private': {
            'all_metrics': metrics_list,
        },

        # Text feedback (shown to LLM to guide evolution)
        'text_feedback': feedback,
    }


def format_scenario_feedback(run_num: int, metrics: dict, total_runs: int) -> str:
    """Generate detailed feedback for a single scenario."""
    # Header
    if total_runs == 1:
        feedback = f"SCENARIO: {metrics['scenario_name']}\n"
        if metrics['scenario_description']:
            feedback += f"{metrics['scenario_description']}\n"
        feedback += "\n"
    else:
        feedback = f"═══ SCENARIO {run_num}/{total_runs}: {metrics['scenario_name']} ═══\n"

    # Parameters
    feedback += "YOUR PARAMETERS:\n"
    feedback += (
        f"  eq={metrics['eq_sigmas']:.1f}σ, "
        f"vol={metrics['vol_sigmas']:.1f}σ, "
        f"fx={metrics['fx_sigmas']:.1f}σ, "
        f"ir={metrics['ir_sigmas']:.1f}σ\n"
    )
    feedback += (
        f"  Horizon: {metrics['horizon_days']} days, "
        f"Crisis: {metrics['crisis_intensity']:.1f}\n\n"
    )

    # P&L summary
    exp_pnl = metrics['exposure_pnl']
    hedge_pnl = metrics['hedge_pnl']
    combined_pnl = exp_pnl + hedge_pnl

    baseline_loss = -exp_pnl          # loss without hedge
    hedged_loss   = -combined_pnl     # loss with hedge

    feedback += "RESULT SUMMARY:\n"
    feedback += f"  Exposure P&L (no hedge): ¥{exp_pnl:,.0f}\n"
    feedback += f"  Hedge P&L:               ¥{hedge_pnl:,.0f}\n"
    feedback += f"  Combined P&L:            ¥{combined_pnl:,.0f}\n"
    feedback += f"  Fitness: {metrics['fitness']:.4f}\n\n"

    # Interpretation (qualitative, no 'effectiveness' metric)
    feedback += "INTERPRETATION:\n"

    # Thresholds just to avoid noise from tiny numbers
    loss_threshold = 1e6   # ¥1M
    big_loss_threshold = 1e8  # ¥100M

    if abs(combined_pnl) < loss_threshold:
        feedback += "  • Overall outcome is close to breakeven.\n"
    elif combined_pnl < -loss_threshold:
        if abs(combined_pnl) > big_loss_threshold:
            feedback += "  • This is a LARGE loss scenario.\n"
        else:
            feedback += "  • This is a loss scenario.\n"
    else:
        feedback += "  • This is a profit scenario for the combined portfolio.\n"

    if abs(baseline_loss) > loss_threshold:
        # Compare loss with and without hedge
        if hedged_loss > baseline_loss * 1.1:
            feedback += "  • Loss WITH hedge is noticeably larger than loss on exposure alone (hedge amplified the move).\n"
            hedge_mode = "amplifying"
        elif hedged_loss < baseline_loss * 0.9:
            feedback += "  • Loss WITH hedge is clearly smaller than loss on exposure alone (hedge cushioned the move).\n"
            hedge_mode = "cushioning"
        else:
            feedback += "  • Hedge changed the outcome only modestly versus exposure alone.\n"
            hedge_mode = "neutral"
    else:
        hedge_mode = "undefined"
        feedback += "  • Exposure alone has small P&L; relative hedge impact is hard to interpret.\n"

    feedback += "\n"

    # Per-instrument breakdown (only show significant contributions)
    feedback += "HEDGE BREAKDOWN (significant contributions):\n"
    for name, pnl in metrics['hedge_instruments'].items():
        if abs(pnl) > 1e8:  # Only show if > ¥100M
            sign = "+" if pnl > 0 else ""
            feedback += f"  • {name}: {sign}¥{pnl:,.0f}\n"
    feedback += "\n"

    # Key drivers from parameters
    feedback += "KEY DRIVERS BASED ON PARAMETERS:\n"
    drivers = []

    if metrics['vol_sigmas'] > 2:
        drivers.append(f"  • Large vol spike (+{metrics['vol_sigmas']:.1f}σ)")
    if metrics['vol_sigmas'] < -2:
        drivers.append(f"  • Vol crush ({metrics['vol_sigmas']:.1f}σ)")

    if metrics['fx_sigmas'] > 2:
        drivers.append(f"  • Strong JPY weakness (+{metrics['fx_sigmas']:.1f}σ)")
    if metrics['fx_sigmas'] < -2:
        drivers.append(f"  • Strong JPY strength ({metrics['fx_sigmas']:.1f}σ)")

    if metrics['ir_sigmas'] > 2:
        drivers.append(f"  • Yield spike (+{metrics['ir_sigmas']:.1f}σ)")
    if metrics['ir_sigmas'] < -2:
        drivers.append(f"  • Yield drop ({metrics['ir_sigmas']:.1f}σ)")

    if metrics['horizon_days'] > 7:
        drivers.append(f"  • Long horizon ({metrics['horizon_days']} days) → carry / theta effects matter")
    elif metrics['horizon_days'] <= 2:
        drivers.append(f"  • Very short horizon ({metrics['horizon_days']} days) → shock / gap risk dominates")

    if metrics['crisis_intensity'] > 0.6:
        drivers.append(f"  • High crisis mode ({metrics['crisis_intensity']:.1f}) → correlations close to crisis regime")

    if drivers:
        feedback += "\n".join(drivers) + "\n\n"
    else:
        feedback += "  • No particularly extreme parameter – scenario is relatively moderate.\n\n"

    # Suggestions: what to try next
    feedback += "IDEAS TO IMPROVE OR REFINE THIS SCENARIO:\n"
    suggestions = []

    # 1) If hedge is cushioning, suggest exploring ways to weaken/counter it
    if hedge_mode == "cushioning":
        suggestions.append("  • If your goal is to find failure modes, explore shocks that push hedge P&L in the SAME direction as exposure P&L.")
    elif hedge_mode == "amplifying":
        suggestions.append("  • This is already an interesting stress where hedge amplifies the move – try small tweaks to test robustness (±0.5σ on key factors).")
    elif hedge_mode == "neutral":
        suggestions.append("  • Hedge impact is modest – consider combining multiple shocks (vol + FX + rates) to create clearer outcomes.")

    # 2) Factor-specific ideas based on hedge instruments
    total_option_pnl = sum(
        pnl for name, pnl in metrics['hedge_instruments'].items()
        if 'Put' in name or 'Option' in name
    )
    if abs(total_option_pnl) > 1e9:
        if metrics['vol_sigmas'] > 0:
            suggestions.append("  • Options are active: try a vol crush (vol_sigmas ≈ -3.0) to emphasize theta / vega decay.")
        else:
            suggestions.append("  • Options are active: try a vol spike (vol_sigmas ≈ +3.0) to stress convexity.")

    if any('FX' in name or 'USDJPY' in name for name in metrics['hedge_instruments']):
        suggestions.append("  • FX hedge present: explore fx_sigmas ≈ ±3.0 to see JPY strength/weakness impacts.")

    if any('JGB' in name or 'Bond' in name for name in metrics['hedge_instruments']):
        suggestions.append("  • Rate hedge present: explore ir_sigmas ≈ ±3.0 for large yield moves.")

    # 3) Time dimension
    if metrics['horizon_days'] < 7:
        suggestions.append("  • Increase horizon_days (e.g. 10–15) if you want more carry/theta-driven effects.")
    else:
        suggestions.append("  • Shorten horizon_days (e.g. 2–3) if you want a purer shock scenario.")

    # 4) Magnitude vs plausibility trade-off
    if metrics['plausibility_penalty'] > 0.5:
        suggestions.append("  • Plausibility penalty is high – consider reducing sigma magnitudes while keeping the same qualitative direction of shocks.")
    else:
        if combined_pnl > -loss_threshold:  # not much damage
            suggestions.append("  • Scenario is quite plausible but not very damaging – try nudging sigmas further in the same direction to increase impact.")

    if suggestions:
        feedback += "\n".join(suggestions[:4]) + "\n\n"
    else:
        feedback += "  • Try varying one factor at a time (vol / FX / rates / horizon) to map out the sensitivity.\n\n"

    # Plausibility warning
    if metrics['plausibility_penalty'] > 0.5:
        feedback += f"⚠️ PLAUSIBILITY: Penalty = {metrics['plausibility_penalty']:.2f}\n"
        feedback += "  Scenario may be too extreme – reduce sigma magnitudes or crisis_intensity.\n\n"

    return feedback


def main(program_path: str, results_dir: str) -> tuple[dict, bool, str]:
    print(f"Evaluating program: {program_path}")
    print(f"Saving results to: {results_dir}")
    os.makedirs(results_dir, exist_ok=True)

    # Load all scenarios from YAML
    scenarios = load_scenarios()
    num_runs = len(scenarios)

    def get_scenario_kwargs(run_idx: int) -> dict:
        return scenarios[run_idx]

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
        print(f"\nText feedback:")
        print(metrics['text_feedback'])
    else:
        print(f"Evaluation failed: {err}")
