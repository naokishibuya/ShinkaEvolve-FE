import math
import numpy as np
from quant_types import (
    Instrument,
    Greeks,
    Scenario,
    RiskStats,
    ShockParams,
    FactorMoves,
    PnL,
    PnLSummary,
)


# EVOLVE-BLOCK-START
def build_analysis_prompt(
    scenario: Scenario,
    stats: RiskStats,
    shock: ShockParams,
    factor_moves: FactorMoves,
    pnl_summary: PnLSummary,
) -> str:
    return f"""
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
{scenario}

{stats}

{shock}

{factor_moves}

{pnl_summary}

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
    """.strip()
# EVOLVE-BLOCK-END
