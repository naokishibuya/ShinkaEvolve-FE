# Shock Parameters Overview

Stress scenarios are expressed in **sigma space**, meaning each shock is specified as a number of **daily standard deviations (“sigmas”)** of that factor’s typical movement. These sigmas are later converted into actual equity/vol/FX/rate moves using the fixed historical statistics.

Each scenario specifies four shock parameters:

```python
eq_shock_sigma: float
vol_shock_sigma: float
fx_shock_sigma: float
ir_shock_sigma: float
```

These represent **signed**, **1-day sigma-unit** shocks for each factor.

---

## What “sigma” means

A **sigma** = one standard deviation of **the factor’s daily changes**, computed from historical data.

The actual shock applied is:

$$
\text{move} = \text{sigmas} \times \sigma_{\text{daily}} \times \sqrt{\text{horizon\_days}}
$$

where `σ_daily` comes from historical stats (e.g., `eq_vol`, `fx_vol`, etc.).

Sigma-based representation:

- normalizes all factors into a common unit,
- stabilizes evolutionary search,
- corresponds to standard VaR/ES stress-testing practice.

---

## Parameter Details

### **1. `eq_shock_sigma` — Equity (Nikkei 225) shock**
Number of daily sigmas of **Nikkei log-return**.

- Negative → equity drop  
- Positive → equity rally  
- Example: `eq_shock_sigma = -5` ≈ 5σ equity crash

Converted to price move using:

$$
\Delta S / S \approx \text{eq\_shock\_sigma} \times \text{eq\_vol} \times \sqrt{T}
$$

---

### **2. `vol_shock_sigma` — Implied volatility shock**

Number of daily sigmas of **changes in implied volatility** (vol-of-vol).

- Positive → IV spike  
- Negative → IV crush  
- Example: `vol_shock_sigma = +3` → 3σ IV increase

Vega PnL impact:

$$
\text{Vega PnL} \approx \mathcal{V} \times \Delta \sigma
$$

Gamma PnL is indirectly affected via correlated spot moves.

---

### **3. `fx_shock_sigma` — USD/JPY shock**

Number of daily sigmas of **USDJPY log-return**.

- Positive → USDJPY up (JPY weaker)  
- Negative → USDJPY down (JPY stronger)  
- Example: `fx_shock_sigma = +2`

Converted using:

$$
\Delta FX = \text{fx\_shock\_sigma} \times \text{fx\_vol} \times \sqrt{T}
$$

FX moves affect Nikkei and hedge instruments through:

- exporter/importer earnings effects,
- translation effects,
- directional FX hedges.

---

### **4. `ir_shock_sigma` — Interest-rate (10Y JGB yield) shock**

Number of daily sigmas of **daily yield changes**.

- Positive → yield spike  
- Negative → yield drop  
- Example: `ir_shock_sigma = +2`

Converted using:

$$
\Delta y_{\text{decimal}} = \text{ir\_shock\_sigma} \times \text{ir\_vol} \times \sqrt{T}
$$

Applied through DV01:

$$
\text{Rate PnL} = \text{DV01} \times (\Delta y_{\text{decimal}} \times 10{,}000)
$$

---

## Summary Table

| Parameter          | Meaning                                      | Interpretation                    |
|--------------------|----------------------------------------------|-----------------------------------|
| `eq_shock_sigma`   | # of daily σ of NKY log-return               | Equity crash / rally              |
| `vol_shock_sigma`  | # of daily σ of Δ implied vol                | Vol spike / vol crush             |
| `fx_shock_sigma`   | # of daily σ of USDJPY log-return            | JPY move (FX shock)               |
| `ir_shock_sigma`   | # of daily σ of 10Y JGB yield changes        | Rate spike / rally (DV01-based)   |

These four signals define a complete, signed, multi-factor shock in sigma space.
