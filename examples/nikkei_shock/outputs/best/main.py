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
    def format_instrument(instr: Instrument) -> str:
        return (
            f"- {instr.name} (MTM: ¥{instr.mtm_value:,.0f}, "
            f"Eq Delta: {instr.eq_linear:.3f}, Eq Gamma: {instr.eq_quad:.3f}, "
            f"Vega: {instr.vol_linear:.3f}, FX: {instr.fx_linear:.3f}, DV01: {instr.ir_dv01:.3f})"
        )

    def format_pnl(pnl: PnL) -> str:
        return (
            f"Total: ¥{pnl.total:,.0f}, Equity: ¥{pnl.equity:,.0f}, Vol: ¥{pnl.vol:,.0f}, "
            f"FX: ¥{pnl.fx:,.0f}, Rates: ¥{pnl.rates:,.0f}"
        )

    def format_greeks(greeks: Greeks) -> str:
        return (
            f"Delta: ¥{greeks.delta:,.0f}, Gamma: ¥{greeks.gamma:,.0f}, Vega: ¥{greeks.vega:,.0f}, "
            f"FX: ¥{greeks.fx:,.0f}, DV01: ¥{greeks.dv01:,.0f}"
        )

    def format_factor_moves(fm: FactorMoves) -> str:
        return (
            f"Equity move: {fm.eq_move*100:.3f}%, Vol move: {fm.vol_move*100:.3f}%, "
            f"FX move: {fm.fx_move*100:.3f}%, IR move: {fm.ir_move*100:.3f}%"
        )

    # Format crisis correlation matrix in readable form
    corr_labels = ["Equity", "Volatility", "FX", "Interest Rates"]
    corr_matrix = stats.corr_crisis
    corr_rows = []
    for i, row_label in enumerate(corr_labels):
        row_vals = [f"{corr_matrix[i,j]:.2f}" for j in range(len(corr_labels))]
        corr_rows.append(f"{row_label:12}: " + "  ".join(row_vals))

    exposure_list = "\n".join(format_instrument(instr) for instr in scenario.exposure)
    hedge_list = "\n".join(format_instrument(instr) for instr in scenario.hedge)

    exposure_pnl_lines = []
    for name, pnl in pnl_summary.exposure_pnls.items():
        exposure_pnl_lines.append(f"  {name}: {format_pnl(pnl)}")
    exposure_pnl_text = "\n".join(exposure_pnl_lines)

    hedge_pnl_lines = []
    for name, pnl in pnl_summary.hedge_pnls.items():
        hedge_pnl_lines.append(f"  {name}: {format_pnl(pnl)}")
    hedge_pnl_text = "\n".join(hedge_pnl_lines)

    # Compose the prompt with clear sections and detailed instructions
    prompt = f"""
You are a senior financial risk analyst tasked with producing a comprehensive hedge-weakness analysis
for the following portfolio scenario under an optimized worst-case market shock.

---
SCENARIO OVERVIEW:

Name: {scenario.name}
Description: {scenario.description}

EXPOSURE INSTRUMENTS:
{exposure_list}

HEDGE INSTRUMENTS:
{hedge_list}

PORTFOLIO NET GREEKS:
{format_greeks(scenario.greeks)}

RISK STATS (Crisis Regime):
- Horizon Days: {stats.horizon_days}
- Daily 1σ Volatilities:
  Equity: {stats.eq_vol:.3%}, Volatility: {stats.vol_of_vol:.3%}, FX: {stats.fx_vol:.3%}, Interest Rates: {stats.ir_vol:.3%}
- Crisis Correlation Matrix (rows=Equity, Vol, FX, IR):
{chr(10).join(corr_rows)}
- Max Factor Sigma: {stats.max_factor_sigma:.2f}
- Max Joint Sigma: {stats.max_joint_sigma:.2f}

SHOCK PARAMETERS (Pre-scaling σ units):
- Equity Shock: {shock.eq_shock_sigma:+.3f}σ
- Volatility Shock: {shock.vol_shock_sigma:+.3f}σ
- FX Shock: {shock.fx_shock_sigma:+.3f}σ
- Interest Rate Shock: {shock.ir_shock_sigma:+.3f}σ
- Joint Shock Sigma (Mahalanobis distance): {shock.joint_sigma:.3f}

ACTUAL FACTOR MOVES (Scaled for horizon and vol):
{format_factor_moves(factor_moves)}

PNL SUMMARY:
- Net Portfolio P&L: {format_pnl(pnl_summary.net)}
- Exposure-Only P&L:
{exposure_pnl_text}
- Hedge-Only P&L:
{hedge_pnl_text}
- Loss: ¥{pnl_summary.loss:,.0f} (Loss ratio: {pnl_summary.loss_ratio:.3%} of notional ¥{pnl_summary.notional:,.0f})

---

ANALYSIS TASK:

Please provide a detailed, scenario-specific hedge-weakness analysis addressing the following points:

1. Portfolio Exposures:
   - Identify and summarize the main portfolio exposures by instrument name and mark-to-market value.
   - Discuss the net portfolio Greeks (delta, gamma, vega, FX, DV01) and interpret their economic meaning.
   - Distinguish exposure instruments from hedge instruments in terms of their directional and sensitivity profiles.

2. Hedge Intent:
   - For each hedge instrument, explain its intended protective role.
   - Describe how the hedge is expected to perform under normal market conditions and its theoretical risk mitigation purpose.

3. Shock Scenario Analysis:
   - Explain why the specific shock directions and magnitudes (including sign) are particularly harmful to this portfolio.
   - Discuss how the magnitudes relate to crisis volatilities and the maximum allowed sigmas.
   - Analyze the joint sigma value and explain what it implies about the severity and plausibility of this stress event.
   - Reference the crisis correlation matrix to describe how factor co-movements exacerbate or mitigate portfolio risk.

4. Loss Drivers and Hedge Breakdown:
   - Identify which risk factors (equity, vol, FX, rates) contribute most to the overall loss.
   - Explain how linear exposures (delta, DV01) and non-linear exposures (gamma, vega) interact with the factor moves to produce the realized P&L.
   - Analyze where and why hedges fail or underperform—highlight any structural weaknesses or assumptions in the hedge construction.
   - If some hedges worsen portfolio loss, explain the mechanism.

5. Structural and Scenario-Specific Insights:
   - Critically evaluate the hedge design philosophy and any implicit assumptions about market behavior or factor correlations that this scenario exposes.
   - Discuss potential multi-factor interactions, cross-asset dependencies, and crisis regime behaviors that amplify losses beyond simple additive effects.
   - Analyze how breakdowns or shifts in typical crisis correlations contribute to hedge underperformance and portfolio vulnerability.
   - Quantify and discuss the role of joint sigma in exacerbating losses beyond individual factor shocks.
   - Provide scenario-specific, actionable recommendations for hedge restructuring, mitigation strategies, or alternative constructions. Detail specific structural changes or instruments to consider, referencing the data.
   - Avoid generic advice; ground recommendations in the observed data and structural weaknesses.

6. Summary:
   - Conclude with a concise synthesis of the portfolio’s key vulnerabilities and the rationale behind them, supported by quantitative particulars from the data above.

---

Remember: Use precise numbers and instrument names from the provided data. Avoid generic or boilerplate explanations. Ground every insight firmly in the scenario’s unique quantitative details. Your analysis should reveal deep structural weaknesses and provide clear, actionable guidance.

Begin your detailed hedge-weakness analysis now.
""".strip()

    return prompt
# EVOLVE-BLOCK-END