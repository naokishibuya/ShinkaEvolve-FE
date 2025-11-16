from typing import Any


# EVOLVE-BLOCK-START
def analyze_hedge_weakness(scenario: dict[str, Any]) -> str:
    """
    Analyze hedge weaknesses for a given scenario.

    Args:
        scenario: dict with:
          - name (str): scenario name
          - description (str): scenario description
          - exposure: list of instruments
          - hedge: list of instruments
          - stats: dict with vols and 4x4 corr matrices
          - config: dict with max_sigma_ratio, max_horizon_days, lambda_penalty

        Each instrument is a dict with fields:
          - name (str): Instrument name
          - mtm_value (float): Current mark-to-market value in JPY (positive = long, negative = short).
          - eq_linear (float): Equity sensitivity (delta-like; P&L per 1σ equity move, scaled by mtm_value).
          - eq_quad (float): Equity convexity (gamma-like; P&L per (1σ equity move)^2, scaled by mtm_value).
          - vol_linear (float): Volatility sensitivity (Vega-like; P&L per 1σ move in volatility, scaled by mtm_value).
          - fx_linear (float): FX sensitivity (P&L per 1σ move in FX rate, e.g. USDJPY scaled by mtm_value).
          - ir_dv01 (float): Interest rate sensitivity (DV01; P&L per 1bp move in interest rates, absolute JPY amount).

        Stats dict contains:
          - eq_vol (float): Daily equity volatility (1σ) as a decimal, e.g. 0.2 = 20%
          - vol_of_vol (float): Daily volatility-of-volatility (1σ) as a decimal
          - fx_vol (float): Daily FX volatility (1σ) as a decimal 
          - ir_vol (float): Daily interest rate volatility (1σ) as a decimal
          - corr_normal (np.ndarray, shape (4,4)): Normal regime correlation: 4x4 matrix in [equity, vol, fx, ir] order
          - corr_crisis (np.ndarray, shape (4,4)): Crisis regime correlation: 4x4 matrix in [equity, vol, fx, ir] order

        config dict contains:
          - max_sigma_ratio (float): How extreme shocks should be (in terms of σ, i.e., 10σ)
          - max_horizon_days (int): Max horizon days to avoid sqrt(T) blowup
          - lambda_penalty (float): Weight of plausibility penalty in total loss

    ============================
    EXAMPLE SCENARIO DICTIONARY
    ============================
    ```python
    {
        "name": "JPY Rate Hedge",
        "description": "Portfolio of JPY bonds hedged with payer swaps.",
        "exposure": [
            {
                "name": "10yr JGB",
                "mtm_value": 50000000,
                "eq_linear": 0.0,
                "eq_quad": 0.0,
                "vol_linear": 0.0,
                "fx_linear": 0.0,
                "ir_dv01": 600000,
            },
        ],
        "hedge": [
            {
                "name": "Short_Nikkei_Futures",
                "mtm_value": -100000000000,
                "eq_linear": 1.0,
            },
            {
                "name": "10yr Payer Swap",
                "mtm_value": -30000000,
                "eq_linear": 0.0,
                "eq_quad": 0.0,
                "vol_linear": 0.0,
                "fx_linear": 0.0,
                "ir_dv01": -450000,
            },
        ],
        "stats": {
            "eq_vol": 0.2,
            "vol_of_vol": 0.15,
            "fx_vol": 0.1,
            "ir_vol": 0.05,
            "corr_normal": np.array([
                [1.0, -0.3, 0.1, -0.2],
                [-0.3, 1.0, -0.1, 0.05],
                [0.1, -0.1, 1.0, 0.15],
                [-0.2, 0.05, 0.15, 1.0],
            ]),
            "corr_crisis": np.array([
                [1.0, -0.5, 0.2, -0.3],
                [-0.5, 1.0, -0.2, 0.1],
                [0.2, -0.2, 1.0, 0.25],
                [-0.3, 0.1, 0.25, 1.0],
            ]),
        },
        "config": {
            "max_sigma_ratio": 5.0,
            "max_horizon_days": 10,
            "lambda_penalty": 0.01,
        },
    }

    ============================
    RETURN REQUIREMENTS
    ============================
    Must return a single multi-line string describing:
      • the portfolio's true exposures,
      • what each hedge instrument is intended to insure,
      • structural or residual weaknesses,
      • consistency with the data (stats + correlations + config).

    The returned value MUST be a string.
    """
    # IMPORTANT: Do NOT change the function signature or return type.

    # Do your analysis here.
    name = scenario["name"]

    analysis = (
        f"TODO: analyze scenario '{name}' for exposures, hedges, or weaknesses."
    )
    return analysis
# EVOLVE-BLOCK-END
