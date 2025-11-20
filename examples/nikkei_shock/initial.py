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
        You are a financial risk analyst. Given the following scenario and shock parameters, provide a detailed analysis of the potential impacts on the portfolio.
        Scenario Name: {scenario.name}
        Description: {scenario.description}
        Exposure Instruments: {', '.join([inst.name for inst in scenario.exposure])}
        Hedge Instruments: {', '.join([inst.name for inst in scenario.hedge])}
        Statistics:
          - Daily Equity Volatility: {stats.eq_vol}
          - Daily Volatility of Volatility: {stats.vol_of_vol}
          - Daily FX Volatility: {stats.fx_vol}
          - Daily Interest Rate Volatility: {stats.ir_vol}
          - Crisis Correlation Matrix: {stats.corr_crisis.tolist()}
          - Crisis Horizon (days): {stats.horizon_days}
          - Max Factor Sigma: {stats.max_factor_sigma}
          - Max Joint Sigma: {stats.max_joint_sigma}
        Shock Parameters:
          - Equity Sigma: {shock.eq_shock_sigma}
          - Volatility Sigma: {shock.vol_shock_sigma}
          - FX Sigma: {shock.fx_shock_sigma}
          - Interest Rate Sigma: {shock.ir_shock_sigma}
          - Joint Sigma (Mahalanobis Distance): {shock.joint_sigma}
        Factor Moves:
          - Equity Move: {factor_moves.eq_move}
          - Volatility Move: {factor_moves.vol_move}
          - FX Move: {factor_moves.fx_move}
          - Interest Rate Move: {factor_moves.ir_move}
        PnL Summary:
          - Total PnL: {pnl_summary.net.total}
          - Equity PnL: {pnl_summary.net.equity}
          - Volatility PnL: {pnl_summary.net.vol}
          - FX PnL: {pnl_summary.net.fx}
          - Rates PnL: {pnl_summary.net.rates}
          - Loss: {pnl_summary.loss}
          - Notional: {pnl_summary.notional}
          - Loss Percentage: {pnl_summary.loss_ratio * 100}%
        Based on the above information, analyze the risks and potential outcomes for the portfolio.
        Provide your analysis in a clear and structured manner.
    """.strip()
# EVOLVE-BLOCK-END
