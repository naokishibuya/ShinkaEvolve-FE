import numpy as np
import re
from typing import Any
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
- config: max_sigma_ratio (shock size), max_horizon_days, lambda_penalty.

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
"""


SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)


def extract_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


def generate_feedback(scenarios: list[dict], analyses: list[str], llm_judge: LLMClient) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs."""
    user_msgs = []
    judge_scores = []
    judge_texts = []

    for scenario, analysis in zip(scenarios, analyses):
        scenario_text = _format_scenario_for_judge(scenario)
        user_msg = USER_MSG.format(scenario_text, analysis)

        response = llm_judge.query(msg=user_msg, system_msg=SYSTEM_MSG, llm_kwargs=llm_judge.get_kwargs())
        score = extract_score(response.content)

        user_msgs.append(user_msg)
        judge_scores.append(score)
        judge_texts.append(response.content)

    combined_score = float(np.mean(judge_scores))

    analyses = _to_json_safe(analyses)
    scenarios = _to_json_safe(scenarios)
    public_feedback = [
        {
            "scenario_name": scenario["name"],
            "analysis": analyses[i],
            "judge_score": judge_scores[i],
            "judge_text": judge_texts[i],
        }
        for i, scenario in enumerate(scenarios)
    ]

    private_feedback = {
        "system_msg": SYSTEM_MSG,
        "user_msgs": user_msgs
    }

    text_feedback = "\n\n".join(
        [
            f"--- Scenario: {scenario['name']} ---\n"
            f"{judge_texts[i]}"
            for i, scenario in enumerate(scenarios)
        ]
    )

    return {
        "combined_score": combined_score,
        "public": public_feedback,
        "private": private_feedback,
        "text_feedback": text_feedback,
    }


def _format_scenario_for_judge(scenario: dict) -> str:
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
            f"ir_dv01={inst['ir_dv01']} (rate DV01)"
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

    stats = scenario["stats"]
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

    cfg = scenario["config"]
    lines.append("Config (shock bounds and penalties):")
    lines.append(
        f"  max_sigma_ratio={cfg['max_sigma_ratio']}, "
        f"max_horizon_days={cfg['max_horizon_days']}, "
        f"lambda_penalty={cfg['lambda_penalty']}"
    )

    return "\n".join(lines)


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
