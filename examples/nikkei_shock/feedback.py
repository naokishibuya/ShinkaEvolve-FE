import numpy as np
import re
from dataclasses import is_dataclass, asdict
from typing import Any
from scenario import Scenario, RiskStats, ShockParams, ScenarioResponse
from quant_utils import FactorMoves, PnLBreakdown, ScenarioMetrics, evaluate_scenario_metrics
from shinka.llm import LLMClient


SYSTEM_MSG = """
You are an expert risk manager. Your task is to evaluate how well an analysis identifies:

1) the portfolio's true exposures,
2) what each hedge instrument is intended to insure,
3) structural weaknesses or residual risks,
4) potential hedge failure modes under stress,
5) and whether the reasoning is consistent with the scenario data.

Be VERY strict: shallow or incomplete analyses must receive low scores.

FIELD INTERPRETATION GUIDE (IMPORTANT):
- Each scenario lists exposure and hedge instruments.
- mtm_value: current mark-to-market in JPY (positive = long, negative = short).
- eq_lin: equity delta-like sensitivity per 1σ equity move, scaled by mtm_value.
- eq_quad: equity convexity (gamma-like) per (1σ move)^2, scaled by mtm_value.
- vol_linear: volatility sensitivity (vega-like) per 1σ vol move, scaled by mtm_value.
- fx_linear: FX sensitivity per 1σ move in FX (e.g. USDJPY), scaled by mtm_value.
- ir_dv01: interest-rate DV01 in JPY (P&L per 1bp parallel rate move).
- stats.eq_vol / fx_vol / ir_vol / vol_of_vol: daily 1σ vols.
- corr_crisis: 4x4 crisis-regime correlation matrix in [equity, vol, fx, ir] order.
- horizon_days: fixed crisis horizon used for √T scaling.

=== SCORING RUBRIC ===
Score quality_score of the analysis BETWEEN 0 AND 1 (1 = perfect, 0 = useless),
based on how well the analysis addresses the following criteria:

1) Correctly identifies the portfolio’s main exposures and risks.
2) Accurately explains what each hedge instrument is intended to cover.
3) Identifies structural weaknesses or residual risks.
4) Identifies potential hedge failure modes under realistic stress scenarios.
5) Reasoning is consistent with the data provided (sensitivities, vols, correlations).
6) Demonstrates depth of understanding and insight into risk management.
7) Uses correct figures and financial terminology.
8) Clear, concise, and well-organized writing.
9) Avoids vague generalities and unsupported claims.
10) Shows evidence of critical thinking (not template or boilerplate).
11) Uses examples or references to specific scenario details to support arguments.
12) Provides insight into how cross-asset interactions amplify risks.

Respond ONLY in the following format:

quality_score: <float> [0.0, 1.0]
<1–3 sentences of feedback>
"""


# Compile regex once and reuse
SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)


def _extract_quality_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


USER_MSG = """
=== SCENARIO ===
{}

=== ANALYSIS ===
{}

=== WORST-CASE SHOCK PARAMS ===
{}

=== DERIVED FACTOR MOVES (from risk model) ===
These are the actual factor moves implied by the AI's sigma choices,
after applying vol scaling and horizon (√T). Correlations are only used
to evaluate a joint_sigma plausibility measure, not to mix directions.
{}

=== PORTFOLIO P&L UNDER THESE MOVES (JPY) ===
{}
"""


SUMMARY_SYSTEM_MSG = """
Summarize the AI's performance across {} hedge analysis scenarios.

You are writing meta-feedback for an AI that:
  • Writes qualitative risk analysis, and
  • Designs worst-case shock_params that are evaluated quantitatively

YOUR TASK: Write a concise summary (150–300 words) following this EXACT format:

OVERALL PERFORMANCE: [combined_score/1.0 + quality level]
# combined_score is the average of qualitative_score and quantitative_score.

STRENGTHS ACROSS SCENARIOS:
  • [common strength 1 – can be qualitative OR quantitative]
  • [common strength 2]
  • [common strength 3]

COMMON GAPS:
  • [recurring gap 1 – e.g., loss_ratio below threshold, joint_sigma too high,
      or shocks not aligned with net greeks]
  • [recurring gap 2 – e.g., missing basis-risk discussion, no use of P&L breakdown]
  • [recurring gap 3]

NEXT GENERATION FOCUS:
  1. [specific actionable improvement 1 – must reference concrete fields such as net delta/gamma/vega/FX/DV01]
  2. [specific actionable improvement 2 – how to improve shock design or analysis depth]
  3. [specific actionable improvement 3 – how to better connect narrative to P&L and factor_moves]

EXAMPLE:
────────
OVERALL PERFORMANCE: 0.93/1.0 (Excellent – Minor gaps remain)

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

Combined Score: {:.2f}/1.0
Average Quantitative Score: {:.2f}/1.0
Average Qualitative Score: {:.2f}/1.0

Write your summary now, following the exact format instructed."""


def generate_feedback(
    scenarios: list[Scenario],
    stats: RiskStats,
    responses: list[ScenarioResponse],
    llm_judge: LLMClient,
) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs (dataclass-native)."""

    user_msgs: list[str] = []
    metrics_list: list[Any] = []
    quant_feedbacks: list[str] = []
    judge_inputs: list[str] = []
    judge_scores: list[float] = []
    judge_texts: list[str] = []

    for i in range(len(scenarios)):
        scenario = scenarios[i]
        response = responses[i]

        analysis = response.analysis
        shock = response.shock_params

        metrics = evaluate_scenario_metrics(scenario, shock, stats)
        quant_feedback = _format_quantitative_feedback(metrics)

        scenario_text = _format_scenario_for_judge(scenario, stats)
        user_msg, score, judge_text = _evaluate_single_scenario(
            scenario_text,
            analysis,
            shock,  # now pass dataclass, not dict
            metrics.factor_moves,
            metrics.pnl_breakdown,
            llm_judge,
        )

        metrics_list.append(metrics)
        quant_feedbacks.append(quant_feedback)
        user_msgs.append(user_msg)
        judge_inputs.append(user_msg)
        judge_scores.append(score)
        judge_texts.append(judge_text)

    quantitative_score = float(np.mean([m.quantitative_score for m in metrics_list]))
    qualitative_score = float(np.mean(judge_scores))
    combined_score = 0.5 * quantitative_score + 0.5 * qualitative_score

    public_feedback = {}
    for i in range(len(scenarios)):
        public_feedback[f"scenario_{i+1}_qualitative_feedback"] = f"{judge_texts[i]}"
        public_feedback[f"scenario_{i+1}_quantative_feedback"] = f"{quant_feedbacks[i]}"

    private_feedback = {
        "scenarios": [  # ← Full details here
            {
                "name": scenarios[i].name,
                "analysis": responses[i].analysis,
                "shock_params": _to_json_safe(responses[i].shock_params),
                "metrics": _to_json_safe(metrics_list[i]),
            }
            for i in range(len(scenarios))
        ],
    }

    text_feedback = _summarize_feedbacks(
        scenarios,
        combined_score,
        quantitative_score,
        qualitative_score,
        quant_feedbacks,
        judge_texts,
        llm_judge,
    )

    return {
        "combined_score": combined_score,
        "public": public_feedback,
        "text_feedback": text_feedback,
        "private": private_feedback,
    }


def _evaluate_single_scenario(
    scenario_text: str,
    analysis: str,
    shock_params: ShockParams,
    factor_moves: FactorMoves,
    pnl_summary: PnLBreakdown,
    llm_judge: LLMClient,
) -> tuple[str, float, str]:
    shock_block = _format_shock_block(shock_params)
    moves_block = _format_factor_moves(factor_moves)
    pnl_block = _format_pnl_block(pnl_summary)

    user_msg = USER_MSG.format(
        scenario_text,
        analysis,
        shock_block,
        moves_block,
        pnl_block,
    )
    response = llm_judge.query(
        msg=user_msg,
        system_msg=SYSTEM_MSG,
        llm_kwargs=llm_judge.get_kwargs(),
    )
    score = _extract_quality_score(response.content)
    return user_msg, score, response.content


def _format_shock_block(shock_params: ShockParams) -> str:
    """Format the WORST_CASE_SHOCK block with proper structure (dataclass-based)."""
    rationale = shock_params.rationale

    def get_rationale_value(field: str) -> str:
        if rationale is None:
            return "N/A"
        value = getattr(rationale, field, None)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return "N/A"
        return value

    shock_block = f"""
Worst-Case Shock Scenario:
  • eq_shock_sigma:    {shock_params.eq_shock_sigma:.1f}
  • vol_shock_sigma:   {shock_params.vol_shock_sigma:.1f}
  • fx_shock_sigma:    {shock_params.fx_shock_sigma:.1f}
  • ir_shock_sigma:    {shock_params.ir_shock_sigma:.1f}

Worst-Case Shock Rationale:
  • Equity: {get_rationale_value('equity')}
  • Volatility: {get_rationale_value('volatility')}
  • FX: {get_rationale_value('fx')}
  • Rates: {get_rationale_value('rates')}
  • Correlation: {get_rationale_value('correlation')}
"""
    return shock_block.strip()


def _format_factor_moves(moves: FactorMoves) -> str:
    eq = moves.eq_move
    vol = moves.vol_move
    fx = moves.fx_move
    ir = moves.ir_move
    joint_sigma = moves.joint_sigma

    lines: list[str] = []
    lines.append(f"  eq_move : {eq:+.6f}  # equity move in decimal")
    lines.append(f"  vol_move: {vol:+.6f}  # vol-of-vol move in decimal")
    lines.append(f"  fx_move : {fx:+.6f}  # FX move in decimal")
    lines.append(f"  ir_move : {ir:+.6f}  # yield move in decimal")

    lines.append("")
    lines.append("  joint plausibility metrics:")
    lines.append(f"    joint_sigma     : {joint_sigma:.3f}")

    return "\n".join(lines)


def _format_scenario_for_judge(
    scenario: Scenario,
    stats: RiskStats,
) -> str:
    lines: list[str] = []

    lines.append(f"Name: {scenario.name}")
    lines.append(f"Description: {scenario.description}")
    lines.append("")

    lines.append("Exposure instruments (portfolio you want to hedge):")
    for inst in scenario.exposure:
        lines.append(
            f"  - {inst.name}: mtm={inst.mtm_value:.0f} JPY, "
            f"eq_lin={inst.eq_linear} (equity delta), "
            f"eq_quad={inst.eq_quad} (equity convexity), "
            f"vol_lin={inst.vol_linear} (vol sensitivity), "
            f"fx_lin={inst.fx_linear} (FX sensitivity), "
            f"ir_dv01={inst.ir_dv01} (rate DV01, JPY per 1bp move)"
        )
    lines.append("")

    lines.append("Hedge instruments (overlay intended to reduce risk):")
    for inst in scenario.hedge:
        lines.append(
            f"  - {inst.name}: mtm={inst.mtm_value:.0f} JPY, "
            f"eq_lin={inst.eq_linear} (equity delta), "
            f"eq_quad={inst.eq_quad} (equity convexity), "
            f"vol_lin={inst.vol_linear} (vol sensitivity), "
            f"fx_lin={inst.fx_linear} (FX sensitivity), "
            f"ir_dv01={inst.ir_dv01} (rate DV01)"
        )
    lines.append("")

    lines.append("Stats (daily 1σ vols and correlations):")
    lines.append(
        f"  eq_vol={stats.eq_vol}, vol_of_vol={stats.vol_of_vol}, "
        f"fx_vol={stats.fx_vol}, ir_vol={stats.ir_vol}"
    )
    lines.append("  corr_crisis (eq, vol, fx, ir):")
    for row in stats.corr_crisis:
        lines.append(f"    {row}")
    lines.append("")
    lines.append(f"  horizon_days={stats.horizon_days}")

    return "\n".join(lines)


def _format_pnl_block(pnl: PnLBreakdown) -> str:
    net = pnl.net
    exp = pnl.exposure
    hed = pnl.hedge

    lines: list[str] = []
    lines.append("Net P&L totals:")
    lines.append(f"  total : {net.total:,.0f}")
    lines.append(f"  equity: {net.equity:,.0f}")
    lines.append(f"  vol   : {net.vol:,.0f}")
    lines.append(f"  fx    : {net.fx:,.0f}")
    lines.append(f"  rates : {net.rates:,.0f}")
    lines.append("")
    lines.append("Exposure vs. Hedge P&L (totals):")
    lines.append(f"  exposure_total: {exp.total:,.0f}")
    lines.append(f"  hedge_total   : {hed.total:,.0f}")
    return "\n".join(lines)


def _format_quantitative_feedback(metrics: ScenarioMetrics) -> str:
    return f"""
quantitative_score: {metrics.quantitative_score:.2f} [-1, +1]
total_pnl: {metrics.pnl_breakdown.net.total:,.0f} JPY
exposure_amount: {metrics.exposure_amount:,.0f} JPY
loss_ratio: {metrics.loss_ratio:.2f}
joint_sigma: {metrics.factor_moves.joint_sigma:.2f}
{_quant_hint(metrics)}
""".strip()


def _quant_hint(metrics: ScenarioMetrics) -> str:
    qs = metrics.quantitative_score
    lr = metrics.loss_ratio
    js = metrics.factor_moves.joint_sigma

    if lr <= 0.0:
        return "Hint: Portfolio is not losing money; design a scenario where hedges backfire instead of protecting."

    if qs < 0.05:
        return "Hint: Scenario is harmful but inefficient; try achieving similar loss with a smaller joint_sigma."
    elif qs < 0.3:
        return "Hint: Scenario is only mildly harmful; try increasing loss_ratio or reducing joint_sigma."
    elif qs < 0.7:
        return "Hint: Scenario is reasonably harmful; you may still improve loss per unit joint_sigma."
    else:
        return "Hint: Scenario is very efficient."


def _summarize_feedbacks(
    scenarios: list[Scenario],
    combined_score: float,
    quantitative_score: float,
    qualitative_score: float,
    quant_feedbacks: list[str],
    judge_texts: list[str],
    llm_judge: LLMClient,
) -> str:
    # Generate overall summary feedback
    feedbacks_text = "\n\n".join(
        f"=== {scenarios[i].name} ===\n"
        f"Quantitative Feedback: {quant_feedbacks[i]}\n"
        f"Quality Feedback: {judge_texts[i]}"
        for i in range(len(scenarios))
    )

    system_msg = SUMMARY_SYSTEM_MSG.format(len(scenarios))
    msg = SUMMARY_USER_MSG.format(
        feedbacks_text,
        combined_score,
        quantitative_score,
        qualitative_score,
    )
    response = llm_judge.query(
        msg=msg,
        system_msg=system_msg,
        llm_kwargs=llm_judge.get_kwargs(),
    )
    return response.content


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert numpy types (and containers) to plain Python types."""
    if is_dataclass(obj):
        return _to_json_safe(asdict(obj))
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
