import numpy as np
import re
from typing import Any
from shinka.llm import LLMClient


SYSTEM_MSG = (
    "You are an expert risk manager. Your task is to evaluate how well an analysis identifies:\n"
    "1) the portfolio's true exposures,\n"
    "2) what each hedge instrument is intended to insure,\n"
    "3) structural weaknesses or residual risks,\n"
    "4) and whether the reasoning is consistent with the scenario data.\n"
    "Judge based strictly on clarity, correctness, and depth of insight."
)

def get_user_prompt(scenario_yaml: str, analysis: str) -> str:
    return (
        "=== SCENARIO (YAML) ===\n"
        f"{scenario_yaml}\n\n"
        "=== ANALYSIS ===\n"
        f"{analysis}\n\n"
        "=== JUDGMENT INSTRUCTIONS ===\n"
        "Review the scenario and its analysis.\n"
        "Assign ONE quality_score between 0 and 1 based on:\n"
        "- correctness of interpretation,\n"
        "- depth and specificity of hedge-weakness reasoning,\n"
        "- clarity and coherence.\n\n"
        "Respond ONLY in this exact format:\n"
        "quality_score: <float>\n"
    )


SCORE_RE = re.compile(r"quality_score\s*:\s*([0-9]*\.?[0-9]+)", re.I)


def extract_score(output: str) -> float:
    m = SCORE_RE.search(output)
    if not m:
        return 0.0
    return float(m.group(1))


def generate_feedback(all_run_results: list[dict[str, Any]], llm_judge: LLMClient) -> dict[str, Any]:
    """Aggregate feedback from multiple scenario runs."""
    scenario_scores = []
    judge_texts = []

    for result in all_run_results:
        scenario_yaml = result["scenario"]["scenario_yaml"]
        analysis = result["analysis"]
        user_msg = get_user_prompt(scenario_yaml, analysis)
        resp = llm_judge.query(msg=user_msg, system_msg=SYSTEM_MSG, llm_kwargs=llm_judge.get_kwargs())
        score = extract_score(resp.content)
        scenario_scores.append(score)
        judge_texts.append(resp.content)

    combined_score = float(sum(scenario_scores) / max(len(scenario_scores), 1))

    text_feedback = "\n\n".join(
        [
            f"--- Scenario: {result['scenario']['name']} ---\n"
            f"{judge_texts[i]}"
            for i, result in enumerate(all_run_results)
        ]
    )

    return {
        "combined_score": combined_score,
        "public": {
            "num_scenarios": len(all_run_results),
            "judge_scores": scenario_scores,
        },
        "private": {
            "all_run_results": _to_json_safe(all_run_results),
            "judge_texts": judge_texts,
        },
        "text_feedback": text_feedback,
    }


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
