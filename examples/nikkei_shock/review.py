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

=== WHAT MAKES A GOOD ANALYSIS ===

Insightful analysis explains the CAUSAL CHAIN of the loss. It does not just
describe what happened (correlation), but explains the MECHANISM of why it
happened (causation).

BAD (describes correlation):
  "The rate shock of +3σ caused large losses on the JGB position due to negative DV01."

GOOD (explains causal mechanism):
  "The hedge was constructed assuming crisis correlations where equity selloffs trigger
   flight-to-quality flows into JGBs, pushing yields down. This scenario violates that
   assumption: rates rise sharply (+3σ) during an equity decline, turning the intended
   rate hedge into the portfolio's largest loss driver. The ¥-142bn rate loss stems from
   the ¥1bn DV01 exposure multiplied by the 142bp yield increase - a move the hedge
   philosophy never anticipated because it assumed rates and equities move inversely."

The good example explains:
1. The implicit assumption in the hedge design (rates fall when equities fall)
2. How the scenario violates that assumption (rates rise instead)
3. The causal mechanism converting the hedge into a loss driver
4. Specific numbers grounding the explanation

=== EVALUATION CRITERIA ===

Score the analysis on a scale from 0.0 to 1.0 based on:

1. **Writing Style** (weight: critical)
   - MUST be written in flowing prose with connected paragraphs
   - NO bullet-point lists, tables, or checklist-style formatting
   - NO numbered lists of facts
   - Each paragraph should build on the previous one, creating a narrative
   - PENALTY: Analyses that are mostly bullets/lists cannot score above 0.50

2. **Causal Depth** (weight: critical)
   - Must explain the MECHANISM of why hedges failed, not just that they failed
   - Must identify the implicit ASSUMPTIONS in the hedge design that were violated
   - Must trace the causal chain: assumption → scenario violation → hedge failure → loss
   - PENALTY: Analyses that only describe "what happened" without "why" cannot score above 0.40

3. **Data Grounding** (weight: critical)
   - All claims must be supported by specific numbers from the data
   - Referenced shock magnitudes, P&L figures, and factor moves must be accurate
   - Hallucinated or incorrect numbers result in score of 0.0

4. **Scenario Specificity** (weight: high)
   - Explains what makes THIS scenario uniquely dangerous for THIS portfolio
   - Avoids generic statements that could apply to any portfolio
   - References specific instruments, Greeks, and their interactions

5. **Structural Insight** (weight: high)
   - Identifies flaws in the hedge DESIGN PHILOSOPHY, not just hedge performance
   - Explains what assumptions were baked into the hedge construction
   - Articulates why those assumptions failed in this scenario

=== SCORING GUIDANCE ===

- 0.00-0.20: Bullet-point lists of facts; no causal explanation; or hallucinated data.
- 0.20-0.40: Some prose but describes "what happened" without explaining "why" or the mechanism.
- 0.40-0.60: Explains loss mechanisms but in bullet/list format; lacks narrative flow.
- 0.60-0.70: Flowing prose that explains causal chains, but insight is surface-level.
- 0.70-0.80: Deep causal insight in flowing prose; identifies violated hedge assumptions.
- 0.80-0.90: Reveals fundamental flaws in the hedge design philosophy with clear causal reasoning.
- 0.90-0.95: Actionable insight on how to restructure the hedge, grounded in specific data.
- 0.95-1.00: Inspirational analysis a senior PM would share; identifies root cause and remediation.

=== IMPORTANT ===

- Be STRICT about prose style: bullet-heavy analyses are capped at 0.50 regardless of content.
- Be STRICT about causal depth: "X happened because Y" is not enough; explain the mechanism.
- ALWAYS cross-check numerical claims against the QUANTITATIVE SUMMARY table.
- The analysis should make the reader UNDERSTAND the failure, not just KNOW about it.

Respond ONLY in this exact format:

quality_score: <float between 0.0 and 1.0>
<2-3 sentences explaining your score, highlighting key strengths or critical gaps>
"""


# Compile regex once and reuse
SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)
DIFFICULTY_RE = re.compile(r"•\s*(.+?):\s*([0-9]*\.?[0-9]+)", re.MULTILINE)
SCORE_MASK_RE = re.compile(r"quality_score\s*:\s*[0-9]*\.?[0-9]+\s*\n?", re.IGNORECASE)


def _extract_quality_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


def _extract_difficulty_weights(scenarios: list[Scenario], output: str) -> list[float]:
    """Extract difficulty weights from summarizer output.

    Args:
        scenarios: List of Scenario objects
        output: Summarizer's text feedback containing difficulty weights

    Returns:
        A list of difficulty weights corresponding to the input scenarios
    """
    # Try to find the SCENARIO DIFFICULTY WEIGHTS section
    matches = dict(DIFFICULTY_RE.findall(output))  # list[tuple[str, str]] to dict[str, str]

    weights = []
    for scenario in scenarios:
        try:
            weights.append(float(matches[scenario.name]))
        except (KeyError, ValueError):
            print(f"Warning: no weight for '{scenario.name}', using uniform weighting")
            return [1.0] * len(scenarios)
    return weights


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

First, assess the RELATIVE DIFFICULTY of each scenario based on:
  • Non-linear exposures (gamma/convexity effects): Harder to explain than linear exposures
  • Multi-factor interactions (3-4 factors vs 1-2): More interactions = more complex
  • Cross-asset complexity (equity-vol correlation, FX translation): Requires deeper understanding
  • Hedge complexity (multiple instruments with conflicting Greeks): More instruments = harder analysis
  • Subtlety of hedge weakness: Is the vulnerability obvious or requires deep insight?

Assign difficulty weights from 0.0 to 1.0 (higher = more difficult to analyze).
Base your assessment on the SCENARIO CHARACTERISTICS, not on the feedback quality.

Then write concise feedback (150-350 words) in the following EXACT format:

SCENARIO DIFFICULTY WEIGHTS:
  • <scenario_name_1>: <weight between 0.0-1.0>
  • <scenario_name_2>: <weight between 0.0-1.0>
  • <scenario_name_3>: <weight between 0.0-1.0>

OVERALL PERFORMANCE: <quality level>

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

Write your summary following the exact format instructed."""


def generate_feedback(
    scenarios: list[Scenario],
    stats: RiskStats,
    shock_params_list: list[ShockParams],
    factor_moves_list: list[FactorMoves],
    pnl_summary_list: list[PnLSummary],
    prompt_list: list[str],
    analysis_list: list[str],
    llm_reviewer: LLMClient,
    llm_summarizer: LLMClient,
    results_dir: str | None = None,
) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs (dataclass-native).

    Args:
        scenarios: List of scenario objects
        stats: Risk statistics
        shock_params_list: List of shock parameters for each scenario
        factor_moves_list: List of factor moves for each scenario
        pnl_summary_list: List of P&L summaries for each scenario
        prompt_list: List of prompts generated by the prompt-builder
        analysis_list: List of analyses generated by the analyst LLM
        llm_reviewer: LLM client for reviewing analyses
        llm_summarizer: LLM client for summarizing feedback
        results_dir: Optional directory to save markdown reports
    """
    # Generate reviews for each scenario analysis
    reviewer_scores: list[float] = []
    reviewer_texts: list[str] = []
    scenario_texts: list[str] = []
    quant_summaries: list[str] = []

    for i in range(len(scenarios)):
        scenario = scenarios[i]
        shock_params = shock_params_list[i]
        factor_moves = factor_moves_list[i]
        pnl_summary = pnl_summary_list[i]
        analysis = analysis_list[i]

        scenario_text = _format_scenario_for_review(scenario, stats)
        scenario_texts.append(scenario_text)
        quant_summary = _build_quantitative_summary_table(
            shock_params, factor_moves, pnl_summary
        )
        quant_summaries.append(quant_summary)
        user_msg = USER_MSG.format(
            scenario_text,
            quant_summary,
            analysis,
        )

        print("\n" + "=" * 50)
        print(f"Generating review {i+1}/{len(scenarios)}")
        print("-" * 50)
        print(user_msg)

        response = llm_reviewer.query(
            msg=user_msg,
            system_msg=SYSTEM_MSG,
            llm_kwargs=llm_reviewer.get_kwargs(),
        )
        score = _extract_quality_score(response.content)

        reviewer_scores.append(score)
        reviewer_texts.append(response.content)

        print("\n" + "=" * 50)
        print(f"Review {i+1}")
        print("-" * 50)
        print(response.content)

    # Generate overall summary feedback with difficulty-weighted scoring
    # Note: We provide scenario details and feedback, but NOT individual scores
    # to avoid the summarizer simply using scores to infer difficulty
    feedbacks_text = "\n\n".join(
        f"=== {scenarios[i].name} ===\n"
        f"{scenario_texts[i]}\n\n"
        f"Feedback: {SCORE_MASK_RE.sub('', reviewer_texts[i])}\n"
        for i in range(len(scenarios))
    )
    msg = SUMMARY_USER_MSG.format(feedbacks_text)
    print("\nGenerating difficulty-weighted summary with summarizer LLM...")
    response = llm_summarizer.query(
        msg=msg,
        system_msg=SUMMARY_SYSTEM_MSG,
        llm_kwargs=llm_summarizer.get_kwargs(),
    )
    text_feedback = response.content

    # Extract difficulty weights from summarizer output
    difficulty_weights = _extract_difficulty_weights(scenarios, text_feedback)

    # Calculate difficulty-weighted score
    weights_array = np.array(difficulty_weights)
    normalized_weights = weights_array / weights_array.sum()
    combined_score = float(np.sum(np.array(reviewer_scores) * normalized_weights))
    avg_score = float(np.mean(reviewer_scores))  # Unweighted average for reference

    print("\n" + "=" * 50)
    print("SCORING SUMMARY")
    print("=" * 50)
    print(f"Reviewer scores: {reviewer_scores}")
    print(f"Difficulty weights: {difficulty_weights}")
    print(f"Weighted score: {combined_score:.3f}")
    print(f"Simple average score: {avg_score:.3f}")
    print("-" * 50)
    print(f"Text feedback:\n{text_feedback}")
    print("=" * 50)

    # Save markdown reports if results_dir is provided
    if results_dir:
        save_markdown_reports(
            results_dir=results_dir,
            scenarios=scenarios,
            scenario_texts=scenario_texts,
            quant_summaries=quant_summaries,
            prompt_list=prompt_list,
            analysis_list=analysis_list,
            reviewer_texts=reviewer_texts,
            reviewer_scores=reviewer_scores,
            difficulty_weights=difficulty_weights,
            normalized_weights=normalized_weights,
            combined_score=combined_score,
            avg_score=avg_score,
            text_feedback=text_feedback,
        )

    # Extract only the OVERALL PERFORMANCE section for public feedback
    public_feedback = re.split(r"OVERALL PERFORMANCE:",
                             text_feedback, flags=re.IGNORECASE)[-1].strip()

    return {
        "combined_score": combined_score,
        "text_feedback": public_feedback,
        "public": {
            **{f"analysis_{i+1}": f"{analysis_list[i]}" for i in range(len(analysis_list))},
            **{f"review_{i+1}": f"{reviewer_texts[i]}" for i in range(len(reviewer_texts))}
        },
        "private": {
            "simple_avg_score": avg_score,
            **{scenarios[i].name: {
                "prompt": prompt_list[i],
                "analysis": analysis_list[i],
                "review": reviewer_texts[i],
                "difficulty_weight": float(normalized_weights[i]),
                "shock_params": _to_json_safe(shock_params_list[i]),
                "factor_moves": _to_json_safe(factor_moves_list[i]),
                "pnl_summary": _to_json_safe(pnl_summary_list[i]),
            } for i in range(len(scenarios))},
        }
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



def save_markdown_reports(
    results_dir: str,
    scenarios: list[Scenario],
    scenario_texts: list[str],
    quant_summaries: list[str],
    prompt_list: list[str],
    analysis_list: list[str],
    reviewer_texts: list[str],
    reviewer_scores: list[float],
    difficulty_weights: list[float],
    normalized_weights: np.ndarray,
    combined_score: float,
    avg_score: float,
    text_feedback: str,
) -> None:
    """Save markdown reports for each scenario and a summary.

    Args:
        results_dir: Directory to save markdown files
        scenarios: List of scenario objects
        scenario_texts: Formatted scenario descriptions
        quant_summaries: Quantitative summary tables
        prompt_list: Prompts generated by the prompt-builder
        analysis_list: Analyses generated by the analyst LLM
        reviewer_texts: Review feedback for each scenario
        reviewer_scores: Quality scores for each scenario
        difficulty_weights: Raw difficulty weights
        normalized_weights: Normalized weights (sum to 1)
        combined_score: Final weighted score
        avg_score: Simple average score
        text_feedback: Summarizer feedback text
    """
    import os

    os.makedirs(results_dir, exist_ok=True)

    # Save individual scenario reports
    for i in range(len(scenarios)):
        scenario_name_safe = scenarios[i].name.lower().replace(" ", "_")
        md_path = os.path.join(results_dir, f"scenario_{i+1}_{scenario_name_safe}.md")
        with open(md_path, "w") as f:
            f.write(f"# {scenarios[i].name}\n\n")
            f.write(f"**Score:** {reviewer_scores[i]:.2f}\n")
            f.write(f"**Difficulty Weight:** {difficulty_weights[i]:.2f}\n\n")
            f.write("## Scenario Description\n\n")
            f.write(f"```\n{scenario_texts[i]}\n```\n\n")
            f.write("## Quantitative Summary\n\n")
            f.write(f"```\n{quant_summaries[i]}\n```\n\n")
            f.write("## Prompt\n\n")
            f.write(f"```\n{prompt_list[i]}\n```\n\n")
            f.write("## Analysis\n\n")
            f.write(f"{analysis_list[i]}\n\n")
            f.write("## Review\n\n")
            f.write(f"{reviewer_texts[i]}\n")
        print(f"Saved: {md_path}")

    # Save summary report
    summary_path = os.path.join(results_dir, "summary.md")
    with open(summary_path, "w") as f:
        f.write("# Evaluation Summary\n\n")
        f.write(f"**Weighted Score:** {combined_score:.3f}\n")
        f.write(f"**Simple Average:** {avg_score:.3f}\n\n")
        f.write("## Scores by Scenario\n\n")
        f.write("| Scenario | Score | Difficulty | Weighted |\n")
        f.write("|----------|-------|------------|----------|\n")
        for i in range(len(scenarios)):
            weighted_contrib = reviewer_scores[i] * normalized_weights[i]
            f.write(f"| {scenarios[i].name} | {reviewer_scores[i]:.2f} | {difficulty_weights[i]:.2f} | {weighted_contrib:.3f} |\n")
        f.write("\n")
        f.write("## Summarizer Feedback\n\n")
        f.write(f"{text_feedback}\n")
    print(f"Saved: {summary_path}")
