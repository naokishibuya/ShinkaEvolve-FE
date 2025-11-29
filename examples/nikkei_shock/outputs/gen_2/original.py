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
    # Format Greeks data
    greeks = scenario.greeks
    greeks_text = (
        f"Net Portfolio Greeks:\n"
        f"  - Equity Delta: {greeks.delta:,.0f} JPY / 1σ equity move\n"
        f"  - Equity Gamma: {greeks.gamma:,.0f} JPY / (1σ equity move)^2\n"
        f"  - Vega (Volatility sensitivity): {greeks.vega:,.0f} JPY / 1σ vol move\n"
        f"  - FX Sensitivity: {greeks.fx:,.0f} JPY / 1σ FX move\n"
        f"  - DV01 (Interest Rate sensitivity): {greeks.dv01:,.0f} JPY / +1bp rate move\n"
    )

    # Format shock parameters with scaling context
    horizon = stats.horizon_days
    eq_shock_scaled = shock.eq_shock_sigma * stats.eq_vol * math.sqrt(horizon)
    vol_shock_scaled = shock.vol_shock_sigma * stats.vol_of_vol * math.sqrt(horizon)
    fx_shock_scaled = shock.fx_shock_sigma * stats.fx_vol * math.sqrt(horizon)
    ir_shock_scaled = shock.ir_shock_sigma * stats.ir_vol * math.sqrt(horizon)

    corr_matrix = stats.corr_crisis
    corr_text = (
        "Crisis Regime Correlation Matrix (order: Equity, Vol, FX, IR):\n"
        f"{np.array2string(corr_matrix, precision=2, separator=', ')}\n"
        "Note: Strong negative correlations between equity and rates/volatility often amplify losses in stress."
    )

    # Compose instruments summaries with Greeks for exposure and hedge
    def format_instruments(insts: list[Instrument], title: str) -> str:
        lines = [f"{title} Instruments:"]
        for inst in insts:
            lines.append(
                f"  - {inst.name}: MTM={inst.mtm_value:,.0f} JPY, "
                f"Equity Delta={inst.eq_linear:,.2f}, Gamma={inst.eq_quad:,.2f}, "
                f"Vega={inst.vol_linear:,.2f}, FX Delta={inst.fx_linear:,.2f}, "
                f"DV01={inst.ir_dv01:,.0f} JPY/bp"
            )
        return "\n".join(lines)

    exposure_text = format_instruments(scenario.exposure, "Exposure")
    hedge_text = format_instruments(scenario.hedge, "Hedge")

    # P&L attribution summary with key numbers
    pnl = pnl_summary.net
    pnl_text = (
        f"Net Portfolio P&L: {pnl.total:,.0f} JPY\n"
        f"P&L by Factor:\n"
        f"  - Equity: {pnl.equity:,.0f} JPY\n"
        f"  - Volatility: {pnl.vol:,.0f} JPY\n"
        f"  - FX: {pnl.fx:,.0f} JPY\n"
        f"  - Interest Rates: {pnl.rates:,.0f} JPY\n"
        f"Loss Ratio (Loss / Notional): {pnl_summary.loss_ratio:.2%}\n"
    )

    # Brief instructions to analyst emphasizing causal narrative, hedge assumptions, and multi-factor interactions
    prompt = f"""
You are an experienced financial risk analyst tasked with producing a detailed hedge-weakness analysis for a crisis stress scenario. Using the data below, write a clear, structured, scenario-specific narrative analysis that explicitly:

1. Portfolio Exposures:
   - Identify and explain the main portfolio exposures, referencing specific instruments by name and their Greeks.
   - Distinguish between exposure and hedge contributions to risks and sensitivities.
   - Quantify net portfolio sensitivities (delta, gamma, vega, FX, DV01).

2. Hedge Intent and Assumptions:
   - Explain the primary purpose and risk protection goals of each hedge instrument.
   - Articulate the implicit assumptions embedded in the hedge design, e.g., expected factor correlations, volatility regimes, or directional moves.
   - Describe how the hedge instruments are expected to behave under normal and crisis conditions.

3. Crisis Shock Scenario Analysis:
   - Characterize the worst-case shock in terms of factor directions, magnitudes, and joint severity (Mahalanobis distance).
   - Explain how factor volatilities and crisis correlations shape the shock’s impact.
   - Highlight which factor moves are particularly damaging relative to the portfolio’s sensitivities.

4. Loss Drivers and Structural Weaknesses:
   - Analyze how linear (delta) and nonlinear (gamma, vega) exposures contribute to losses.
   - Explain how the shock scenario violates the hedge assumptions or exploits structural vulnerabilities.
   - Discuss cross-asset and multi-factor interactions, including correlation effects that amplify losses or reduce hedge effectiveness.
   - Reference specific instruments and P&L contributions that demonstrate hedge underperformance or failure.

5. Recommendations and Risk Insights:
   - Suggest risk mitigation strategies based on the identified structural weaknesses.
   - Discuss how improved hedge design or diversification could reduce vulnerability in similar stress scenarios.

Important: Use concrete numbers and sensitivities from the data below to support your analysis. Avoid generic or template-like language. Your analysis must be deeply causal, explaining why and how the portfolio’s hedge overlay breaks down under this specific crisis scenario.

-----

Scenario: {scenario.name}
Description: {scenario.description}

{exposure_text}

{hedge_text}

{greeks_text}

Shock Parameters (scaled to {horizon}-day horizon):
  - Equity shock: {shock.eq_shock_sigma:.2f}σ (scaled move {eq_shock_scaled:.4%})
  - Volatility shock: {shock.vol_shock_sigma:.2f}σ (scaled move {vol_shock_scaled:.4%})
  - FX shock: {shock.fx_shock_sigma:.2f}σ (scaled move {fx_shock_scaled:.4%})
  - Interest Rate shock: {shock.ir_shock_sigma:.2f}σ (scaled move {ir_shock_scaled:.4%})
  - Joint shock severity (Mahalanobis distance): {shock.joint_sigma:.2f}σ

{corr_text}

Factor Moves (absolute units after scaling):
  - Equity: {factor_moves.eq_move:.4%}
  - Volatility: {factor_moves.vol_move:.4%}
  - FX: {factor_moves.fx_move:.4%}
  - Interest Rates: {factor_moves.ir_move:.4%}

{pnl_text}

-----

Provide your detailed hedge-weakness analysis below.
"""
    return prompt.strip()
# EVOLVE-BLOCK-END