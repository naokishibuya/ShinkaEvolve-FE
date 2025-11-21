# Default Scenario

**Score:** 0.35
**Difficulty Weight:** 0.85

## Scenario Description

```
Name: Default Scenario
Description: Standard Japanese institutional portfolio with realistic crisis correlations

Exposure instruments (portfolio you want to hedge):
  - Physical_Nikkei_Stocks: mtm=100000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01, JPY per 1bp move)

Hedge instruments (overlay intended to reduce risk):
  - Short_Nikkei_Futures: mtm=-80000000000 JPY, eq_lin=1.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Long_Nikkei_Puts: mtm=5000000000 JPY, eq_lin=-0.35 (equity delta), eq_quad=8.0 (equity convexity), vol_lin=4.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=0.0 (rate DV01)
  - Long_JGB_Futures: mtm=0 JPY, eq_lin=0.0 (equity delta), eq_quad=0.0 (equity convexity), vol_lin=0.0 (vol sensitivity), fx_lin=0.0 (FX sensitivity), ir_dv01=-1000000000.0 (rate DV01)
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
  Equity shock:         -0.09 σ
  Vol shock:            -0.12 σ
  FX shock (USDJPY):    +1.10 σ
  IR shock:             +3.00 σ
  Joint sigma:           3.62   (Mahalanobis distance)

FACTOR MOVES (After Volatility & √T Scaling)
--------------------------------------------------------------------------------
  Equity move:         -0.3324%
  Vol move:            -0.7460%
  FX move:             +2.0892%
  IR move:             +1.4230%

PORTFOLIO P&L (JPY Billions)
--------------------------------------------------------------------------------
  Net Total P&L:        -143.56 bn
    └─ Exposure P&L:      -0.33 bn
    └─ Hedge P&L:       -143.22 bn

  Net P&L by Factor:
    • Equity:             -0.06 bn
    • Vol:                -0.15 bn
    • FX:                 -1.04 bn
    • Rates:            -142.30 bn

  Loss:                  143.56 bn
  Loss Ratio:           143.56% (vs exposure notional)
```

## Prompt

```
You are a financial risk analyst. Given the following scenario and shock parameters,
provide a detailed analysis of the potential impacts on the portfolio.

-----
Scenario(name='Default Scenario', description='Standard Japanese institutional portfolio with realistic crisis correlations', exposure=[Instrument(name='Physical_Nikkei_Stocks', mtm_value=100000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0)], hedge=[Instrument(name='Short_Nikkei_Futures', mtm_value=-80000000000.0, eq_linear=1.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Long_Nikkei_Puts', mtm_value=5000000000.0, eq_linear=-0.35, eq_quad=8.0, vol_linear=4.0, fx_linear=0.0, ir_dv01=0.0), Instrument(name='Long_JGB_Futures', mtm_value=0.0, eq_linear=0.0, eq_quad=0.0, vol_linear=0.0, fx_linear=0.0, ir_dv01=-1000000000.0), Instrument(name='Short_USDJPY_Futures', mtm_value=50000000000.0, eq_linear=0.0, eq_quad=0.0, vol_linear=0.0, fx_linear=-1.0, ir_dv01=0.0)], greeks=Greeks(delta=18250000000.0, gamma=40000000000.0, vega=20000000000.0, fx=-50000000000.0, dv01=-1000000000.0))

RiskStats(eq_vol=0.012, vol_of_vol=0.02, fx_vol=0.006, ir_vol=0.0015, corr_crisis=array([[ 1. , -0.8, -0.4, -0.5],
       [-0.8,  1. ,  0.3,  0.4],
       [-0.4,  0.3,  1. ,  0.2],
       [-0.5,  0.4,  0.2,  1. ]]), horizon_days=10, max_factor_sigma=3.0, max_joint_sigma=4.0)

ShockParams(eq_shock_sigma=np.float64(-0.08759152204502266), vol_shock_sigma=np.float64(-0.11795476156222122), fx_shock_sigma=np.float64(1.1011238619930053), ir_shock_sigma=np.float64(3.0), joint_sigma=3.617522463759586)

FactorMoves(eq_move=-0.0033238645605974558, vol_move=-0.007460114147974001, fx_move=0.020892356339152863, ir_move=0.01423024947075771)

PnLSummary(net=PnL(total=-143556754374.21277, equity=-60439566.71855962, vol=-149202282.95948002, fx=-1044617816.9576432, rates=-142302494707.5771), exposure=PnL(total=-332386456.05974555, equity=-332386456.05974555, vol=0.0, fx=0.0, rates=0.0), hedge=PnL(total=-143224367918.153, equity=271946889.3411859, vol=-149202282.95948002, fx=-1044617816.9576432, rates=-142302494707.5771), exposure_pnls={'Physical_Nikkei_Stocks': PnL(total=-332386456.05974555, equity=-332386456.05974555, vol=-0.0, fx=0.0, rates=0.0)}, hedge_pnls={'Short_Nikkei_Futures': PnL(total=265909164.84779647, equity=265909164.84779647, vol=0.0, fx=-0.0, rates=0.0), 'Long_Nikkei_Puts': PnL(total=-143164558.46609056, equity=6037724.493389462, vol=-149202282.95948002, fx=0.0, rates=0.0), 'Long_JGB_Futures': PnL(total=-142302494707.5771, equity=0.0, vol=-0.0, fx=0.0, rates=-142302494707.5771), 'Short_USDJPY_Futures': PnL(total=-1044617816.9576432, equity=0.0, vol=-0.0, fx=-1044617816.9576432, rates=0.0)}, loss=143556754374.21277, notional=100000000000.0, loss_ratio=1.4355675437421276)

-----
Based on the above information, analyze the risks and potential outcomes for the portfolio.
Provide your analysis in a clear and structured manner.
```

## Analysis

**Portfolio Risk Analysis Report**

**1. Portfolio Structure and Exposures**

- **Exposure:**  
  - Physical Nikkei Stocks: ¥100bn, fully exposed to equity risk (delta = 1.0).
- **Hedge Instruments:**  
  - Short Nikkei Futures: -¥80bn, equity delta hedge (delta = 1.0).
  - Long Nikkei Puts: ¥5bn, negative delta (-0.35), high convexity (gamma = 8.0), significant vega (4.0).
  - Long JGB Futures: No initial MTM, significant interest rate sensitivity (DV01 = -¥1bn).
  - Short USDJPY Futures: ¥50bn, FX delta hedge (fx_linear = -1.0).

**2. Scenario and Shock Parameters**

- **Scenario:**  
  - Standard Japanese institutional portfolio under crisis correlations.
- **Risk Factors:**  
  - Equity volatility: 1.2% daily.
  - Volatility of volatility: 2.0% daily.
  - FX volatility: 0.6% daily.
  - Interest rate volatility: 0.15% daily.
  - Crisis correlation matrix indicates strong negative equity-hedge correlation, moderate cross-asset correlations.
- **Shock Magnitudes:**  
  - Equity shock: -8.76σ (large negative move).
  - Volatility shock: -11.80σ (large negative move).
  - FX shock: +1.10σ (JPY depreciation).
  - Interest rate shock: +3.0σ (rates rise).
  - Joint shock: 3.62σ (multi-factor stress).

**3. Factor Moves (10-day Horizon)**

- Equity: -0.33% (Nikkei decline).
- Volatility: -0.75% (implied vol drop).
- FX: +2.09% (JPY depreciation).
- Interest Rates: +1.42% (rates rise).

**4. P&L Attribution**

- **Total Portfolio P&L:** -¥143.56bn (loss ratio: 1.44x notional).
- **By Risk Factor:**
  - Equity: -¥60.4m
  - Volatility: -¥149.2m
  - FX: -¥1.04bn
  - Rates: -¥142.3bn

- **By Position:**
  - **Exposure (Physical Nikkei Stocks):** -¥332.4m (equity loss).
  - **Hedges:**
    - Short Nikkei Futures: +¥265.9m (equity gain).
    - Long Nikkei Puts: -¥143.2m (small equity gain, large vol loss).
    - Long JGB Futures: -¥142.3bn (large rates loss).
    - Short USDJPY Futures: -¥1.04bn (FX loss).

**5. Risk Analysis**

- **Equity Risk:**  
  - Net equity delta is positive (delta = ¥18.25bn), but the equity move is relatively mild (-0.33%). The physical stock loss is partially offset by the short futures and puts, resulting in a small net equity loss.
- **Volatility Risk:**  
  - The portfolio is long vega (vega = ¥20bn), but implied volatility falls sharply (-0.75%), resulting in a significant volatility loss, primarily on the long put position.
- **FX Risk:**  
  - The portfolio is short USDJPY (fx = -¥50bn). JPY depreciates by 2.09%, resulting in a loss on the short USDJPY futures.
- **Interest Rate Risk:**  
  - The portfolio is short duration (DV01 = -¥1bn). Rates rise by 1.42%, resulting in a very large loss on the long JGB futures position.
- **Hedge Effectiveness:**  
  - Equity hedges (short futures, long puts) partially offset physical stock losses.
  - Volatility and rates hedges are ineffective or misaligned with the direction of the shocks, leading to large losses.
  - FX hedge is insufficient to offset the FX move.

**6. Stress and Correlation Effects**

- The crisis correlation matrix amplifies cross-asset moves, particularly between equities, rates, and FX. The joint shock magnitude (3.62σ) indicates a severe, multi-factor stress scenario.
- The largest loss driver is the interest rate exposure, which dominates the total P&L.

**7. Key Risk Concentrations and Vulnerabilities**

- **Interest Rate Exposure:**  
  - The portfolio is highly sensitive to rate increases due to the large negative DV01 on the long JGB futures. This position alone accounts for nearly the entire portfolio loss.
- **Volatility Exposure:**  
  - The portfolio is long vega, but the scenario features a sharp drop in implied volatility, resulting in significant losses on the long put options.
- **FX Exposure:**  
  - The short USDJPY position is exposed to JPY depreciation, which materializes in the scenario.
- **Equity Exposure:**  
  - Net equity risk is relatively well-hedged, with only a small net loss.

**8. Portfolio Resilience and Recommendations**

- The portfolio is not resilient to a crisis scenario featuring simultaneous rate increases, JPY depreciation, and volatility compression.
- The interest rate hedge is misaligned with the scenario direction; consider reducing or reversing the JGB futures exposure.
- Volatility exposure should be reviewed, as long vega positions are vulnerable to volatility compression in crisis unwind scenarios.
- FX hedges should be recalibrated to better match the portfolio’s net currency exposure.
- Overall, the portfolio requires rebalancing to reduce concentration risk in rates and volatility, and to improve hedge effectiveness under crisis correlations.

**Conclusion**

The portfolio suffers catastrophic losses under the specified crisis scenario, primarily due to excessive interest rate and volatility risk. Equity risk is largely hedged, but cross-asset correlations and misaligned hedges in rates and volatility result in a loss exceeding the initial notional. Immediate risk mitigation actions are required to address these vulnerabilities.

## Review

quality_score: 0.35

While the analysis is written in prose and references specific numbers from the quantitative summary, it primarily describes what happened rather than why it happened. The explanation lists exposures, shock magnitudes, and resulting P&L impacts, but it does not trace the causal chain or identify the implicit assumptions in the hedge design that were violated by the scenario. There is no discussion of why the long JGB futures position was held as a hedge, what risk it was intended to offset, or how the scenario's rate shock specifically turned this hedge into a catastrophic loss driver. The analysis lacks structural insight into the hedge philosophy and fails to articulate the mechanism by which the scenario exploited the portfolio's vulnerabilities.
