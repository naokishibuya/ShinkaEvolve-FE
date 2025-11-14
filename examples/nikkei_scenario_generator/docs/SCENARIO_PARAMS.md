# ScenarioParameters Overview

This example evolves **stress scenarios** for a Nikkei-based portfolio hedging problem.
A scenario is represented in *sigma space*, meaning each factor shock is expressed as a number of **standard deviations** ("sigmas") of that factor’s typical **daily change**.

The `ScenarioParameters` dataclass is:

```python
@dataclass
class ScenarioParameters:
    eq_sigmas: float
    vol_sigmas: float
    fx_sigmas: float
    ir_sigmas: float
    crisis_intensity: float
    horizon_days: int
```

Below is the meaning of each parameter.

## What “sigmas” mean

A **sigma** = one standard deviation of the *daily* movement of that factor, calculated from about **2–3 years of daily historical data** (for example).

The actual scenario shock applied in evaluation is:

$$
\text{shock} = \text{sigmas} \times \sigma_{\text{daily}} \times \sqrt{\text{horizon\_days}}
$$

This produces realistic multi-day stress moves.

Sigma notation normalizes each factor, rather than using absolute units (percent, vol points, basis points), which differ widely in scale.

## Why sigma-based scenarios?

* Makes factors comparable across units (percent, vol points, basis points).
* Keeps evolutionary search numerically stable.
* Allows mixing shocks across equity, FX, rates, and vol.
* Matches standard practice in risk management (e.g., VaR, ES, stress testing).
* Works well with hedging-model sensitivities (delta, gamma, vega, DV01).


## Why log-returns?

We use log returns $=\ln P_t - \ln P_{t-1}$ (not simple returns) because:

- They avoid impossible negative prices.
- They add up across days, making multi-day scenarios easy and consistent.
- They are approximately Gaussian for daily data, making sigma-based shocks meaningful.
- Their Gaussianity justifies the volatility × $\sqrt{T}$ scaling, the standard way to extend 1-day volatility into T-day stress horizons.

For these reasons, log returns are the appropriate factor unit for constructing sigma-based stress scenarios.

## Parameter Details

### **1. `eq_sigmas` — Nikkei 225 return shock**

Number of daily standard deviations of Nikkei **log-return**.

* Negative = index drop
* Example: `eq_sigmas = -5` → roughly a 5-sigma equity crash
* Converted using daily vol of NKY log-returns

Note: equity here means the Nikkei 225 index, not individual stocks.

---

### **2. `vol_sigmas` — implied volatility shock**

Number of daily standard deviations of **changes in implied volatility** (ΔIV).

* This is the “vol-of-vol”: std of daily changes in NKY implied volatility (e.g., VNKY).
* Example: `vol_sigmas = +3` → 3-sigma implied volatility spike.

**Note**: VNKY is the Nikkei Stock Average Volatility Index — Japan’s equivalent of the VIX (for the S&P 500).

**Why this matters for options:**

An IV shock directly affects option value through two channels:

| Greek | Meaning | PnL Impact |
|-------|---------|-----------|
| **Vega** | Option sensitivity to IV changes | Vega PnL ≈ $\mathcal{V}$ × Δσ |
| **Gamma** | Option sensitivity to spot moves | Gamma PnL ≈ 0.5 × $\Gamma$ × (ΔS)² |

Meaning of vol shocks for option portfolios:
- Long options profit from IV spikes (positive vega) and large spot moves (positive gamma). 
- An IV regime shift affects vega PnL even if the underlying price doesn't move.

**Impact on options:**

An IV shock primarily affects **vega PnL** (option value changes with IV):

$$\text{Vega PnL} \approx \mathcal{V} \times \Delta\sigma$$

Gamma PnL is secondary: IV spikes often correlate with underlying price moves (realized volatility), so gamma may follow, but it's not the direct driver of this shock.

Greek sensitivities used:
- Delta: $\Delta ={\frac {\partial V}{\partial S}}$
- Gamma: $\Gamma ={\frac {\partial \Delta }{\partial S}}={\frac {\partial ^{2}V}{\partial S^{2}}}$
- Vega: ${\mathcal {V}}={\frac {\partial V}{\partial \sigma}}$ (IV sensitivity)

---

### **3. `fx_sigmas` — USD/JPY shock**

Number of daily standard deviations of USDJPY **log-returns**.

* Positive = USDJPY up (JPY weaker)
* Negative = USDJPY down (JPY stronger)
* Example: `fx_sigmas = +2` → ~2σ FX shock

**How it affects Nikkei:**

Most large-cap Nikkei companies are exporters (Toyota, Sony, etc.), so FX moves directly impact earnings:

* **Weaker JPY (USD/JPY ↑):** Foreign revenues convert to more yen → exporters benefit
* **Stronger JPY (USD/JPY ↓):** Imported costs rise → importers hurt

**Market impact:**

The Nikkei reprices through two channels:
1. **Earnings expectations** — market adjusts profit forecasts immediately
2. **Currency translation** — balance sheets revalue FX assets/liabilities

**Difference from vol shock:**

The vol shock affects options directly (vega PnL). The FX shock moves the underlying Nikkei price, creating **gamma PnL** for options holders.

---

### **4. `ir_sigmas` — interest-rate shock**

Number of daily standard deviations of **10-year JGB yield changes**.

* Maps directly to DV01 exposure: the PnL impact per basis point of yield movement
* Example: `ir_sigmas = +2` → ~2σ yield spike, meaning "10-year JGB yields move up by 2 standard deviations of typical daily yield changes" (i.e., several basis points)

**How it affects:**

* **Bond portfolios:** DV01 exposure — direct inverse relationship to yields (When you hold a bond and yields go up, the bond price falls)
* **Option portfolios:** Rho exposure — options become less valuable as rates rise (discount rate effect)

| Exposure | Sensitivity | PnL Formula |
|----------|-------------|------------|
| Bonds | DV01 | PnL ≈ -DV01 × Δyield (bp) |
| Options | Rho (ρ) | PnL ≈ ρ × Δyield (%) |

Note: 
- JGB = Japanese Government Bond
- DV01 = PnL per 1 basis point yield move
- Rho = option value change per 1% yield change
- Basis point = 0.01% (0.0001 decimal)

DV01 tells you exactly how much you lose per basis point of yield increase. If DV01 = ¥10,000 (meaning the bond loses ¥10,000 per 1 basis point move), then a 5-basis-point yield increase causes a loss of ¥50,000.

---

### **5. `crisis_intensity` — correlation regime**

Controls how asset shocks correlate with each other.

* `0.0`: Normal market correlations (historical average)
* `1.0`: Crisis correlations (all assets move together)
* Values in between: blend the two regimes

**Why this matters:**

In normal times, shocks are somewhat independent. In crises, correlations break down and everything moves together:
- Example: Equity down → Vol spikes + JPY strengthens + Yields spike
- All shocks amplify each other

**How it works:**

The scenario engine:
1. Interpolates between normal and crisis correlation matrices based on `crisis_intensity`
2. Uses Cholesky decomposition to generate correlated shocks across all 4 risk factors
3. Scales shocks by $\sqrt{\text{horizon\_days}}$ to extend 1-day moves to multi-day horizons

This ensures that if you request `eq_sigmas = -2, vol_sigmas = +3, fx_sigmas = +1, ir_sigmas = +2`, these four shocks move together realistically rather than independently.

---

### **6. `horizon_days` — shock duration**

Number of days over which the shock is assumed to occur.

* Typical range: 1–10
* Shocks scale with $\sqrt{T}$

Example:
A 5-sigma 1-day equity shock ≈ ~11% over 5 days.

---

## Summary Table

| Parameter          | Meaning                           | Uses                      |
| ------------------ | --------------------------------- | ------------------------- |
| `eq_sigmas`        | # of daily σ of NKY log-return    | Equity crash / grind-down |
| `vol_sigmas`       | # of daily σ of Δ implied vol     | Vol spike / vol crush     |
| `fx_sigmas`        | # of daily σ of USDJPY log-return | FX shock / JPY spike      |
| `ir_sigmas`        | # of daily σ of 10Y yield changes | Rate shock (bp)           |
| `crisis_intensity` | Regime switch 0→1                 | Correlation breakdown     |
| `horizon_days`     | Duration of shock                 | $\sqrt{T}$ scaling        |
