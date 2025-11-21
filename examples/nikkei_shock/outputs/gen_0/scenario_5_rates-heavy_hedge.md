# Rates-Heavy Hedge

**Score:** 0.40
**Difficulty Weight:** 0.80

## Scenario Description

```
Name: Rates-Heavy Hedge
Description: Large JGB DV01 hedge that assumes yields fall in crises – vulnerable when yields spike instead

Exposure instruments (portfolio you want to hedge):
  - Physical_Nikkei_Stocks: mtm=100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01, JPY per 1bp move)

Hedge instruments (overlay intended to reduce risk):
  - Short_Nikkei_Futures: mtm=-60000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Long_Nikkei_Puts: mtm=2000000000 JPY, eq_lin=-0.3 (equity delta), eq_quad=6.0 (equity convexity), vol_lin=3.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Long_JGB_Futures: mtm=0 JPY, eq_lin=0.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=-120000000.0 (rate DV01)

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
  Equity shock:         -1.85 σ
  Vol shock:            -0.03 σ
  FX shock (USDJPY):    +0.23 σ
  IR shock:             +3.00 σ
  Joint sigma:           4.00   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         -7.0378%
  Vol move:            -0.2178%
  FX move:             +0.4285%
  IR move:             +1.4230%

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:         -19.83 bn
    └─ Exposure P&L:      -7.04 bn
    └─ Hedge P&L:        -12.79 bn

  Net P&L by Factor:
    • Equity:             -2.74 bn
    • Vol:                -0.01 bn
    • FX:                 +0.00 bn
    • Rates:             -17.08 bn

  Loss:                   19.83 bn
  Loss Ratio:            19.83% (vs exposure notional)
```

## Prompt

```
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
Scenario(name='Rates-Heavy Hedge', description='Large JGB DV01 hedge that assumes yields fall in crises – vulnerable when yields spike instead', exposure=[Instrument(name='Physical_Nikkei_Stocks', mtm_value=100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], hedge=[Instrument(name='Short_Nikkei_Futures', mtm_value=-60000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Long_Nikkei_Puts', mtm_value=2000000000.0, eq_linear=-0.3, eq_quad=6.0, vol_linear=3.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Long_JGB_Futures', mtm_value=0.0, eq_linear=0.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=-120000000.0)], greeks=Greeks(delta=39400000000.0, gamma=12000000000.0, vega=6000000000.0, fx=0.0, dv01=-120000000.0))

RiskStats(eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015, corr_crisis=array([[ 1. , -0.8, -0.4, -0.5],
       [-0.8,  1. ,  0.3,  0.4],
       [-0.4,  0.3,  1. ,  0.2],
       [-0.5,  0.4,  0.2,  1. ]]), horizon_days=10, max_factor_sigma=3.0, max_joint_sigma=4.0)

ShockParams(eq_shock_sigma=np.float64(-1.8546358049462317), vol_shock_sigma=np.float64(-0.034440930765254), fx_shock_sigma=np.float64(0.2258227085014267), ir_shock_sigma=np.float64(3.0000452781138893), joint_sigma=3.9999717055304136)

FactorMoves(eq_move=-0.07037848048475843, vol_move=-0.0021782357190873714, fx_move=0.004284684637516666, ir_move=0.014230464243709778)

PnLSummary(net=PnL(total=-19832819854.773678, equity=-2743193348.0074215, vol=-13069414.314524228, fx=0.0, rates=-17076557092.451733), exposure=PnL(total=-7037848048.475843, equity=-7037848048.475843, vol=0.0, fx=0.0, rates=0.0), hedge=PnL(total=-12794971806.297834, equity=4294654700.468422, vol=-13069414.314524228, fx=0.0, rates=-17076557092.451733), exposure_pnls={'Physical_Nikkei_Stocks': PnL(total=-7037848048.475843, equity=-7037848048.475843, vol=-0.0, fx=0.0, rates=0.0)}, hedge_pnls={'Short_Nikkei_Futures': PnL(total=4222708829.085506, equity=4222708829.085506, vol=0.0, fx=-0.0, rates=0.0), 'Long_Nikkei_Puts': PnL(total=58876457.068391986, equity=71945871.38291621, vol=-13069414.314524228, fx=0.0, rates=0.0), 'Long_JGB_Futures': PnL(total=-17076557092.451733, equity=0.0, vol=-0.0, fx=0.0, rates=-17076557092.451733)}, loss=19832819854.773678, notional=100000000000.0, loss_ratio=0.19832819854773678)

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
```

## Analysis

**Financial Risk Analysis Report: Rates-Heavy Hedge Scenario**

---

### 1. Scenario Overview

**Scenario Name:** Rates-Heavy Hedge  
**Description:** The portfolio is structured with a significant Japanese Government Bond (JGB) DV01 hedge, predicated on the assumption that yields fall during crises. This structure is exposed to significant risk if yields rise instead.

---

### 2. Portfolio Composition

#### 2.1. Exposure
- **Physical Nikkei Stocks:**  
  - Mark-to-Market (MTM) Value: ¥100,000,000,000  
  - Equity Sensitivity (Delta): 1.0  
  - No direct interest rate (IR), volatility, or FX sensitivity.

#### 2.2. Hedge Instruments
- **Short Nikkei Futures:**  
  - MTM Value: -¥60,000,000,000  
  - Equity Sensitivity (Delta): 1.0  
  - No IR, volatility, or FX sensitivity.
- **Long Nikkei Puts:**  
  - MTM Value: ¥2,000,000,000  
  - Equity Sensitivity (Delta): -0.3  
  - Equity Convexity (Gamma): 6.0  
  - Volatility Sensitivity (Vega): 3.0  
  - No IR or FX sensitivity.
- **Long JGB Futures:**  
  - MTM Value: ¥0  
  - Interest Rate DV01: -¥120,000,000  
  - No equity, volatility, or FX sensitivity.

---

### 3. Risk Factor Shocks

#### 3.1. Shock Parameters
- **Equity Shock:** -1.85σ (corresponds to a -7.04% move in Nikkei)
- **Volatility Shock:** -0.03σ (corresponds to a -0.22% move in implied vol)
- **FX Shock:** +0.23σ (corresponds to a +0.43% move in FX)
- **Interest Rate Shock:** +3.00σ (corresponds to a +1.42% move in JGB yields)
- **Joint Sigma:** 4.00σ (multi-factor stress)

#### 3.2. Correlation Matrix (Crisis)
- Strong negative correlation between equity and rates (-0.8)
- Moderate negative correlation between equity and volatility (-0.4)
- Moderate negative correlation between equity and FX (-0.5)
- Positive correlations among other factors

---

### 4. Portfolio Sensitivities (Greeks)

- **Delta (Equity):** ¥39,400,000,000
- **Gamma (Equity):** ¥12,000,000,000
- **Vega (Volatility):** ¥6,000,000,000
- **DV01 (Interest Rate):** -¥120,000,000

---

### 5. P&L Attribution

#### 5.1. Total Portfolio P&L (10-day Horizon)
- **Net Loss:** -¥19,832,819,854.77  
- **Loss Ratio:** 19.83% of notional

#### 5.2. P&L Breakdown
| Component                | Total P&L (¥)         | Equity (¥)         | Volatility (¥)     | FX (¥) | Rates (¥)           |
|--------------------------|-----------------------|--------------------|--------------------|--------|---------------------|
| **Exposure**             | -7,037,848,048.48     | -7,037,848,048.48  | 0.0                | 0.0    | 0.0                 |
| **Hedge**                | -12,794,971,806.30    | 4,294,654,700.47   | -13,069,414.31     | 0.0    | -17,076,557,092.45  |
| **Physical Nikkei Stocks** | -7,037,848,048.48   | -7,037,848,048.48  | 0.0                | 0.0    | 0.0                 |
| **Short Nikkei Futures** | 4,222,708,829.09      | 4,222,708,829.09   | 0.0                | 0.0    | 0.0                 |
| **Long Nikkei Puts**     | 58,876,457.07         | 71,945,871.38      | -13,069,414.31     | 0.0    | 0.0                 |
| **Long JGB Futures**     | -17,076,557,092.45    | 0.0                | 0.0                | 0.0    | -17,076,557,092.45  |

---

### 6. Risk Analysis

#### 6.1. Equity Risk
- The portfolio is net long Nikkei exposure, partially hedged by short futures and long puts.
- The equity shock (-7.04%) results in a significant loss on the physical stocks (-¥7.04bn), partially offset by gains on short futures (+¥4.22bn) and long puts (+¥71.95m).
- The net equity P&L is negative, indicating the hedge is not fully effective against large equity drawdowns.

#### 6.2. Volatility Risk
- The long put position provides positive vega, but the realized volatility move is negative (-0.22%), resulting in a small loss (-¥13.07m) from volatility exposure.

#### 6.3. Interest Rate Risk
- The portfolio is long JGB futures with a large negative DV01 (-¥120m per bp).
- The interest rate shock is a +1.42% (142bp) increase in yields, resulting in a substantial loss on the JGB futures (-¥17.08bn).
- This loss dominates the total portfolio P&L, confirming the scenario's vulnerability to yield spikes.

#### 6.4. FX Risk
- No material FX exposure in the portfolio; FX moves have negligible impact.

#### 6.5. Correlation and Joint Stress
- The scenario reflects a crisis regime with high negative correlation between equity and rates.
- The joint sigma shock (4σ) amplifies the impact across all risk factors, leading to outsized losses.

---

### 7. Key Risk Concentrations

- **Interest Rate Risk:** The largest risk driver is the long JGB futures position. The negative DV01, combined with a large upward shock in yields, results in catastrophic losses.
- **Hedge Effectiveness:** The equity hedge (short futures, long puts) provides partial mitigation but is insufficient to offset the equity and especially the rates-driven losses.
- **Scenario Dependency:** The portfolio is constructed for a crisis where yields fall. In the opposite scenario (yields rise), the hedge structure fails, exposing the portfolio to significant tail risk.

---

### 8. Potential Outcomes and Recommendations

#### 8.1. Outcomes
- Under the specified shock, the portfolio suffers a loss of ¥19.83bn (19.8% of notional), primarily due to the rates move.
- The equity hedge reduces, but does not eliminate, losses from an equity drawdown.
- The portfolio is highly vulnerable to scenarios where both equities fall and yields rise, a regime shift from the assumed crisis correlation.

#### 8.2. Recommendations
- **Reduce Rates Exposure:** Rebalance or reduce the long JGB futures position to lower DV01 sensitivity.
- **Diversify Hedges:** Consider alternative hedging strategies that are robust to both falling and rising yield environments.
- **Stress Testing:** Regularly perform multi-factor stress tests, including adverse rate shocks, to monitor and manage tail risks.
- **Dynamic Hedging:** Implement dynamic risk management to adjust hedges as market regimes shift, particularly in relation to rates-equity correlation.

---

**Conclusion:**  
The portfolio exhibits significant tail risk due to concentrated interest rate exposure. The current hedge structure is inadequate in scenarios where yields rise sharply, leading to large potential losses. Immediate risk mitigation actions are warranted to address the identified vulnerabilities.

## Review

quality_score: 0.40

While the analysis is thorough in its data presentation and describes the portfolio's composition, risk exposures, and P&L attribution, it falls short in causal depth and narrative flow. The explanation is heavily structured as a series of sectioned bullet points and tables, lacking the connected prose and narrative required for a higher score. Most critically, it does not clearly articulate the causal mechanism: it fails to explain the implicit assumption in the hedge design (that yields fall when equities fall), how this scenario violates that assumption (yields rise during an equity selloff), and how this turns the rate hedge into a loss driver. The analysis describes "what happened" but not "why" in a mechanistic sense, and thus does not provide the deep structural insight or narrative flow demanded by the higher scoring bands.
