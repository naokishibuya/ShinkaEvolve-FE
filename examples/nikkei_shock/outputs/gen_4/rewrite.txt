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
    greeks = scenario.greeks
    horizon = stats.horizon_days
    sqrt_h = math.sqrt(horizon)

    # Scale shocks to absolute moves for clarity
    eq_shock_scaled = shock.eq_shock_sigma * stats.eq_vol * sqrt_h
    vol_shock_scaled = shock.vol_shock_sigma * stats.vol_of_vol * sqrt_h
    fx_shock_scaled = shock.fx_shock_sigma * stats.fx_vol * sqrt_h
    ir_shock_scaled = shock.ir_shock_sigma * stats.ir_vol * sqrt_h

    # Format crisis correlation matrix with labels and signs for readability
    corr_labels = ["Equity", "Volatility", "FX", "Interest Rates"]
    corr_rows = []
    header = "          " + "  ".join(f"{lbl[:3]}" for lbl in corr_labels)
    corr_rows.append(header)
    for i, row in enumerate(stats.corr_crisis):
        vals = "  ".join(f"{v:+.2f}" for v in row)
        corr_rows.append(f"{corr_labels[i]:<9} {vals}")
    corr_text = (
        "Crisis Regime Correlation Matrix (factors order: Equity, Volatility, FX, Interest Rates):\n"
        + "\n".join(corr_rows)
        + "\n\nNote: Crisis correlations often invert or intensify stress; analyze their impact on hedge effectiveness."
    )

    # Format instruments nicely with Greeks
    def format_instruments(insts: list[Instrument], title: str) -> str:
        lines = [f"{title} Instruments (MTM and Greeks):"]
        for inst in insts:
            lines.append(
                f"  - {inst.name}: MTM={inst.mtm_value:,.0f} JPY, "
                f"Eq Delta={inst.eq_linear:+.3f}, Gamma={inst.eq_quad:+.3f}, "
                f"Vega={inst.vol_linear:+.3f}, FX Delta={inst.fx_linear:+.3f}, "
                f"DV01={inst.ir_dv01:+,.0f} JPY/bp"
            )
        return "\n".join(lines)

    exposure_text = format_instruments(scenario.exposure, "Exposure")
    hedge_text = format_instruments(scenario.hedge, "Hedge")

    pnl = pnl_summary.net
    pnl_text = (
        f"Net Portfolio P&L: {pnl.total:,.0f} JPY\n"
        f"P&L Breakdown by Risk Factor:\n"
        f"  - Equity: {pnl.equity:,.0f} JPY\n"
        f"  - Volatility: {pnl.vol:,.0f} JPY\n"
        f"  - FX: {pnl.fx:,.0f} JPY\n"
        f"  - Interest Rates: {pnl.rates:,.0f} JPY\n"
        f"Loss Ratio (Loss / Notional): {pnl_summary.loss_ratio:.2%}\n"
    )

    greeks_text = (
        f"Net Portfolio Greeks (sensitivities per unit move):\n"
        f"  - Equity Delta: {greeks.delta:,.0f} JPY / 1σ equity move\n"
        f"  - Equity Gamma: {greeks.gamma:,.0f} JPY / (1σ equity move)^2\n"
        f"  - Vega (Volatility sensitivity): {greeks.vega:,.0f} JPY / 1σ vol move\n"
        f"  - FX Sensitivity: {greeks.fx:,.0f} JPY / 1σ FX move\n"
        f"  - DV01 (Interest Rate sensitivity): {greeks.dv01:,.0f} JPY / +1bp rate move\n"
    )

    prompt = f"""
You are a senior financial risk analyst with specialization in multi-factor hedge design and crisis stress testing.  
Using the data below for this unique portfolio and crisis shock scenario, produce a thorough, deeply causal hedge-weakness analysis structured as follows:

1. Portfolio Exposures and Greeks:
   - Identify and quantify the primary portfolio exposures by instrument, explicitly naming each and citing MTM and Greeks.
   - Clearly differentiate the roles and sensitivities of exposures versus hedges.
   - Summarize net portfolio Greeks and link them explicitly to individual instruments' contributions.

2. Hedge Intent and Embedded Assumptions:
   - Explain the risk protection goals for each hedge instrument.
   - Articulate the implicit assumptions about crisis factor correlations, volatility regimes, and directional moves underlying the hedge design.
   - Describe the expected performance and behavior of each hedge under both normal and crisis conditions, focusing on assumed factor dynamics.

3. Crisis Shock Scenario Characterization:
   - Present a detailed description of the worst-case shock, including factor directions, magnitudes, and joint severity (Mahalanobis distance).
   - Explain how factor volatilities and crisis correlations influence portfolio risk and the effectiveness of hedges.
   - Identify and quantify which factor moves cause the largest losses relative to portfolio sensitivities.

4. Loss Drivers and Structural Weaknesses:
   - Analyze linear (delta) and nonlinear (gamma, vega) contributions to losses with explicit numeric references.
   - Provide a causal explanation of how the scenario's shocks violate hedge assumptions or exploit structural vulnerabilities.
   - Discuss multi-factor and cross-asset interactions, especially correlation breakdowns that amplify losses or degrade hedge effectiveness.
   - Reference specific instruments and P&L components to illustrate hedge underperformance or failure.

5. Recommendations and Risk Mitigation Insights:
   - Offer actionable, scenario-specific risk mitigation strategies directly addressing the structural weaknesses identified.
   - Discuss how hedge redesign or diversification can mitigate causal vulnerabilities revealed by this scenario.
   - Where possible, quantify how alternative hedge adjustments could change scenario outcomes.

Important: Anchor your analysis rigorously in quantitative data—reference specific Greeks, shock magnitudes, factor moves, and P&L figures. Avoid generic or boilerplate language. Your narrative must be scenario-specific, integrating nonlinearities, multi-factor dependencies, and correlation regime dynamics into a coherent causal story.

-----

Scenario: {scenario.name}
Description: {scenario.description}

{exposure_text}

{hedge_text}

{greeks_text}

Shock Parameters (scaled to {horizon}-day horizon):
  - Equity shock: {shock.eq_shock_sigma:+.2f}σ (absolute scaled move {eq_shock_scaled:.4%})
  - Volatility shock: {shock.vol_shock_sigma:+.2f}σ (absolute scaled move {vol_shock_scaled:.4%})
  - FX shock: {shock.fx_shock_sigma:+.2f}σ (absolute scaled move {fx_shock_scaled:.4%})
  - Interest Rate shock: {shock.ir_shock_sigma:+.2f}σ (absolute scaled move {ir_shock_scaled:.4%})
  - Joint shock severity (Mahalanobis distance): {shock.joint_sigma:.2f}σ

{corr_text}

Factor Moves (absolute units after horizon scaling):
  - Equity: {factor_moves.eq_move:+.4%}
  - Volatility: {factor_moves.vol_move:+.4%}
  - FX: {factor_moves.fx_move:+.4%}
  - Interest Rates: {factor_moves.ir_move:+.4%}

{pnl_text}

-----

Begin your detailed hedge-weakness analysis below.
"""
    return prompt.strip()
# EVOLVE-BLOCK-END