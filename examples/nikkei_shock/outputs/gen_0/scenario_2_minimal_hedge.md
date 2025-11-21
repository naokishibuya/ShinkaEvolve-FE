# Minimal Hedge

**Score:** 0.35
**Difficulty Weight:** 0.35

## Scenario Description

```
Name: Minimal Hedge
Description: Weak hedge with only 40% equity coverage - vulnerability to simple crashes

Exposure instruments (portfolio you want to hedge):
  - Physical_Nikkei_Stocks: mtm=100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01, JPY per 1bp move)

Hedge instruments (overlay intended to reduce risk):
  - Short_Nikkei_Futures: mtm=-40000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)

Stats (daily 1σ vols and correlations):
  eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015
  corr_crisis (eq, vol, fx, ir):
    [ 1.  -0.8 -0.4 -0.5]
    [-0.8  1.   0.3  0.4]
    [-0.4  0.3  1.   0.2]
    [-0.5  0.4  0.2  1. ]

  horizon_days=10
```

## Quantitative Summary

```
SHOCK PARAMETERS (Optimizer Output)
--------------------------------------------------------------------------------
  Equity shock:         -2.20 σ
  Vol shock:            +0.01 σ
  FX shock (USDJPY):    +0.03 σ
  IR shock:             +0.01 σ
  Joint sigma:           3.99   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         -8.3294%
  Vol move:            +0.0632%
  FX move:             +0.0664%
  IR move:             +0.0024%

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:          -5.00 bn
    └─ Exposure P&L:      -8.33 bn
    └─ Hedge P&L:         +3.33 bn

  Net P&L by Factor:
    • Equity:             -5.00 bn
    • Vol:                +0.00 bn
    • FX:                 +0.00 bn
    • Rates:              +0.00 bn

  Loss:                    5.00 bn
  Loss Ratio:             5.00% (vs exposure notional)
```

## Prompt

```
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
Scenario(name='Minimal Hedge', description='Weak hedge with only 40% equity coverage - vulnerability to simple crashes', exposure=[Instrument(name='Physical_Nikkei_Stocks', mtm_value=100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], hedge=[Instrument(name='Short_Nikkei_Futures', mtm_value=-40000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], greeks=Greeks(delta=60000000000.0, gamma=0.0, vega=0.0, fx=0.0, dv01=0.0))

RiskStats(eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015, corr_crisis=array([[ 1. , -0.8, -0.4, -0.5],
       [-0.8,  1. ,  0.3,  0.4],
       [-0.4,  0.3,  1. ,  0.2],
       [-0.5,  0.4,  0.2,  1. ]]), horizon_days=10, max_factor_sigma=3.0, max_joint_sigma=4.0)

ShockParams(eq_shock_sigma=np.float64(-2.1950000000000376), vol_shock_sigma=np.float64(0.010000000000073556), fx_shock_sigma=np.float64(0.03499999999986539), ir_shock_sigma=np.float64(0.005000000000071326), joint_sigma=3.9913445537285166)

FactorMoves(eq_move=-0.08329439356883656, vol_move=0.0006324555320383281, fx_move=0.0006640783086328056, ir_move=2.3717082451601173e-05)

PnLSummary(net=PnL(total=-4997663614.130194, equity=-4997663614.130194, vol=0.0, fx=0.0, rates=0.0), exposure=PnL(total=-8329439356.883656, equity=-8329439356.883656, vol=0.0, fx=0.0, rates=0.0), hedge=PnL(total=3331775742.7534623, equity=3331775742.7534623, vol=0.0, fx=0.0, rates=0.0), exposure_pnls={'Physical_Nikkei_Stocks': PnL(total=-8329439356.883656, equity=-8329439356.883656, vol=0.0, fx=0.0, rates=0.0)}, hedge_pnls={'Short_Nikkei_Futures': PnL(total=3331775742.7534623, equity=3331775742.7534623, vol=-0.0, fx=-0.0, rates=0.0)}, loss=4997663614.130194, notional=100000000000.0, loss_ratio=0.04997663614130194)

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
```

## Analysis

---
**Financial Risk Analysis Report**

**Scenario Overview**  
- **Scenario Name:** Minimal Hedge  
- **Description:** Weak hedge with only 40% equity coverage, exposing the portfolio to significant downside risk in the event of an equity market crash.

**Portfolio Composition**  
- **Exposure:**  
  - Physical Nikkei Stocks: ¥100,000,000,000 (delta = 1.0)
- **Hedge:**  
  - Short Nikkei Futures: -¥40,000,000,000 (delta = 1.0)
- **Net Delta Exposure:** ¥60,000,000,000

**Risk Factor Shocks**  
- **Equity Shock:** -2.195σ, corresponding to an -8.33% move in the Nikkei index over a 10-day horizon.
- **Volatility Shock:** +0.01σ, negligible impact due to zero vega exposure.
- **FX Shock:** +0.035σ, negligible impact due to zero FX exposure.
- **Interest Rate Shock:** +0.005σ, negligible impact due to zero IR exposure.
- **Joint Sigma:** 3.99, indicating a severe, multi-factor stress scenario.

**Correlation Matrix (Crisis Regime)**
- High negative correlation between equity and other risk factors, but only equity risk is material due to portfolio composition.

---

### 1. **PnL Attribution**

| Component                | PnL (¥)           | % of Notional |
|--------------------------|-------------------|--------------|
| **Physical Nikkei Stocks** | -8,329,439,357   | -8.33%       |
| **Short Nikkei Futures**   | +3,331,775,743   | +3.33%       |
| **Net Portfolio PnL**      | -4,997,663,614   | -5.00%       |

- **Total Portfolio Loss:** ¥4,997,663,614  
- **Loss Ratio:** 4.998% of notional

---

### 2. **Risk Analysis**

#### **Equity Risk**
- The portfolio is highly exposed to equity downside, with only 40% of the physical equity exposure hedged via short futures.
- The net delta of ¥60bn results in a direct, linear loss in the event of an equity market decline.
- Under the -8.33% equity shock, the unhedged portion of the portfolio incurs a loss of approximately ¥5bn, as observed.

#### **Hedge Effectiveness**
- The short futures position offsets only 40% of the equity exposure.
- The hedge is linear and does not provide protection against non-linear (gamma) or volatility (vega) risks, though these are not present in the current portfolio.
- The residual risk (unhedged 60% of the equity exposure) is fully exposed to market shocks.

#### **Other Risk Factors**
- **Volatility, FX, and Interest Rate Risks:** No material impact due to zero vega, FX, and IR exposures.
- **Correlation Effects:** The crisis correlation matrix indicates potential for cross-asset contagion, but the portfolio is not exposed to these factors.

---

### 3. **Stress Scenario Outcomes**

- **Severe Equity Drawdown:** The scenario simulates a significant equity market crash, resulting in a 5% portfolio loss over 10 days.
- **Hedge Shortfall:** The partial hedge fails to sufficiently mitigate losses, leaving the portfolio vulnerable to further equity declines.
- **No Diversification Benefit:** The lack of exposure to other risk factors means the portfolio cannot benefit from potential offsetting moves in FX, rates, or volatility.

---

### 4. **Key Risk Metrics**

- **Net Delta Exposure:** ¥60,000,000,000 (unhedged)
- **Portfolio Loss (10-day, -2.2σ equity shock):** ¥4,997,663,614
- **Loss as % of Notional:** 4.998%
- **Hedge Ratio:** 40% (suboptimal for crash protection)

---

### 5. **Conclusions and Recommendations**

- The portfolio is highly vulnerable to equity market crashes due to insufficient hedging.
- The current hedge ratio (40%) is inadequate for risk mitigation in severe market downturns.
- No material risk from volatility, FX, or interest rates, but also no diversification benefit.
- To reduce risk, increase the hedge ratio or introduce additional hedging instruments (e.g., options for non-linear protection).
- Consider diversification into other asset classes or risk factors to reduce concentration risk.

---

**Summary:**  
The portfolio, under the "Minimal Hedge" scenario, demonstrates significant vulnerability to equity market shocks, with a projected 5% loss of notional under a severe 10-day stress. The partial hedge provides limited protection, and the absence of diversification amplifies downside risk. Immediate action to enhance hedging and diversify exposures is recommended to mitigate future losses.

## Review

quality_score: 0.35  
While the analysis is thorough in its description of the portfolio composition, hedge ratio, and resulting P&L, it primarily catalogs "what happened" rather than "why" the hedge failed in this scenario. The explanation is heavily structured as a series of headings and bullet-style sections, lacking the required narrative flow. Most critically, it does not articulate the implicit assumption in the hedge design (e.g., that a 40% hedge would be sufficient for typical moves or that other risk factors might offset equity losses), nor does it trace a causal chain explaining why this particular equity shock exposes the portfolio's vulnerability. The analysis is accurate and data-grounded, but it falls short on causal depth and prose style, resulting in a low score.
