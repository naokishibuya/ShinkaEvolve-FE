import numpy as np
import re
from typing import Any
from utils import calculate_factor_moves, calculate_portfolio_pnl
from shinka.llm import LLMClient


SYSTEM_MSG = """
You are an expert risk manager. Your task is to evaluate how well an analysis identifies:

1) the portfolio's true exposures,
2) what each hedge instrument is intended to insure,
3) structural weaknesses or residual risks,
4) and whether the reasoning is consistent with the scenario data.
Be VERY strict: shallow or incomplete analyses must receive low scores.

FIELD INTERPRETATION GUIDE (IMPORTANT):
- Each scenario lists exposure and hedge instruments.
- mtm_value: current mark-to-market in JPY (positive = long, negative = short).
- eq_lin: equity delta-like sensitivity per 1σ equity move, scaled by mtm_value.
- eq_quad: equity convexity (gamma-like) per (1σ equity move)^2, scaled by mtm_value.
- vol_linear: volatility sensitivity (vega-like) per 1σ vol move, scaled by mtm_value.
- fx_linear: FX sensitivity per 1σ move in FX (e.g. USDJPY), scaled by mtm_value.
- ir_dv01: interest-rate DV01 in JPY (P&L per 1bp parallel rate move).
- stats.eq_vol / fx_vol / ir_vol / vol_of_vol: daily 1σ vols.
- corr_normal / corr_crisis: 4x4 corr matrices in [equity, vol, fx, ir] order.
- config: max_sigma_ratio (shock size in σ), max_horizon_days (shock horizon in days).

=== SCORING RUBRIC ===
Score quality_score of the analysis of the given scenario between 0 and 1 (1 = perfect, 0 = useless)
based on how well the analysis addresses the following criteria:

1) Correctly identifies the portfolio's main exposures and risks.
2) Accurately explains what each hedge instrument is intended to cover.
3) Identifies any structural weaknesses or residual risks in the hedge.
4) Provides reasoning that is consistent with the scenario data (sensitivities, vols, correlations).
5) Demonstrates depth of understanding and insight into risk management.
6) Uses correct figures and financial terminology.
7) Is clear, concise, and well-organized.
8) Avoids vague generalities and unsupported claims.
9) Shows evidence of critical thinking and analysis.
10) Deep understanding of how shocks propagate through correlated risk factors.
11) Considers the plausibility of shocks given the provided stats and config.
12) Provides specific examples from the scenario to support points made.
13) Deep insight into hedge effectiveness and potential failure modes.

Respond ONLY as:
quality_score: <float>
<1–3 sentence justification and advice for improvement>
"""


USER_MSG = """
=== SCENARIO ===
{}

=== ANALYSIS ===
{}

=== WORST-CASE SHOCK PARAMS ===
{}

=== DERIVED CORRELATED FACTOR MOVES (from risk model) ===
These are the actual factor moves implied by the AI's sigma choices,
after applying correlations, crisis_intensity, and horizon scaling.
{}

=== PORTFOLIO P&L UNDER THESE MOVES (JPY) ===
{}
"""


# Compile regex once and reuse
SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)


def _extract_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


SUMMARY_SYSTEM_MSG = """
Summarize the AI's performance across {} hedge analysis scenarios.

YOUR TASK: Write a concise summary (150-200 words) following this EXACT format:

OVERALL PERFORMANCE: [score + quality level]

STRENGTHS ACROSS SCENARIOS:
  • [common strength 1]
  • [common strength 2]
  • [common strength 3]

COMMON GAPS:
  • [recurring gap 1]
  • [recurring gap 2]
  • [recurring gap 3]

NEXT GENERATION FOCUS:
  1. [specific actionable improvement 1]
  2. [specific actionable improvement 2]
  3. [specific actionable improvement 3]

EXAMPLE:
────────
OVERALL PERFORMANCE: 0.93/1.0 (Excellent - Minor gaps remain)

STRENGTHS ACROSS SCENARIOS:
  • Correctly identified all major exposures (delta, gamma, vega, FX, IR)
  • Strong quantification of residual risks with specific figures
  • Good understanding of correlation regime shifts

COMMON GAPS:
  • Basis risk rarely discussed (FX hedges, JGB overlay)
  • Practical hedge limitations not mentioned (cost, liquidity, model risk)
  • Zero MTM positions need clarification (e.g., JGB futures)

NEXT GENERATION FOCUS:
  1. Add basis risk discussion for FX/IR hedges
  2. Mention cost/benefit analysis for expensive hedges (OTM puts)
  3. Explicitly address scenario-specific vulnerabilities from descriptions
────────
"""

SUMMARY_USER_MSG = """
INDIVIDUAL SCENARIO FEEDBACKS:
{}

Average Score: {:.2f}/1.0

Write your summary now, following the exact format instructed."""


def generate_feedback(
    scenarios: list[dict],
    stats: dict[str, Any],
    config: dict[str, Any],
    responses: list[str],
    llm_judge: LLMClient,
) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs."""

    # Iterate through scenarios and analyses to get individual feedback
    analysis_list = []
    shock_params_list = []
    factor_moves_list = []
    scenario_texts = []
    judge_inputs = []
    judge_scores = []
    judge_texts = []
    for i in range(len(scenarios)):
        scenario = scenarios[i]
        response = responses[i]
        exposure = scenario["exposure"]
        hedge = scenario["hedge"]
        analysis = response["analysis"]
        shock_params = response["shock_params"]

        scenario_text = _format_scenario_for_judge(scenario, stats, config)
        factor_moves = calculate_factor_moves(shock_params, stats)
        pnl_summary = calculate_portfolio_pnl(exposure, hedge, factor_moves)

        judge_input, score, judge_text = _evaluate_single_scenario(
            scenario_text,
            analysis,
            shock_params,
            factor_moves,
            pnl_summary,
            llm_judge)

        analysis_list.append(analysis)
        shock_params_list.append(shock_params)
        factor_moves_list.append(factor_moves)
        scenario_texts.append(scenario_text)
        judge_inputs.append(judge_input)
        judge_scores.append(score)
        judge_texts.append(judge_text)

    combined_score = float(np.mean(judge_scores))

    scenarios = _to_json_safe(scenarios)
    stats = _to_json_safe(stats)
    config = _to_json_safe(config)
    shock_params_list = _to_json_safe(shock_params_list)
    factor_moves_list = _to_json_safe(factor_moves_list)

    public_feedback = {
        "avg_score": combined_score,
        "num_scenarios": len(scenarios),
        "scenarios": [
            {
                "name": scenario["name"],
                "score": judge_scores[i],
                "feedback": judge_texts[i],
                "analysis": analysis_list[i],
                "shock_params": shock_params_list[i],
            }
            for i, scenario in enumerate(scenarios)
        ],
        "stats": stats,
        "config": config,
    }

    private_feedback = {
        "judges": [
            {
                "input": judge_inputs[i].splitlines(),
                "score": judge_scores[i],
                "text": judge_texts[i].splitlines(),
                "scenario": scenario_texts[i].splitlines(),
                "analysis": analysis_list[i].splitlines(),
                "shock_params": shock_params_list[i],
                "derived_moves": factor_moves_list[i],
            }
            for i in range(len(judge_scores))
        ]
    }

    text_feedback = _summarize_feedbacks(scenarios, combined_score, judge_texts, llm_judge)

    return {
        "combined_score": combined_score,
        "public": public_feedback,
        "private": private_feedback,
        "text_feedback": text_feedback,
    }


def _evaluate_single_scenario(
    scenario_text: str,
    analysis: str,
    shock_params: dict[str, Any],
    derived_moves: dict[str, Any],
    pnl_summary: dict[str, Any],
    llm_judge: LLMClient,
) -> float:
    shock_block = _format_shock_block(shock_params)
    pnl_block = _format_pnl_block(pnl_summary)
    user_msg = USER_MSG.format(
        scenario_text,
        analysis,
        shock_block,
        derived_moves,
        pnl_block)
    response = llm_judge.query(
        msg=user_msg,
        system_msg=SYSTEM_MSG,
        llm_kwargs=llm_judge.get_kwargs())
    score = _extract_score(response.content)
    return user_msg, score, response.content


def _format_shock_block(
    shock_params: dict[str, Any],
) -> str:
    """Format the WORST_CASE_SHOCK block with proper structure."""
    rationale = shock_params.get("rationale", {})
    def get_rationale_value(key: str) -> str:
        if key not in rationale:
            return "N/A"
        value = rationale[key]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return "N/A"
        return value

    shock_block = f"""
Worst-Case Shock Scenario:
  • eq_shock_sigma:    {shock_params["eq_shock_sigma"]:.1f}
  • vol_shock_sigma:   {shock_params["vol_shock_sigma"]:.1f}
  • fx_shock_sigma:    {shock_params["fx_shock_sigma"]:.1f}
  • ir_shock_sigma:    {shock_params["ir_shock_sigma"]:.1f}
  • horizon_days:      {shock_params["horizon_days"]}
  • crisis_intensity:  {shock_params["crisis_intensity"]:.2f}

Worst-Case Shock Rationale:
  • Equity: {get_rationale_value('equity')}
  • Volatility: {get_rationale_value('volatility')}
  • FX: {get_rationale_value('fx')}
  • Rates: {get_rationale_value('rates')}
  • Correlation regime: {get_rationale_value('correlation')}
"""
    return shock_block.strip()


def _format_scenario_for_judge(scenario: dict[str, Any], stats: dict[str, Any], config: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append(f"Name: {scenario['name']}")
    lines.append(f"Description: {scenario['description']}")
    lines.append("")

    lines.append("Exposure instruments (portfolio you want to hedge):")
    for inst in scenario["exposure"]:
        lines.append(
            f"  - {inst['name']}: mtm={inst['mtm_value']:.0f} JPY, "
            f"eq_lin={inst['eq_linear']} (equity delta), "
            f"eq_quad={inst['eq_quad']} (equity convexity), "
            f"vol_lin={inst['vol_linear']} (vol sensitivity), "
            f"fx_lin={inst['fx_linear']} (FX sensitivity), "
            f"ir_dv01={inst['ir_dv01']} (rate DV01, JPY per 1bp move)"

        )
    lines.append("")

    lines.append("Hedge instruments (overlay intended to reduce risk):")
    for inst in scenario["hedge"]:
        lines.append(
            f"  - {inst['name']}: mtm={inst['mtm_value']:.0f} JPY, "
            f"eq_lin={inst['eq_linear']} (equity delta), "
            f"eq_quad={inst['eq_quad']} (equity convexity), "
            f"vol_lin={inst['vol_linear']} (vol sensitivity), "
            f"fx_lin={inst['fx_linear']} (FX sensitivity), "
            f"ir_dv01={inst['ir_dv01']} (rate DV01)"
        )
    lines.append("")

    lines.append("Stats (daily 1σ vols and correlations):")
    lines.append(
        f"  eq_vol={stats['eq_vol']}, vol_of_vol={stats['vol_of_vol']}, "
        f"fx_vol={stats['fx_vol']}, ir_vol={stats['ir_vol']}"
    )
    lines.append("  corr_normal (eq, vol, fx, ir):")
    for row in stats["corr_normal"]:
        lines.append(f"    {row}")
    lines.append("  corr_crisis (eq, vol, fx, ir):")
    for row in stats["corr_crisis"]:
        lines.append(f"    {row}")
    lines.append("")

    lines.append("Config (shock bounds and penalties):")
    lines.append(
        f"  max_sigma_ratio={config['max_sigma_ratio']}, "
        f"max_horizon_days={config['max_horizon_days']}"
    )

    return "\n".join(lines)


def _format_pnl_block(pnl: dict[str, Any]) -> str:
    net = pnl["net_totals"]
    exp = pnl["exposure_totals"]
    hed = pnl["hedge_totals"]

    lines = []
    lines.append("Net P&L totals:")
    lines.append(f"  total : {net['total']:,.0f}")
    lines.append(f"  equity: {net['equity']:,.0f}")
    lines.append(f"  vol   : {net['vol']:,.0f}")
    lines.append(f"  fx    : {net['fx']:,.0f}")
    lines.append(f"  rates : {net['rates']:,.0f}")
    lines.append("")
    lines.append("Exposure vs. Hedge P&L (totals):")
    lines.append(f"  exposure_total: {exp['total']:,.0f}")
    lines.append(f"  hedge_total   : {hed['total']:,.0f}")
    return "\n".join(lines)


def _summarize_feedbacks(
    scenarios: list[dict],
    combined_score: float,
    judge_texts: list[str],
    llm_judge: LLMClient,
) -> str:
    # Generate overall summary feedback
    feedbacks_text = "\n\n".join([
        f"=== {scenarios[i]['name']} ===\n{judge_text}"
        for i, judge_text in enumerate(judge_texts)
    ])

    system_msg = SUMMARY_SYSTEM_MSG.format(len(scenarios))
    msg = SUMMARY_USER_MSG.format(feedbacks_text, combined_score)
    response = llm_judge.query(msg=msg, system_msg=system_msg, llm_kwargs=llm_judge.get_kwargs())
    return response.content


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert numpy types to plain Python types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_to_json_safe(v) for v in obj)
    return obj
