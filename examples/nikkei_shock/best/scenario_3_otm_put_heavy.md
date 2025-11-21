# OTM Put Heavy

**Score:** 0.93
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
You are a senior financial risk analyst tasked with producing a comprehensive hedge-weakness analysis
for the following portfolio scenario under an optimized worst-case market shock.

---
SCENARIO OVERVIEW:

Name: OTM Put Heavy
Description: Over-hedged with expensive deep OTM puts - vulnerable to vol crush

EXPOSURE INSTRUMENTS:
- Physical_Nikkei_Stocks (MTM: ¥100,000,000,000, Eq Delta: 1.000, Eq Gamma: 0.000, Vega: 0.000, FX: 0.000, DV01: 0.000)

HEDGE INSTRUMENTS:
- Short_Nikkei_Futures (MTM: ¥-100,000,000,000, Eq Delta: 1.000, Eq Gamma: 0.000, Vega: 0.000, FX: 0.000, DV01: 0.000)
- Long_OTM_Puts (MTM: ¥10,000,000,000, Eq Delta: -0.200, Eq Gamma: 12.000, Vega: 5.000, FX: 0.000, DV01: 0.000)
- Short_USDJPY_Futures (MTM: ¥50,000,000,000, Eq Delta: 0.000, Eq Gamma: 0.000, Vega: 0.000, FX: -1.000, DV01: 0.000)

PORTFOLIO NET GREEKS:
Delta: ¥-2,000,000,000, Gamma: ¥120,000,000,000, Vega: ¥50,000,000,000, FX: ¥-50,000,000,000, DV01: ¥0

RISK STATS (Crisis Regime):
- Horizon Days: 10
- Daily 1σ Volatilities:
  Equity: 1.200%, Volatility: 2.000%, FX: 0.600%, Interest Rates: 0.150%
- Crisis Correlation Matrix (rows=Equity, Vol, FX, IR):
Equity      : 1.00  -0.80  -0.40  -0.50
Volatility  : -0.80  1.00  0.30  0.40
FX          : -0.40  0.30  1.00  0.20
Interest Rates: -0.50  0.40  0.20  1.00
- Max Factor Sigma: 3.00
- Max Joint Sigma: 4.00

SHOCK PARAMETERS (Pre-scaling σ units):
- Equity Shock: +0.048σ
- Volatility Shock: -2.183σ
- FX Shock: +1.690σ
- Interest Rate Shock: +0.000σ
- Joint Shock Sigma (Mahalanobis distance): 3.974

ACTUAL FACTOR MOVES (Scaled for horizon and vol):
Equity move: 0.184%, Vol move: -13.808%, FX move: 3.206%, IR move: 0.000%

PNL SUMMARY:
- Net Portfolio P&L: Total: ¥-8,510,700,477, Equity: ¥-3,474,968, Vol: ¥-6,903,979,394, FX: ¥-1,603,246,115, Rates: ¥0
- Exposure-Only P&L:
  Physical_Nikkei_Stocks: Total: ¥183,893,447, Equity: ¥183,893,447, Vol: ¥-0, FX: ¥0, Rates: ¥0
- Hedge-Only P&L:
  Short_Nikkei_Futures: Total: ¥-183,893,447, Equity: ¥-183,893,447, Vol: ¥0, FX: ¥-0, Rates: ¥0
  Long_OTM_Puts: Total: ¥-6,907,454,362, Equity: ¥-3,474,968, Vol: ¥-6,903,979,394, FX: ¥0, Rates: ¥0
  Short_USDJPY_Futures: Total: ¥-1,603,246,115, Equity: ¥0, Vol: ¥-0, FX: ¥-1,603,246,115, Rates: ¥0
- Loss: ¥8,510,700,477 (Loss ratio: 8.511% of notional ¥100,000,000,000)

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
```

## Analysis

---
**HEDGE-WEAKNESS ANALYSIS: OTM PUT HEAVY PORTFOLIO**

---

### 1. Portfolio Exposures

**Instrument Exposures and MTM Values:**

- **Physical_Nikkei_Stocks:** ¥100,000,000,000 (Exposure Instrument)
- **Short_Nikkei_Futures:** ¥-100,000,000,000 (Hedge Instrument)
- **Long_OTM_Puts:** ¥10,000,000,000 (Hedge Instrument)
- **Short_USDJPY_Futures:** ¥50,000,000,000 (Hedge Instrument)

**Net Portfolio Greeks:**

- **Delta:** ¥-2,000,000,000  
  *Slight net short equity exposure; nearly delta-neutral but with a small net short bias.*
- **Gamma:** ¥120,000,000,000  
  *Significant positive convexity; portfolio profits from large moves in Nikkei, especially downward due to put positioning.*
- **Vega:** ¥50,000,000,000  
  *Substantial positive vega; portfolio is highly sensitive to changes in implied volatility, especially through long OTM puts.*
- **FX:** ¥-50,000,000,000  
  *Short USDJPY exposure; portfolio loses if JPY strengthens (USDJPY falls).*
- **DV01:** ¥0  
  *No direct interest rate sensitivity.*

**Exposure vs. Hedge Instruments:**

- **Physical_Nikkei_Stocks**: Pure long equity exposure, no convexity or volatility sensitivity.
- **Short_Nikkei_Futures**: Offsets equity delta, no convexity or vega.
- **Long_OTM_Puts**: Provides negative delta, high positive gamma, and high positive vega; intended to protect against large equity declines and volatility spikes.
- **Short_USDJPY_Futures**: Provides FX hedge against JPY appreciation.

---

### 2. Hedge Intent

**Short_Nikkei_Futures:**  
Intended to neutralize the equity delta from the physical stock position, reducing directional equity risk. Under normal conditions, this hedge should offset small moves in the Nikkei, keeping the portfolio close to delta-neutral.

**Long_OTM_Puts:**  
Designed to provide tail risk protection against large equity drawdowns and volatility spikes. The deep OTM nature means these options are cheap but only pay off in extreme downside scenarios. The high vega exposure is a byproduct, making the portfolio sensitive to changes in implied volatility.

**Short_USDJPY_Futures:**  
Intended to hedge currency risk from JPY exposure in the Nikkei stocks. Aims to offset losses from JPY appreciation (USDJPY decline), which would otherwise erode the value of Japanese assets for a non-JPY base investor.

---

### 3. Shock Scenario Analysis

**Shock Directions and Magnitudes:**

- **Equity:** +0.184% (mild positive move)
- **Volatility:** -13.808% (severe vol crush)
- **FX:** +3.206% (USDJPY rally; JPY weakens)
- **Interest Rates:** 0.000% (no move)

**Harmful Shock Characteristics:**

- **Volatility Shock:** The -13.808% move (corresponding to -2.183σ) is a deep vol crush, severely reducing the value of long OTM puts, which are highly vega-sensitive. This is the primary loss driver.
- **Equity Shock:** The small positive move (+0.184%) is insufficient to trigger meaningful intrinsic value in the OTM puts, rendering their gamma protection ineffective.
- **FX Shock:** The +3.206% move (USDJPY up) is adverse for the short USDJPY futures, resulting in a significant FX loss.

**Crisis Volatilities and Maximum Sigmas:**

- The joint Mahalanobis sigma is 3.974, close to the maximum allowed (4.00), indicating a highly severe but plausible crisis scenario.
- The individual factor shocks are within the crisis regime, but the joint move is near the tail of the allowed risk envelope.

**Crisis Correlation Matrix Implications:**

- **Equity-Volatility:** Strong negative correlation (-0.80). In typical crises, equity down is paired with vol up, benefiting long puts. Here, the scenario is reversed: equity is flat/up, vol collapses, causing maximum pain for long vega positions.
- **Equity-FX:** Moderate negative correlation (-0.40). The scenario delivers a positive equity move with a negative FX move (USDJPY up), compounding losses.
- **Volatility-FX:** Positive correlation (0.30). The scenario delivers both vol down and USDJPY up, both adverse for the portfolio.

---

### 4. Loss Drivers and Hedge Breakdown

**Risk Factor Contributions:**

- **Volatility:** ¥-6,903,979,394 (dominant loss driver; 81% of total loss)
- **FX:** ¥-1,603,246,115 (19% of total loss)
- **Equity:** ¥-3,474,968 (negligible)
- **Rates:** ¥0

**Linear vs. Non-Linear Exposures:**

- **Delta (Linear):** Near-neutral; small net short, resulting in minimal equity P&L.
- **Gamma (Non-Linear):** High positive gamma, but ineffective as the equity move is too small to trigger convexity benefits.
- **Vega (Non-Linear):** Large positive vega; the vol crush directly translates to a massive loss on the long OTM puts.

**Hedge Failures and Structural Weaknesses:**

- **Long_OTM_Puts:**  
  - *Vega Exposure:* The puts are highly sensitive to implied volatility. The scenario’s vol crush (-13.808%) wipes out their value, resulting in a ¥-6.9bn loss.
  - *Gamma Ineffectiveness:* The small equity move (+0.184%) is insufficient to activate the gamma protection. The puts remain deep OTM, providing no offsetting gain.
  - *Structural Weakness:* Over-reliance on vega-heavy hedges exposes the portfolio to vol regime shifts, especially vol crushes that can occur in post-crisis or mean-reverting environments.
- **Short_USDJPY_Futures:**  
  - *FX Exposure:* The hedge is designed to protect against JPY appreciation. The scenario delivers JPY depreciation (USDJPY up), resulting in a ¥-1.6bn loss.
  - *Correlation Breakdown:* The expected negative correlation between equity and FX fails; both move adversely, compounding losses.
- **Short_Nikkei_Futures:**  
  - *Delta Hedge:* Performs as intended, offsetting the physical stock’s equity move. Net equity P&L is negligible.

**Hedges Worsening Losses:**

- The long OTM puts, intended as a tail hedge, become a source of loss due to their vega exposure in a vol crush scenario. Instead of mitigating risk, they amplify losses when volatility collapses without a corresponding equity selloff.

---

### 5. Structural and Scenario-Specific Insights

**Hedge Design Philosophy and Implicit Assumptions:**

- The portfolio construction assumes that crisis events will be characterized by equity drawdowns accompanied by volatility spikes (high negative equity-vol correlation).
- The heavy allocation to deep OTM puts reflects a belief in the efficacy of vega/gamma hedges for tail risk, neglecting scenarios where volatility collapses or where equity and vol decouple.

**Multi-Factor Interactions and Crisis Regime Behaviors:**

- The joint sigma of 3.974 demonstrates that the scenario is not just a sum of individual factor shocks but a rare, highly correlated event where multiple risk factors move in directions that are all adverse to the portfolio.
- The crisis correlation matrix shows that the scenario is a "correlation breakdown": equity does not fall, but volatility collapses, and FX moves against the hedge, all at once. This multi-factor co-movement amplifies losses beyond what would be expected from any single factor move.

**Breakdown of Typical Crisis Correlations:**

- The scenario exposes the risk of relying on historical crisis correlations. The negative equity-vol correlation fails; instead, vol collapses while equity is flat/up, rendering vega-heavy hedges not just ineffective but actively loss-generating.
- The positive correlation between vol and FX (0.30) means that a vol crush is likely to coincide with an adverse FX move, compounding losses on both the OTM puts and the FX hedge.

**Quantification of Joint Sigma Impact:**

- The joint sigma of 3.974 (near the maximum allowed 4.00) indicates a highly plausible but extreme event. The loss ratio of 8.511% of notional (¥8.5bn loss on ¥100bn notional) is a direct result of this rare but plausible multi-factor stress, far exceeding what would be expected from any single-factor shock.

**Scenario-Specific, Actionable Recommendations:**

- **Reduce Vega Concentration:**  
  - Rebalance the hedge structure to reduce reliance on long vega (OTM puts). Consider replacing a portion of the OTM puts with closer-to-the-money options or dynamic hedges (e.g., collars, put spreads) that provide convexity with less vega exposure.
- **Incorporate Vega-Neutral Structures:**  
  - Use option spreads (e.g., ratio put spreads, calendar spreads) to offset vega risk while retaining some downside convexity.
- **Diversify Tail Hedges:**  
  - Add instruments that benefit from equity drawdowns without being vega-dependent, such as dynamic short futures overlays or structured products with built-in downside protection.
- **FX Hedge Reassessment:**  
  - Re-examine the FX hedge sizing and directionality. Consider using options or more dynamic FX hedges that can adapt to regime shifts in equity/FX correlation.
- **Stress Testing for Correlation Breakdown:**  
  - Implement scenario analysis that explicitly tests for correlation breakdowns and vol crushes, not just traditional crisis regimes.
- **Limit Over-Hedging with OTM Puts:**  
  - Avoid over-hedging with deep OTM puts, especially when implied volatilities are elevated and risk of mean reversion (vol crush) is high.

---

### 6. Summary

The OTM Put Heavy portfolio exhibits acute vulnerability to vol crush scenarios, as evidenced by a ¥8.5bn loss (8.511% of notional) under a joint 3.974σ crisis shock. The primary structural weakness is over-reliance on expensive, deep OTM puts, which expose the portfolio to severe vega risk. In this scenario, a sharp volatility collapse, coupled with a mild equity uptick and adverse FX move, renders the vega-heavy hedge not only ineffective but actively loss-generating. The hedge design implicitly assumes persistent negative equity-vol correlation and fails to account for regime shifts or correlation breakdowns. The joint sigma analysis confirms that multi-factor co-movements can drive losses far beyond single-factor expectations. Actionable mitigation requires reducing vega concentration, diversifying tail hedges, and explicitly stress-testing for non-traditional crisis scenarios, including vol crushes and correlation breakdowns. Structural hedge redesign is essential to address these vulnerabilities and ensure robust protection across a broader range of crisis regimes.

## Review

quality_score: 0.93

This analysis demonstrates deep insight into the structural vulnerabilities of the portfolio, clearly explaining how the over-reliance on long OTM puts exposes the portfolio to a vol crush scenario. The explanation is highly specific, referencing the actual shock magnitudes, P&L breakdowns, and the joint sigma, and it accurately ties the scenario's factor moves to the observed losses. The analyst not only identifies the causal chain from the vol crush to the vega-driven losses but also highlights the breakdown of typical crisis correlations and the amplification of losses through multi-factor interactions. Actionable recommendations are provided, showing an understanding of how the hedge could be restructured to avoid this weakness. The only minor gap is that, while the analysis is comprehensive, it could be slightly more concise in places, but this does not detract from its overall quality and depth.
