from typing import Any


# EVOLVE-BLOCK-START
def analyze_hedge_weakness(
    name: str,
    description: str,
    exposure: list[dict[str, Any]],
    hedge: list[dict[str, Any]],
    net_greeks: dict[str, float],
    stats: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze hedge weaknesses and propose worst-case shock parameters for the given scenario.
    """
    # IMPORTANT: Do NOT change the function signature or return type.

    # Placeholder implementation – evolutionary loop will improve this.
    analysis = f"TODO: analyze scenario '{name}' for exposures, hedges, and weaknesses.\n"

    shock_params = {
        "eq_shock_sigma": -5.0,
        "vol_shock_sigma": 5.0,
        "fx_shock_sigma": 0.0,
        "ir_shock_sigma": 0.0,
        "horizon_days": 5,
        "crisis_intensity": 0.5,
        "rationale": {
            "equity": "TODO",
            "volatility": "TODO",
            "fx": "TODO",
            "rates": "TODO",
            "correlation": "TODO",
        },
    }

    return {
        "analysis": analysis,
        "shock_params": shock_params,
    }
# EVOLVE-BLOCK-END
