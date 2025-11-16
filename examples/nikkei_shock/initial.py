"""
=== YAML SCENARIO FORMAT ===

scenario_yaml is always a YAML string with the following structure:

```yaml
name: <str>
description: <str>

exposure:
  - name: <str>
    mtm_value: <float>
    eq_linear: <float>
    eq_quad: <float>
    vol_linear: <float>
    fx_linear: <float>
    ir_dv01: <float>

hedge:
  - name: <str>
    mtm_value: <float>
    eq_linear: <float>
    eq_quad: <float>
    vol_linear: <float>
    fx_linear: <float>
    ir_dv01: <float>

stats:
  eq_vol: <float>
  vol_of_vol: <float>
  fx_vol: <float>
  ir_vol: <float>
  corr_normal: <list[list[float]]> # 4x4 matrix (equity, vol, fx, ir)
  corr_crisis: <list[list[float]]> # 4x4 matrix (equity, vol, fx, ir)

config:
  max_sigma_ratio: <float>
  max_horizon_days: <int>
  lambda_penalty: <float>
```

The AI should parse scenario_yaml with yaml.safe_load() and then analyze exposure vs hedge.

Example scenario_yaml:

```yaml
name: "JPY Rate Hedge"
description: "Portfolio of JPY bonds hedged with payer swaps."
exposure:
  - name: "10yr JGB"
    mtm_value: 50000000
    eq_linear: 0.0
    eq_quad: 0.0
    vol_linear: 0.0
    fx_linear: 0.0
    ir_dv01: 600000

hedge:
  - name: "10yr Payer Swap"
    mtm_value: -30000000
    eq_linear: 0.0
    eq_quad: 0.0
    vol_linear: 0.0
    fx_linear: 0.0
    ir_dv01: -450000

stats:
  eq_vol: 0.2
  vol_of_vol: 0.15
  fx_vol: 0.1
  ir_vol: 0.05
  corr_normal:
    - [1.0, -0.3, 0.1, -0.2]
    - [-0.3, 1.0, -0.1, 0.05]
    - [0.1, -0.1, 1.0, 0.15]
    - [-0.2, 0.05, 0.15, 1.0]
  corr_crisis:
    - [1.0, -0.5, 0.2, -0.3]
    - [-0.5, 1.0, -0.2, 0.1]
    - [0.2, -0.2, 1.0, 0.25]
    - [-0.3, 0.1, 0.25, 1.0]

config:
  max_sigma_ratio: 5.0
  max_horizon_days: 10
  lambda_penalty: 0.01
```
"""
import yaml
import math
import numpy as np
import pandas as pd
import re

# EVOLVE-BLOCK-START
def analyze_hedge_weakness(scenario: dict) -> str:
    """
    scenario is a dict with:
      - "name": <str>
      - "description": <str>
      - "exposure": list of instruments
      - "hedge": list of instruments
      - "stats": dict of stats
      - "config": dict of config
      - "scenario_yaml": YAML string with all of the above
    """
    name = scenario["name"]
    description = scenario["description"]
    exposure = scenario["exposure"]
    hedge = scenario["hedge"]
    stats = scenario["stats"]
    config = scenario["config"]
    scenario_yaml = scenario["scenario_yaml"]
    # Your code here to analyze the hedge weakness based on data
    return (
        f"Baseline hedge analysis for scenario '{name}': "
        "this stub does not yet analyze exposures, hedges, or weaknesses."
    )
# EVOLVE-BLOCK-END


def run_experiment(scenario: dict) -> dict:
    analysis = analyze_hedge_weakness(scenario)
    return {"scenario": scenario, "analysis": analysis}
