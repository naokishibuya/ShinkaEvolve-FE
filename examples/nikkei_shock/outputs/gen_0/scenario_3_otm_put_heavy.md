# OTM Put Heavy

**Score:** 0.45
**Difficulty Weight:** 0.75

## Scenario Description

```
Name: OTM Put Heavy
Description: Over-hedged with expensive deep OTM puts - vulnerable to vol crush

Exposure instruments (portfolio you want to hedge):
  - Physical_Nikkei_Stocks: mtm=100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01, JPY per 1bp move)

Hedge instruments (overlay intended to reduce risk):
  - Short_Nikkei_Futures: mtm=-100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Long_OTM_Puts: mtm=10000000000 JPY, eq_lin=-0.2 (equity delta), eq_quad=12.0 (equity convexity), vol_lin=5.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Short_USDJPY_Futures: mtm=50000000000 JPY, eq_lin=0.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=-1.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)

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
  Equity shock:         +0.05 σ
  Vol shock:            -2.18 σ
  FX shock (USDJPY):    +1.69 σ
  IR shock:             +0.00 σ
  Joint sigma:           3.97   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         +0.1839%
  Vol move:            -13.8080%
  FX move:             +3.2065%
  IR move:             +0.0000%

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:          -8.51 bn
    └─ Exposure P&L:      +0.18 bn
    └─ Hedge P&L:         -8.69 bn

  Net P&L by Factor:
    • Equity:             -0.00 bn
    • Vol:                -6.90 bn
    • FX:                 -1.60 bn
    • Rates:              +0.00 bn

  Loss:                    8.51 bn
  Loss Ratio:             8.51% (vs exposure notional)
```

## Prompt

```
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
Scenario(name='OTM Put Heavy', description='Over-hedged with expensive deep OTM puts - vulnerable to vol crush', exposure=[Instrument(name='Physical_Nikkei_Stocks', mtm_value=100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], hedge=[Instrument(name='Short_Nikkei_Futures', mtm_value=-100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Long_OTM_Puts', mtm_value=10000000000.0, eq_linear=-0.2, eq_quad=12.0, vol_linear=5.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Short_USDJPY_Futures', mtm_value=50000000000.0, eq_linear=0.0, eq_quad=0.0, vol_linear=0.0, fx_linear=-1.0, ir_dv01=0.0)], greeks=Greeks(delta=-2000000000.0, gamma=120000000000.0, vega=50000000000.0, fx=-50000000000.0, dv01=0.0))

RiskStats(eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015, corr_crisis=array([[ 1. , -0.8, -0.4, -0.5],
       [-0.8,  1. ,  0.3,  0.4],
       [-0.4,  0.3,  1. ,  0.2],
       [-0.5,  0.4,  0.2,  1. ]]), horizon_days=10, max_factor_sigma=3.0, max_joint_sigma=4.0)

ShockParams(eq_shock_sigma=np.float64(0.048460178361063554), vol_shock_sigma=np.float64(-2.1832299804363786), fx_shock_sigma=np.float64(1.6899697912331912), ir_shock_sigma=np.float64(1.0888151000457197e-06), joint_sigma=3.9738892912124992)

FactorMoves(eq_move=0.0018389344732675967, vol_move=-0.13807958788287616, fx_move=0.032064922303056846, ir_move=5.164703500392868e-09)

PnLSummary(net=PnL(total=-8510700477.443367, equity=-3474968.146716863, vol=-6903979394.143808, fx=-1603246115.1528423, rates=0.0), exposure=PnL(total=183893447.32675967, equity=183893447.32675967, vol=0.0, fx=0.0, rates=0.0), hedge=PnL(total=-8694593924.770126, equity=-187368415.47347653, vol=-6903979394.143808, fx=-1603246115.1528423, rates=0.0), exposure_pnls={'Physical_Nikkei_Stocks': PnL(total=183893447.32675967, equity=183893447.32675967, vol=-0.0, fx=0.0, rates=0.0)}, hedge_pnls={'Short_Nikkei_Futures': PnL(total=-183893447.32675967, equity=-183893447.32675967, vol=0.0, fx=-0.0, rates=0.0), 'Long_OTM_Puts': PnL(total=-6907454362.290525, equity=-3474968.1467168755, vol=-6903979394.143808, fx=0.0, rates=0.0), 'Short_USDJPY_Futures': PnL(total=-1603246115.1528423, equity=0.0, vol=-0.0, fx=-1603246115.1528423, rates=0.0)}, loss=8510700477.443367, notional=100000000000.0, loss_ratio=0.08510700477443367)

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
```

## Analysis

---
**Portfolio Risk Analysis Report**

**Scenario Overview:**
- **Scenario Name:** OTM Put Heavy
- **Description:** The portfolio is over-hedged with expensive deep out-of-the-money (OTM) puts, making it vulnerable to a volatility (vol) crush.
- **Portfolio Structure:**
  - **Exposure:** Physical Nikkei Stocks (¥100bn)
  - **Hedges:** 
    - Short Nikkei Futures (¥-100bn)
    - Long OTM Puts (¥10bn)
    - Short USDJPY Futures (¥50bn)

---

### 1. Portfolio Greeks and Sensitivities

| Greek      | Value              | Interpretation                                      |
|------------|--------------------|-----------------------------------------------------|
| Delta      | -2.0bn             | Slight net short equity exposure                    |
| Gamma      | 120.0bn            | Extremely high convexity to equity moves            |
| Vega       | 50.0bn             | Very high sensitivity to volatility changes         |
| FX         | -50.0bn            | Large short USDJPY exposure                        |
| DV01       | 0                  | No interest rate risk                              |

- **Key Risk:** The portfolio is highly convex (large gamma) and extremely long volatility (large vega), primarily due to the OTM put position.

---

### 2. Shock Scenario and Factor Moves

- **Equity Shock:** +0.18% (mild positive move)
- **Volatility Shock:** -13.8% (severe vol crush)
- **FX Shock (USDJPY):** +3.2% (JPY depreciation)
- **Interest Rate Shock:** Negligible

**Joint Sigma:** 3.97 (near max joint stress)

---

### 3. P&L Attribution

| Component                | P&L (¥)           | Key Drivers                                      |
|--------------------------|-------------------|--------------------------------------------------|
| **Total Net P&L**        | -8,510,700,477    | Substantial loss                                 |
| - Equity                 | -3,474,968        | Minor, due to near-flat net delta                |
| - Volatility             | -6,903,979,394    | Major loss from vol crush                        |
| - FX                     | -1,603,246,115    | Loss from short USDJPY as JPY weakens            |
| - Rates                  | 0                 | No interest rate exposure                        |

#### Instrument-Level P&L

- **Physical Nikkei Stocks:** +183,893,447 (gain from mild equity rise)
- **Short Nikkei Futures:** -183,893,447 (offsets stock gain; net delta near zero)
- **Long OTM Puts:** -6,907,454,362 (large loss, mainly from vega/vol crush)
- **Short USDJPY Futures:** -1,603,246,115 (loss from JPY depreciation)

---

### 4. Risk Factor Analysis

#### a. Equity Risk
- **Net Delta:** Near zero; equity moves have minimal impact.
- **Gamma:** High; large moves would introduce significant non-linearity, but current move is small.

#### b. Volatility Risk
- **Vega Exposure:** +50bn; extremely sensitive to implied volatility.
- **Volatility Shock:** -13.8% (vol crush) leads to a loss of ~¥6.9bn, confirming the portfolio’s vulnerability to falling volatility.

#### c. FX Risk
- **Short USDJPY Exposure:** -50bn notional; JPY depreciation (USDJPY up) results in a loss of ~¥1.6bn.

#### d. Interest Rate Risk
- **No material exposure.**

---

### 5. Scenario-Specific Observations

- **Over-hedging with OTM Puts:** The portfolio is over-hedged on the downside with deep OTM puts, which are expensive and highly sensitive to implied volatility. In a scenario where volatility collapses (as in this shock), these options lose significant value, resulting in large mark-to-market losses.
- **Hedge Inefficiency:** The short futures position offsets the physical equity exposure, leaving the portfolio with minimal net delta but high convexity and vega.
- **FX Hedge:** The short USDJPY futures position introduces additional risk, which materializes as a loss when the JPY weakens.

---

### 6. Loss Metrics

- **Total Loss:** ¥8.51bn (8.5% of notional)
- **Loss Ratio:** 8.51%
- **Primary Loss Driver:** Volatility crush on OTM puts.

---

### 7. Risk Concentrations and Vulnerabilities

- **Volatility Risk Concentration:** The portfolio is highly exposed to volatility declines due to the large vega from OTM puts.
- **Convexity Risk:** High gamma could lead to large P&L swings in the event of significant equity moves, though this is not realized in the current scenario.
- **FX Risk:** Material exposure to USDJPY, with losses realized in this scenario.

---

### 8. Potential Outcomes and Recommendations

- **If Volatility Rebounds:** The portfolio could recover losses due to high vega, but this is contingent on implied volatility rising.
- **If Equity Moves Sharply:** High gamma could result in large gains or losses, depending on direction and magnitude.
- **If Volatility Continues to Fall:** Further losses are likely, especially if OTM puts continue to lose value.
- **Hedge Optimization:** Consider reducing OTM put exposure or replacing with less vega-sensitive hedges to mitigate vulnerability to vol crush.
- **FX Risk Management:** Reassess the necessity and sizing of the short USDJPY position to avoid further FX-driven losses.

---

**Summary:**  
The portfolio is structurally vulnerable to volatility declines due to excessive long vega from deep OTM puts. The current scenario, characterized by a severe vol crush and mild equity and FX moves, results in a significant loss, primarily driven by the collapse in implied volatility. The hedge structure is inefficient, with over-hedging on the downside and unnecessary FX risk. Immediate attention to vega and FX exposures is warranted to prevent further adverse outcomes.

## Review

quality_score: 0.45

While the analysis is thorough in its data grounding and provides a clear breakdown of the portfolio's exposures and P&L attribution, it falls short in causal depth and narrative flow. The explanation is heavily structured as a sequence of bullet points, tables, and checklist-style sections, which violates the requirement for connected prose and limits the score to a maximum of 0.50. More critically, the analysis describes "what happened"—noting the large vega exposure and the loss from a vol crush—but does not deeply explore the causal mechanism or the violated assumptions in the hedge design. It fails to articulate why the portfolio was constructed with such high vega, what implicit market regime or correlation assumptions were embedded, and how the scenario specifically invalidates those assumptions to turn the hedge into a loss driver. Thus, while factually accurate and specific, the analysis lacks the narrative and causal insight required for a higher score.
