def render_report(result) -> str:
    """
    Render a scenario evaluation report.

    Args:
        result: ScenarioResult object
    """
    p = result.params
    s = result.shock

    lines = []
    lines.append("=== Scenario Report ===")
    lines.append(f"Sigmas: EQ={p.eq_sigmas:.2f}, VOL={p.vol_sigmas:.2f}, "
                 f"FX={p.fx_sigmas:.2f}, IR={p.ir_sigmas:.2f}")
    lines.append(f"Horizon: {p.horizon_days} days, crisis_intensity={p.crisis_intensity:.2f}")
    lines.append("")
    lines.append(f"Factor moves:")
    lines.append(f"  Nikkei return: {s.eq_ret*100:.2f}%")
    lines.append(f"  Implied vol change: {s.vol_change*100:.2f} vol pts")
    lines.append(f"  USDJPY return: {s.fx_ret*100:.2f}%")
    lines.append(f"  10Y JGB yield change: {s.ir_change*100:.2f} bp")

    lines.append("")
    lines.append(f"Base portfolio PnL:   {result.base_pnl:,.0f} JPY")
    lines.append(f"Hedged portfolio PnL: {result.hedge_pnl:,.0f} JPY")
    lines.append(f"Base loss:   {result.base_loss:,.0f} JPY")
    lines.append(f"Hedged loss: {result.hedge_loss:,.0f} JPY")
    lines.append(f"Hedge effectiveness (loss reduction): {result.hedge_effectiveness:,.0f} JPY")

    lines.append("")
    lines.append(f"Plausibility penalty: {result.plaus_penalty:.4f}")

    # Simple interpretation line
    if result.hedge_effectiveness < 0:
        lines.append("WARNING: Hedge made things worse under this scenario.")
    elif result.hedge_effectiveness < 0.0:
        lines.append("Hedge slightly worsened outcome.")
    elif result.hedge_effectiveness < 1e8:
        lines.append("Hedge provides limited protection.")
    else:
        lines.append("Hedge provides substantial protection in this scenario.")

    return "\n".join(lines)

