import math
import numpy as np
from scenario import (
    Instrument,
    Greeks,
    GreeksBreakdown,
    Scenario,
    RiskStats,
    Rationale,
    ShockParams,
    ScenarioResponse,
)


# EVOLVE-BLOCK-START
def analyze_hedge_weakness(scenario: Scenario, stats: RiskStats) -> ScenarioResponse:
    """Analyze hedge weaknesses and propose worst-case shock parameters."""
    # IMPORTANT: Do NOT change this function signature or the returned structure.

    analysis = f"TODO: analyze scenario '{scenario.name}' for exposures, hedges, and weaknesses.\n"

    shock_params = ShockParams(
        eq_shock_sigma=0.0,
        vol_shock_sigma=0.0,
        fx_shock_sigma=0.0,
        ir_shock_sigma=0.0,
        rationale=Rationale(
            equity=None,
            volatility=None,
            fx=None,
            rates=None,
        ),
    )

    return ScenarioResponse(
        analysis=analysis,
        shock_params=shock_params,
    )
# EVOLVE-BLOCK-END
