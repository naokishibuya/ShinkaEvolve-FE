# Historical Stats Overview

Historical stats provide all **market parameters needed to convert sigma-based
shocks into real factor moves** over a multi-day horizon. These values are fixed
inputs to the scenario generator and **do not change during evolution**.

```python
eq_vol: float               # daily vol of Nikkei 225 log returns
vol_of_vol: float           # daily vol of implied-volatility (ATM IV) changes
fx_vol: float               # daily vol of USDJPY log returns
ir_vol: float               # daily vol of 10Y JGB yield changes
corr_crisis: np.ndarray     # 4×4 crisis-regime correlation matrix
horizon_days: int           # scenario time horizon (days)
````

The scenario generator uses these fields to:

1. Convert sigma shocks into **actual factor moves** (eq, vol, fx, rates).
2. Evaluate **joint sigma plausibility** using the *Mahalanobis radius* based on the crisis correlation matrix.

---

## 1. eq_vol — Daily volatility of Nikkei log returns

Derived from historical daily log returns:

$$
\text{eq\_vol} = \operatorname{std}(\ln P_t - \ln P_{t-1})
$$

Convert an equity shock in sigma units to a real equity move:

$$
\text{eq\_move} = \text{eq\_shock\_sigma} \times \text{eq\_vol} \times \sqrt{T}
$$

Example:
If `eq_vol = 0.012`, `eq_shock_sigma = -3`, and `T = 10` days:

$$
\text{eq\_move} \approx -3 \cdot 0.012 \cdot \sqrt{10} \approx -11.4%
$$

---

## 2. vol_of_vol — Daily volatility of implied-vol changes

Represents the standard deviation of **daily changes in implied volatility** (e.g., VNKY ATM IV).

$$
\Delta \sigma = \text{vol\_shock\_sigma} \times \text{vol\_of\_vol} \times \sqrt{T}
$$

Used to compute **vega and convexity PnL**.

---

## 3. fx_vol — Daily volatility of USDJPY log returns

Computed from daily log-return series of USDJPY.

$$
\text{fx\_move} = \text{fx\_shock\_sigma} \times \text{fx\_vol} \times \sqrt{T}
$$

If `fx_vol = 0.006` and `fx_shock_sigma = +5`:

$$
\text{fx\_move} \approx 5 \cdot 0.006 \cdot \sqrt{10} \approx +9.5%
$$

---

## 4. ir_vol — Daily volatility of 10Y JGB yield changes

Based on daily changes in **10Y JGB yields**, expressed in decimal form.

$$
\text{ir\_move} = \text{ir\_shock\_sigma} \times \text{ir\_vol} \times \sqrt{T}
$$

Example:
If `ir_vol = 0.0015` and `ir_shock_sigma = +4`:

$$
\text{ir\_move} \approx 4 \cdot 0.0015 \cdot \sqrt{10} = 0.01895
$$

This means yields rise by **1.895% = 189.5 bp**.

PNL linkage:

$$
\text{PnL}_\text{rates} = \text{DV01} \times (10{,}000 \cdot \text{ir\_move})
$$

---

## 5. corr_crisis — Crisis-regime correlation matrix (4×4)

The matrix encodes the **cross-asset correlation structure during market stress**.

Order:
`[equity, implied vol, FX (USDJPY), rates (10Y JGB)]`

Example layout:

```
         EQ      VOL     FX      IR
EQ      1.0     -0.8   -0.4    -0.5
VOL    -0.8      1.0    0.3     0.4
FX     -0.4      0.3    1.0     0.2
IR     -0.5      0.4    0.2     1.0
```

### How correlations are used

**Important change:**

* We **do NOT mix directions** using correlations.
* Factor moves (eq/vol/fx/ir) remain **independent**, based solely on the chosen sigma values.
* The correlation matrix is used **only** to compute:

### **joint_sigma (Mahalanobis radius)**

$$
\text{joint\_sigma}
= \sqrt{
\sigma^\top ,
\text{corr\_crisis}^{-1} ,
\sigma
}
$$

where:

$$
\sigma =
\begin{bmatrix}
\text{eq\_shock\_sigma} \\
\text{vol\_shock\_sigma} \\
\text{fx\_shock\_sigma} \\
\text{ir\_shock\_sigma}
\end{bmatrix}
$$

### Purpose:

* Plausibility constraint
* Penalizes “unrealistic” shock combinations
* Prevents the model from selecting impossible cross-asset configurations

### NOT used for:

* Direction mixing
* Generating correlated factor moves
* Affecting individual equity/vol/FX/rates shocks

This keeps the model simple and interpretable.

---

## 6. horizon_days — Scenario horizon in days

Used universally for √T scaling:

$$
\text{scale} = \sqrt{T} = \sqrt{\text{horizon\_days}}
$$

This applies to **all four factors**.
