# HistoricalStats Overview

`HistoricalStats` contains all the **market statistics needed to turn a proposed scenario (in sigma units) into real shocks**.
These values are computed **offline** from historical daily time series of Nikkei 225, VNKY (or ATM implied vol), USDJPY, and 10Y JGB yields.

This dataclass is treated as **fixed input** to the scenario generator and does not change during evolution.

```python
@dataclass
class HistoricalStats:
    eq_vol: float               # daily vol of NKY log returns
    vol_of_vol: float           # daily vol of implied vol changes
    fx_vol: float               # daily vol of USDJPY log returns
    ir_vol: float               # daily vol of 10Y JGB yield changes

    corr_normal: np.ndarray     # 4x4 normal-regime correlation matrix
    corr_crisis: np.ndarray     # 4x4 crisis-regime correlation matrix
```

It is used to map sigma-level scenario proposals into **realistic, correlated multi-factor shocks**

## What Each Field Means

### **1. eq_vol — Daily volatility of Nikkei log returns**

* Computed from **daily log returns** of Nikkei 225.
* Represents the standard deviation of daily log-price movements: $\text{eq\_vol} = \text{std}(\ln P_t - \ln P_{t-1})$.
* Converts `eq_sigmas` (number of standard deviations) into a real price shock over T days.

$$
\text{eq\_shock} = \text{eq\_sigmas} \times \text{eq\_vol} \times \sqrt{T}
$$

**Example:** 

If `eq_vol = 2%`, `eq_sigmas = -2`, and `T = 10` days:
$$
\text{eq\_shock} = -2 \times 0.02 \times \sqrt{10} \approx -12.6\%
$$

---

### **2. vol_of_vol — Daily volatility of implied-volatility changes**

* Derived from **daily changes in implied vol** (e.g., VNKY or ATM IV).
* Represents the standard deviation of daily IV movements (in percentage points or basis points).
* Converts `vol_sigmas` (number of standard deviations) into a real IV shock over T days.

$$
\Delta \sigma = \text{vol\_sigmas} \times \text{vol\_of\_vol} \times \sqrt{T}
$$

**Example:**

If `vol_of_vol = 1.5%`, `vol_sigmas = +3`, and `T = 10` days:
$$
\Delta \sigma = 3 \times 0.015 \times \sqrt{10} \approx +1.42\%
$$

This reflects **volatility regime shifts**, which directly impact **vega PnL** for option portfolios.

---

### **3. fx_vol — Daily volatility of USDJPY log returns**

* Computed from **daily log returns** of USDJPY.
* Represents the standard deviation of daily FX movements.
* Used to convert `fx_sigmas` into a realistic USDJPY move over T days.

$$
\text{fx\_shock} = \text{fx\_sigmas} \times \text{fx\_vol} \times \sqrt{T}
$$

**Example:**

If `fx_vol = 0.8%`, `fx_sigmas = +2`, and `T = 10` days:
$$
\text{fx\_shock} = 2 \times 0.008 \times \sqrt{10} \approx +5.1\%
$$

---

### **4. ir_vol — Daily volatility of 10Y JGB yield changes**

* Computed from **daily yield changes** of 10Y JGB (in basis points or decimal form).
* Represents the standard deviation of daily yield movements.
* Used to convert `ir_sigmas` into a realistic yield shock over T days.

$$
\text{ir\_shock} = \text{ir\_sigmas} \times \text{ir\_vol} \times \sqrt{T}
$$

**Example:**

If `ir_vol = 3 bp` (0.0003), `ir_sigmas = +2`, and `T = 10` days:
$$
\text{ir\_shock} = 2 \times 0.0003 \times \sqrt{10} \approx +1.9 \text{ bp}
$$

**Note:** For bond portfolios, `ir_shock` translates to PnL via DV01 (see Scenario Parameters section).

---

### **5. corr_normal — Normal-regime correlation matrix (4×4)**

Correlation structure between the four risk factors in calm markets.

The 4×4 matrix captures all pairwise correlations:
* **Equity:** Daily log-returns of Nikkei 225
* **Vol:** Daily changes in implied volatility (VNKY or ATM IV)
* **FX:** Daily log-returns of USDJPY
* **Rates:** Daily yield changes of 10Y JGB

**Example structure:**
```
         Equity  Vol    FX     Rates
Equity    1.0   -0.3   0.1    0.2
Vol      -0.3    1.0  -0.1   -0.2
FX        0.1   -0.1    1.0    0.3
Rates     0.2   -0.2    0.3    1.0
```

Used when `crisis_intensity = 0`.

---

### **6. corr_crisis — Crisis-regime correlation matrix (4×4)**

Correlation structure between the four risk factors during stress periods (e.g., 2008, 2011, 2020).

In crises, correlations typically strengthen and shift compared to normal regimes. Assets tend to move together in risk-off mode.

**Example crisis-regime correlation matrix:**
```
         Equity  Vol    FX     Rates
Equity    1.0   -0.7  -0.6    0.3
Vol      -0.7    1.0   0.5   -0.4
FX       -0.6    0.5    1.0   -0.2
Rates     0.3   -0.4   -0.2    1.0
```

Used when `crisis_intensity = 1`.

---

## How Correlation Regimes Work

In `evaluate.py`, the scenario engine transforms independent sigma shocks into correlated multi-factor moves:

1. **Interpolate (blend) correlations** based on `crisis_intensity`

    $$
    \text{corr}(c) = (1 - c)\cdot\text{corr\_normal} + c\cdot\text{corr\_crisis}
    $$

    where $c = \text{crisis\_intensity}$. This enables smooth transition between normal, partial stress, and full crisis regimes.

2. **Build covariance matrix** by scaling correlations with volatilities

    $$
    \text{cov} = D \cdot \text{corr}(c) \cdot D
    $$

    with $D = \text{diag}(\text{eq\_vol}, \text{vol\_of\_vol}, \text{fx\_vol}, \text{ir\_vol})$.

3. **Factorize via Cholesky decomposition**

    $$
    L = \text{Cholesky}(\text{cov})
    $$

    This produces a lower triangular matrix `L` such that $\text{cov} = L \, L^T$, encoding the full correlation structure.

4. **Generate correlated shocks** by applying the Cholesky matrix to independent sigmas and scaling by horizon

    $$
    \text{correlated\_shocks} = L \cdot \sigma\_\text{vec} \times \sqrt{T}
    $$

    where $\sigma\_\text{vec} = [\text{eq\_sigmas}, \text{vol\_sigmas}, \text{fx\_sigmas}, \text{ir\_sigmas}]^T$.

    The matrix-vector product `L @ σ_vec` transforms independent shocks into correlated ones respecting the interpolated regime.
