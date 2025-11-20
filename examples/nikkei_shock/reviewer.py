import numpy as np
import re
from dataclasses import is_dataclass, asdict
from typing import Any
from quant_types import (
    Scenario,
    RiskStats,
    ShockParams,
    PnLSummary,
    FactorMoves,
)
from shinka.llm import LLMClient


SYSTEM_MSG = """
You are an expert financial risk analyst evaluating the quality of hedge-weakness
analyses produced by another analyst LLM.

Your task is to score how well the ANALYSIS explains why the computed worst-case
shock scenario is particularly harmful to this specific hedged portfolio.

=== EVALUATION CRITERIA ===

Score the analysis on a scale from 0.0 to 1.0 based on:

1. **Exposure Identification** (weight: high)
   - Correctly identifies main portfolio exposures from the instruments
   - References specific instrument names and their Greeks
   - Distinguishes between exposure and hedge contributions

2. **Hedge Intent Explanation** (weight: high)
   - Explains what each hedge is designed to protect
   - Describes expected hedge behavior under normal conditions

3. **Shock Analysis** (weight: very high)
   - Explains why these specific shock directions are harmful
   - References actual shock magnitudes (in σ units)
   - Connects shock severity to the joint_sigma measure
   - Explains how crisis correlations link the factor moves

4. **Loss Driver Explanation** (weight: very high)
   - Identifies which factor moves contribute most to the loss
   - Explains how non-linear exposures (gamma, vega) amplify losses
   - Points out where hedges fail or underperform
   - References actual P&L numbers to support reasoning

5. **Data Consistency** (weight: critical)
   - Analysis does not contradict the provided numbers
   - References match the actual Greeks, shocks, and P&L values
   - Numerical reasoning is sound (even if approximate)

6. **Specificity** (weight: high)
   - Uses scenario-specific detail, not generic statements
   - References actual instruments, numbers, and relationships
   - Avoids boilerplate language that could apply to any portfolio

7. **Technical Quality** (weight: medium)
   - Uses appropriate financial terminology correctly
   - Clear structure and organization
   - Concise and focused

=== IMPORTANT ===
- Be STRICT: Generic, shallow, or numerically inconsistent analyses must score low
- The analysis should explain WHY this shock is bad, not just WHAT the shock is
- Good analyses reference specific numbers from the data tables below
- Focus on evaluating the EXPLANATION quality, not the shock design (shocks are pre-computed)

Respond ONLY in this exact format:

quality_score: <float between 0.0 and 1.0>
<2-3 sentences explaining your score, highlighting key strengths or critical gaps>
"""


# Compile regex once and reuse
SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)


def _extract_quality_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


USER_MSG = """
=== SCENARIO DESCRIPTION ===
{}

=== QUANTITATIVE SUMMARY ===
{}

=== ANALYST'S EXPLANATION ===
{}

Evaluate the quality of the analyst's explanation above using the scoring criteria.
The explanation should accurately reflect the quantitative data and provide meaningful
insight into why this specific shock scenario exploits weaknesses in the hedge overlay.
"""


SUMMARY_SYSTEM_MSG = """
You are an expert evaluator providing feedback to improve a prompt-building function.

The prompt-builder creates prompts that guide an analyst LLM to explain hedge weaknesses.
You've evaluated the quality of the analyst's outputs across multiple scenarios.

Write concise feedback (150-250 words) in the following EXACT format:

OVERALL PERFORMANCE: <combined_score>/1.0 (<quality level>)

STRENGTHS:
  • <common strength 1>
  • <common strength 2>
  • <common strength 3>

GAPS:
  • <recurring weakness 1>
  • <recurring weakness 2>
  • <recurring weakness 3>

PROMPT IMPROVEMENTS FOR NEXT GENERATION:
  1. <actionable suggestion to improve prompt design>
  2. <actionable suggestion to improve prompt design>
  3. <actionable suggestion to improve prompt design>

Quality level must be: Excellent, Strong, Moderate, Weak, or Poor

Focus your improvement suggestions on:
- What information should prompts emphasize or de-emphasize
- How to better structure prompts to elicit specific, data-grounded analyses
- What guidance would help analysts avoid generic statements
- How to encourage references to concrete numbers (Greeks, shocks, P&L)
- Ways to promote better explanation of cross-asset interactions

Remember: You're helping evolve the PROMPT-BUILDER, not the analyst LLM.
"""


SUMMARY_USER_MSG = """
INDIVIDUAL SCENARIO FEEDBACKS:
{}

Combined Score: {:.2f}/1.0

Write your summary now, following the exact format instructed."""


def generate_feedback(
    scenarios: list[Scenario],
    stats: RiskStats,
    shock_params_list: list[ShockParams],
    factor_moves_list: list[FactorMoves],
    pnl_summary_list: list[PnLSummary],
    analysis_list: list[str],
    llm_reviewer: LLMClient,
) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs (dataclass-native)."""

    reviewer_scores: list[float] = []
    reviewer_texts: list[str] = []

    for i in range(len(scenarios)):
        scenario = scenarios[i]
        shock_params = shock_params_list[i]
        factor_moves = factor_moves_list[i]
        pnl_summary = pnl_summary_list[i]
        analysis = analysis_list[i]

        scenario_text = _format_scenario_for_review(scenario, stats)
        quant_summary = _build_quantitative_summary_table(
            shock_params, factor_moves, pnl_summary
        )
        user_msg = USER_MSG.format(
            scenario_text,
            quant_summary,
            analysis,
        )
        response = llm_reviewer.query(
            msg=user_msg,
            system_msg=SYSTEM_MSG,
            llm_kwargs=llm_reviewer.get_kwargs(),
        )
        score = _extract_quality_score(response.content)

        reviewer_scores.append(score)
        reviewer_texts.append(response.content)

    combined_score = float(np.mean(reviewer_scores))

    public_feedback = {
        "combined_score": combined_score,
    }
    for i in range(len(scenarios)):
        public_feedback[f"analysis_{i+1}"] = f"{reviewer_texts[i]}"

    private_feedback = {
        "scenarios": [  # ← Full details here
            {
                "name": scenarios[i].name,
                "analysis": analysis_list[i],
                "shock_params": _to_json_safe(shock_params_list[i]),
                "factor_moves": _to_json_safe(factor_moves_list[i]),
                "pnl_summary": _to_json_safe(pnl_summary_list[i]),
            }
            for i in range(len(scenarios))
        ],
    }

    # Generate overall summary feedback
    feedbacks_text = "\n\n".join(
        f"=== {scenarios[i].name} ===\n"
        f"Feedback: {reviewer_texts[i]}\n"
        for i in range(len(scenarios))
    )

    msg = SUMMARY_USER_MSG.format(
        feedbacks_text,
        combined_score,
    )
    response = llm_reviewer.query(
        msg=msg,
        system_msg=SUMMARY_SYSTEM_MSG,
        llm_kwargs=llm_reviewer.get_kwargs(),
    )
    text_feedback = response.content

    return {
        "combined_score": combined_score,
        "public": public_feedback,
        "text_feedback": text_feedback,
        "private": private_feedback,
    }


def _format_scenario_for_review(
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


def _build_quantitative_summary_table(
    shock_params: ShockParams,
    factor_moves: FactorMoves,
    pnl_summary: PnLSummary,
) -> str:
    """Build a comprehensive quantitative summary table for reviewer."""

    # Calculate loss in billions for readability
    loss_bn = pnl_summary.loss / 1_000_000_000
    net_total_bn = pnl_summary.net.total / 1_000_000_000
    exposure_total_bn = pnl_summary.exposure.total / 1_000_000_000
    hedge_total_bn = pnl_summary.hedge.total / 1_000_000_000

    # P&L breakdown by factor in billions
    net_eq_bn = pnl_summary.net.equity / 1_000_000_000
    net_vol_bn = pnl_summary.net.vol / 1_000_000_000
    net_fx_bn = pnl_summary.net.fx / 1_000_000_000
    net_rates_bn = pnl_summary.net.rates / 1_000_000_000

    table = f"""
SHOCK PARAMETERS (Optimizer Output)
--------------------------------------------------------------------------------
  Equity shock:        {shock_params.eq_shock_sigma:+6.2f} σ
  Vol shock:           {shock_params.vol_shock_sigma:+6.2f} σ
  FX shock (USDJPY):   {shock_params.fx_shock_sigma:+6.2f} σ
  IR shock:            {shock_params.ir_shock_sigma:+6.2f} σ
  Joint sigma:         {shock_params.joint_sigma:6.2f}   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         {factor_moves.eq_move:+8.4%}
  Vol move:            {factor_moves.vol_move:+8.4%}
  FX move:             {factor_moves.fx_move:+8.4%}
  IR move:             {factor_moves.ir_move:+8.4%}

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:       {net_total_bn:+8.2f} bn
    └─ Exposure P&L:   {exposure_total_bn:+8.2f} bn
    └─ Hedge P&L:      {hedge_total_bn:+8.2f} bn

  Net P&L by Factor:
    • Equity:          {net_eq_bn:+8.2f} bn
    • Vol:             {net_vol_bn:+8.2f} bn
    • FX:              {net_fx_bn:+8.2f} bn
    • Rates:           {net_rates_bn:+8.2f} bn

  Loss:                {loss_bn:8.2f} bn
  Loss Ratio:          {pnl_summary.loss_ratio:8.2%} (vs exposure notional)
"""
    return table.strip()


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
