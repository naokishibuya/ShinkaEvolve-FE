# Short Vol Seller

**Score:** 0.65
**Difficulty Weight:** 0.90

## Scenario Description

```
Name: Short Vol Seller
Description: Delta-hedged short-vol portfolio – profits in calm markets, vulnerable to vol spikes and large moves

Exposure instruments (portfolio you want to hedge):
  - Physical_Nikkei_Stocks: mtm=100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01, JPY per 1bp move)

Hedge instruments (overlay intended to reduce risk):
  - Short_Nikkei_Futures: mtm=-100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Short_Vol_Position: mtm=10000000000 JPY, eq_lin=0.0 (equity delta), eq_quad=-15.0 (equity convexity), vol_lin=-10.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)

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
  Equity shock:         +1.06 σ
  Vol shock:            +1.41 σ
  FX shock (USDJPY):    +0.00 σ
  IR shock:             +0.00 σ
  Joint sigma:           4.00   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         +4.0330%
  Vol move:            +8.8883%
  FX move:             +0.0000%
  IR move:             +0.0000%

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:          -9.01 bn
    └─ Exposure P&L:      +4.03 bn
    └─ Hedge P&L:        -13.04 bn

  Net P&L by Factor:
    • Equity:             -0.12 bn
    • Vol:                -8.89 bn
    • FX:                 +0.00 bn
    • Rates:              +0.00 bn

  Loss:                    9.01 bn
  Loss Ratio:             9.01% (vs exposure notional)
```

## Prompt

```
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
Scenario(name='Short Vol Seller', description='Delta-hedged short-vol portfolio – profits in calm markets, vulnerable to vol spikes and large moves', exposure=[Instrument(name='Physical_Nikkei_Stocks', mtm_value=100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], hedge=[Instrument(name='Short_Nikkei_Futures', mtm_value=-100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Short_Vol_Position', mtm_value=10000000000.0, eq_linear=0.0, eq_quad=-15.0, vol_linear=-10.0, fx_linear=0.0, ir_dv01=0.0)], greeks=Greeks(delta=0.0, gamma=-150000000000.0, vega=-100000000000.0, fx=0.0, dv01=0.0))

RiskStats(eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015, corr_crisis=array([[ 1. , -0.8, -0.4, -0.5],
       [-0.8,  1. ,  0.3,  0.4],
       [-0.4,  0.3,  1. ,  0.2],
       [-0.5,  0.4,  0.2,  1. ]]), horizon_days=10, max_factor_sigma=3.0, max_joint_sigma=4.0)

ShockParams(eq_shock_sigma=np.float64(1.062791821111483), vol_shock_sigma=np.float64(1.405369837939751), fx_shock_sigma=np.float64(4.153599662745852e-06), ir_shock_sigma=np.float64(4.16893887993223e-06), joint_sigma=3.9999790654166887)

FactorMoves(eq_move=0.040330113999726136, vol_move=0.08888339285582661, fx_move=7.880901253670474e-08, ir_move=1.9775013429925615e-08)

PnLSummary(net=PnL(total=-9010328142.72498, equity=-121988857.14231777, vol=-8888339285.58266, fx=0.0, rates=0.0), exposure=PnL(total=4033011399.972614, equity=4033011399.972614, vol=0.0, fx=0.0, rates=0.0), hedge=PnL(total=-13043339542.697594, equity=-4155000257.1149316, vol=-8888339285.58266, fx=0.0, rates=0.0), exposure_pnls={'Physical_Nikkei_Stocks': PnL(total=4033011399.972614, equity=4033011399.972614, vol=0.0, fx=0.0, rates=0.0)}, hedge_pnls={'Short_Nikkei_Futures': PnL(total=-4033011399.972614, equity=-4033011399.972614, vol=-0.0, fx=-0.0, rates=0.0), 'Short_Vol_Position': PnL(total=-9010328142.72498, equity=-121988857.14231797, vol=-8888339285.58266, fx=0.0, rates=0.0)}, loss=9010328142.72498, notional=100000000000.0, loss_ratio=0.0901032814272498)

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
```

## Analysis

---
**Financial Risk Analysis Report**

**Portfolio Scenario:**  
*Short Vol Seller*  
Delta-hedged short-volatility portfolio, structured to profit in stable markets but exposed to volatility spikes and large market moves.

---

### 1. Portfolio Structure and Exposures

**Instruments:**
- **Physical Nikkei Stocks:** Long exposure, MTM value ¥100bn, delta = +1.0.
- **Short Nikkei Futures:** Short exposure, MTM value -¥100bn, delta = +1.0.
- **Short Vol Position:** Net short volatility, MTM value ¥10bn, gamma = -15.0, vega = -10.0.

**Net Greeks:**
- **Delta:** 0.0 (delta-neutral)
- **Gamma:** -¥150bn (significant short gamma)
- **Vega:** -¥100bn (significant short vega)
- **FX, IR:** No material exposure

---

### 2. Risk Factor Shocks and Market Moves

**Shock Parameters (10-day horizon):**
- **Equity Shock (σ):** 1.06, **Move:** +4.03%
- **Volatility Shock (σ):** 1.41, **Move:** +8.89 vol points
- **FX, IR Shocks:** Negligible

**Correlation Matrix (Crisis):**
- High negative correlation between equity and volatility (-0.8), indicating that equity sell-offs are likely to coincide with volatility spikes.

---

### 3. P&L Attribution

**Total Net P&L:** -¥9.01bn  
- **Equity P&L:** -¥122mn  
- **Volatility P&L:** -¥8.89bn  
- **FX, Rates P&L:** 0

**Component P&L:**
- **Physical Nikkei Stocks:** +¥4.03bn (equity rally)
- **Short Nikkei Futures:** -¥4.03bn (offsets equity move)
- **Short Vol Position:** -¥9.01bn (driven by negative gamma and vega)

**Loss Ratio:** 9.0% of notional

---

### 4. Risk Analysis

#### a. **Delta and Equity Risk**
- The portfolio is delta-neutral; equity moves are largely hedged between physical stocks and short futures.
- Equity P&L is minimal (-¥122mn), confirming effective delta hedging.

#### b. **Gamma and Convexity Risk**
- Substantial short gamma (-¥150bn): Portfolio loses money on large directional moves in the underlying, regardless of direction.
- The realized equity move (+4.03%) results in a negative gamma P&L, as the portfolio is structurally short convexity.

#### c. **Vega and Volatility Risk**
- Large short vega (-¥100bn): Portfolio is highly sensitive to increases in implied volatility.
- The observed volatility spike (+8.89 vol points) results in a significant negative vega P&L (-¥8.89bn).
- The negative correlation between equity and volatility amplifies losses during market stress, as both gamma and vega exposures are adversely affected.

#### d. **Tail Risk and Stress Scenario**
- The joint shock scenario (4σ move) represents a severe but plausible stress event.
- The portfolio suffers a loss of ¥9.01bn, or 9% of notional, primarily due to the short volatility position.
- The loss is concentrated in the short vol position, which is exposed to both large moves (gamma) and volatility spikes (vega).

#### e. **Liquidity and Margin Risk**
- A loss of this magnitude may trigger margin calls or forced liquidation, especially if volatility remains elevated or increases further.
- The portfolio’s risk profile is highly nonlinear; losses can accelerate rapidly in more extreme scenarios.

---

### 5. Key Risk Drivers

- **Short Gamma:** Exposes the portfolio to large losses on outsized market moves, regardless of direction.
- **Short Vega:** Exposes the portfolio to volatility spikes, which are likely during equity sell-offs or market stress.
- **Correlation Structure:** Negative equity-volatility correlation increases risk during crisis periods.
- **Limited Diversification:** Risk is concentrated in a single market (Nikkei) and a single risk factor (volatility).

---

### 6. Potential Outcomes and Recommendations

- **In Calm Markets:** Portfolio generates steady profits from short volatility premium.
- **In Volatile/Stress Markets:** Portfolio is vulnerable to rapid, nonlinear losses due to short gamma and vega exposures.
- **Current Scenario:** Realized stress event results in a material loss (9% of notional), primarily from the short vol position.

**Risk Mitigation:**
- Reduce short gamma and vega exposures, particularly in environments with rising volatility or increased tail risk.
- Consider dynamic hedging or purchasing out-of-the-money options to limit tail risk.
- Monitor market volatility and correlation regimes closely; adjust exposures proactively in response to changing risk conditions.

---

**Conclusion:**  
The portfolio is highly exposed to volatility and convexity risk, with losses accelerating in stress scenarios characterized by large market moves and volatility spikes. While delta risk is effectively hedged, the short vol strategy is vulnerable to tail events, as demonstrated by the significant loss under the given shock scenario. Active risk management and hedging of nonlinear exposures are critical to mitigate further downside.

## Review

quality_score: 0.65

The analysis is written in clear, connected prose and accurately references the quantitative data, including the specific equity and volatility shocks and the resulting P&L breakdown. It explains the portfolio's delta-neutral construction and highlights the large short gamma and vega exposures, correctly attributing the loss to the volatility spike and the large move in equities. However, the explanation falls short of deeply exploring the causal chain and the implicit assumptions in the hedge design. It describes the risk factors and their effects but does not fully articulate why the hedge overlay—particularly the short vol position—was constructed under assumptions that fail in this scenario, nor does it trace how the negative equity-volatility correlation specifically undermines the intended risk reduction. The analysis is thorough and accurate but lacks the deeper structural insight and critique of the hedge philosophy that would elevate it to a higher score.
