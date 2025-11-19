# ShinkaEvolve-FE (Financial Engineering)

ShinkaEvolve-FE is a POC project based on the [SakanaAI's ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) that applies LLM-driven program evolution to financial engineering problems, specifically cross-asset risk analysis and stress testing.

## Motivation

Institutional risk managers face a fundamental challenge: **portfolios that appear well-hedged under normal conditions can fail catastrophically during market crises**. Traditional stress testing often relies on historical scenarios or simple sensitivity analysis, which may miss:

- **Correlation breakdowns**: Hedges that work in normal markets can amplify losses when asset correlations shift during crises
- **Convexity risks**: Non-linear exposures (gamma, vega) that matter more during large moves
- **Cross-asset transmission**: How equity shocks propagate through volatility, FX, and interest rates
- **Hedge inefficiencies**: Over-hedged positions that bleed costs or under-hedged ones that leave residual risk

This project addresses these challenges by **evolving AI agents that discover portfolio weaknesses** through adversarial stress testing. Rather than relying on fixed scenarios, the system uses LLM-based evolution to iteratively improve both:
1. **Risk analysis quality**: How well the AI explains exposures, hedge intent, and failure modes
2. **Shock efficiency**: How effectively multi-factor shocks exploit portfolio weaknesses

## The Nikkei Shock Implementation

The `examples/nikkei_shock` implementation demonstrates this approach on Japanese institutional portfolios with realistic cross-asset dynamics:

### Core Components

1. **Portfolio Scenarios** ([scenarios.yaml](examples/nikkei_shock/scenarios.yaml))
   - Six carefully designed portfolios with different hedge vulnerabilities
   - Each includes exposure instruments (e.g., physical Nikkei stocks) and hedge instruments (futures, puts, FX hedges, JGBs)
   - Instruments have full Greek profiles: delta, gamma, vega, FX sensitivity, and DV01
   - Synthetic market statistics: daily volatilities for equity (1.2%), vol-of-vol (2%), USDJPY (0.6%), JGB yields (0.15%)
   - Crisis correlation matrix capturing flight-to-safety dynamics (equity crash → vol spike + JPY strength + yield drop)

2. **AI-Driven Analysis** ([initial.py](examples/nikkei_shock/initial.py))
   - LLM evolves the `analyze_hedge_weakness()` function through generations
   - Must identify net exposures from Greek breakdowns (delta, gamma, vega, FX, DV01)
   - Determine what each hedge instrument protects against
   - Find structural weaknesses and residual risks
   - Propose adversarial multi-factor shocks that exploit those weaknesses
   - Returns both qualitative analysis (textual explanation) and quantitative shock parameters (sigma units per factor)

3. **Dual Evaluation System** ([evaluate.py](examples/nikkei_shock/evaluate.py), [feedback.py](examples/nikkei_shock/feedback.py))

   **Quantitative Scoring** ([quant_utils.py](examples/nikkei_shock/quant_utils.py)):
   - Converts shock sigmas → actual factor moves using crisis correlations and √T scaling
   - Computes portfolio P&L breakdown by factor (equity, vol, FX, rates)
   - Measures loss ratio (loss / exposure) and joint sigma (Mahalanobis distance)
   - Normalizes both metrics against targets using rational squashing: `x/(1+|x|)` maps ℝ to (-1,1)
     - `norm_loss = 0.5` at target loss ratio (25% by default)
     - `norm_sigma = 0.5` at target crisis severity (3σ Mahalanobis by default)
   - Final score = `normalize(norm_loss - norm_sigma)` ∈ (-1, 1)
     - Score = 0.0 when both targets are met (balanced stress test)
     - Positive scores: loss outpaces severity (efficient shock)
     - Negative scores: excessive severity for limited loss (inefficient shock)

   **Qualitative Scoring** (LLM Judge):
   - Another LLM evaluates the analysis quality on 5 criteria:
     1. Correctly identifies main net exposures and hedge intent
     2. Identifies structural weaknesses and hedge failure modes
     3. Consistency with data (sensitivities, correlations, actual P&L)
     4. Shows insight into cross-asset interactions
     5. Technical accuracy and clarity
   - Very strict grading: shallow or generic analyses receive low scores

   **Combined Feedback**:
   - Final score = 0.5 × quantitative + 0.5 × qualitative
   - Meta-judge LLM summarizes performance across scenarios
   - Provides structured feedback: strengths, common gaps, and next-generation focus areas
   - This feedback guides the evolutionary process toward better analysis

4. **Evolution Loop** (Shinka Framework)
   - LLM coder mutates the `analyze_hedge_weakness()` function based on feedback
   - Each generation is evaluated on all 6 scenarios
   - Winners are selected based on combined scores
   - Over generations, the AI learns to:
     - Write more insightful risk analysis
     - Design more efficient adversarial shocks
     - Better exploit cross-asset correlation dynamics
     - Identify subtle hedge weaknesses (basis risk, convexity mismatches, etc.)

### Key Innovation: Multi-Dimensional Quality with Balanced Optimization

Unlike traditional optimization (which might just maximize P&L loss), this system co-optimizes three dimensions:

1. **Analysis quality** (qualitative score ∈ [0, 1]): The AI must *explain why* a shock is dangerous, not just find it
   - Evaluated by LLM judge on technical accuracy, insight, and clarity

2. **Shock efficiency** (quantitative score ∈ (-1, 1)): Losses must come from realistic crisis-like scenarios
   - Measures balance between portfolio loss and shock severity
   - Score = 0.0 when loss ratio and Mahalanobis distance both hit configured targets
   - Rewards finding weaknesses without resorting to extreme "tail of tail" shocks

3. **Cross-asset coherence** (embedded in quantitative score): Shocks must respect crisis correlations
   - Mahalanobis distance penalizes correlation-inconsistent factor combinations
   - E.g., equity down + vol up + JPY strong is lower-sigma than uncorrelated shocks

**Combined score** = 0.5 × quantitative + 0.5 × qualitative ∈ (-0.5, 1.0)

This design ensures evolved agents produce **interpretable, realistic stress tests** rather than gaming the system with implausible scenarios or brute-force severity.

### Example Workflow

```python
# Scenario: Portfolio with 100B yen Nikkei stocks, hedged with:
# - 80B short Nikkei futures (80% linear hedge)
# - 5B long ATM puts (convexity protection)
# - 50B short USDJPY futures (JPY strength hedge)
# - -1B DV01 JGB futures (yield-drop hedge)

# AI analyzes the greeks_breakdown:
# Net delta: +20B (under-hedged on linear equity)
# Net gamma: +40B (positive convexity from puts)
# Net vega: +20B (benefits from vol spike)
# Net FX: -50B (benefits from JPY strength)
# Net DV01: -1B (benefits from yield drop)

# AI identifies weakness:
# "FX hedge assumes JPY strengthens in crisis, but if JPY weakens
#  (e.g., inflation scare), the -50B FX position amplifies losses"

# AI proposes shock:
# eq_shock_sigma: -8.0  (equity crash)
# vol_shock_sigma: +3.0 (moderate vol spike)
# fx_shock_sigma: +6.0  (JPY weakens - adversarial to FX hedge)
# ir_shock_sigma: +4.0  (yields rise - adversarial to JGB position)

# Evaluation:
# - Quantitative:
#   - P&L: -15B (15% loss ratio), joint_sigma: 3.2
#   - norm_loss = normalize(0.15 / 0.25) = 0.375  (below target)
#   - norm_sigma = normalize(3.2 / 3.0) = 0.516   (slightly above target)
#   - score = normalize(0.375 - 0.516) = -0.066   (slightly inefficient)
# - Qualitative: Judge scores analysis 0.75/1.0 for clear identification of FX weakness
# - Combined: 0.5 × (-0.066) + 0.5 × 0.75 = 0.342
# - Feedback: "Loss below target; aim shocks more directly at net delta/gamma/vega"
```

## Feature Highlights

- **Native Ollama support** ([shinka/llm/models/ollama.py](shinka/llm/models/ollama.py)): Use `ollama::model-name` in configs to run local chat, coder, or embedding models alongside cloud providers
- **Structured dataclass contracts**: Type-safe interfaces ensure LLM-generated code matches evaluation expectations
- **Multi-scenario evaluation**: Each generation tested on 6 diverse portfolios to avoid overfitting
- **Interpretable feedback loop**: Text summaries guide evolution toward better analysis, not just better scores

## Installation

```bash
# Clone the repository
git clone https://github.com/naokishibuya/ShinkaEvolve-FE
cd ShinkaEvolve-FE

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
uv pip install -e .          # installs Shinka + ollama SDK
```

### Ollama Setup

```bash
curl https://ollama.ai/install.sh | sh

ollama pull codellama:7b
ollama pull deepseek-coder:6.7b
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Choosing LLMs & Embeddings

- Cloud API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) are required for cloud models
- Ollama respects `OLLAMA_BASE_URL` / `OLLAMA_TIMEOUT` environment variables
- Mix and match: Use cloud models for coder/judge and local embeddings, or vice versa

## Quick Start

### Running Nikkei Shock Evolution

Two preset configurations are available:

**1. Free Local-Only Mode** ([nikkei_shock_example_free.yaml](configs/variant/nikkei_shock_example_free.yaml))
```bash
shinka_launch variant=nikkei_shock_example_free
```
- **Coder LLM**: Uses local Ollama models (default: `llama3.1:8b` or similar)
- **Judge LLM**: `ollama::llama3.1:8b` for analysis quality evaluation
- **Evolution**: Zero-budget evolution (generates candidates but minimal selection pressure)
- **Best for**: Quick experimentation, understanding the workflow, testing on consumer hardware
- **Limitations**: Analysis quality and shock design may be suboptimal due to smaller model capacity

**2. Cloud-Powered Mode** ([nikkei_shock_example.yaml](configs/variant/nikkei_shock_example.yaml))
```bash
shinka_launch variant=nikkei_shock_example
```
- **Coder LLM**: `gpt-4.1-mini` for evolving the analysis function
- **Judge LLM**: `gpt-4.1` for high-quality analysis evaluation
- **Evolution**: Small budget evolution (10 generations)
- **Best for**: Production-quality results, research experiments, discovering subtle hedge weaknesses
- **Requirements**: OpenAI API key with GPT-4 access

### What Happens During Evolution

1. **Initialization**: Starts with a stub `analyze_hedge_weakness()` function ([initial.py](examples/nikkei_shock/initial.py))
2. **Evaluation**: Runs on 6 scenarios, receives dual scores (qualitative + quantitative) and text feedback
3. **Mutation**: LLM coder reads feedback and modifies the function to improve analysis and shock design
4. **Selection**: Better candidates (higher combined scores) are kept for next generation
5. **Iteration**: Repeats for configured number of generations
6. **Output**: Best evolved function saved with performance metrics

You can monitor progress in real-time as each generation's scores and feedback are displayed.

## Directory Highlights

| Path | Purpose |
|------|---------|
| **Core Nikkei Shock Implementation** | |
| [examples/nikkei_shock/scenarios.yaml](examples/nikkei_shock/scenarios.yaml) | Portfolio scenarios with instruments, greeks, market stats, and crisis correlations |
| [examples/nikkei_shock/initial.py](examples/nikkei_shock/initial.py) | Stub `analyze_hedge_weakness()` function that LLM evolves |
| [examples/nikkei_shock/evaluate.py](examples/nikkei_shock/evaluate.py) | Evaluation orchestrator: runs scenarios, validates outputs, aggregates metrics |
| [examples/nikkei_shock/feedback.py](examples/nikkei_shock/feedback.py) | Dual evaluation: LLM judge for analysis quality + quantitative shock scoring |
| [examples/nikkei_shock/quant_utils.py](examples/nikkei_shock/quant_utils.py) | Financial math: factor moves, P&L calculation, Mahalanobis distance, efficiency scoring |
| [examples/nikkei_shock/scenario.py](examples/nikkei_shock/scenario.py) | Dataclass definitions and YAML loading for type-safe contracts |
| **Configuration** | |
| [configs/variant/nikkei_shock_example.yaml](configs/variant/nikkei_shock_example.yaml) | Cloud-powered setup (GPT-4.1-mini coder + GPT-4.1 judge, 10 generations) |
| [configs/variant/nikkei_shock_example_free.yaml](configs/variant/nikkei_shock_example_free.yaml) | Free local setup (Ollama models, zero-budget evolution) |
| [configs/task/nikkei_shock.yaml](configs/task/nikkei_shock.yaml) | Task configuration: system prompt, function contract, evaluation settings |
| **Framework Extensions** | |
| [shinka/llm/models/ollama.py](shinka/llm/models/ollama.py) | Ollama adapter for local LLM support (chat and embeddings) |
| **Upstream Examples** | |
| `examples/circle_packing`, `examples/ale_bench`, ... | Original ShinkaEvolve examples (unchanged) |
| `docs/` | Upstream documentation (Getting Started, WebUI, Configuration) |

## Customization Guide

### Adding New Portfolio Scenarios

Edit [scenarios.yaml](examples/nikkei_shock/scenarios.yaml) to add new portfolios:

```yaml
scenarios:
  - name: Your Scenario Name
    description: Brief description of the portfolio and expected vulnerabilities
    exposure:
      - name: Asset_Name
        mtm_value: 100_000_000  # Mark-to-market in JPY
        eq_linear: 1.0          # Equity delta (per 1σ move)
        eq_quad: 0.0            # Equity gamma (per σ²)
        vol_linear: 0.0         # Vega (per 1σ vol move)
        fx_linear: 0.0          # FX delta (per 1σ FX move)
        ir_dv01: 0.0            # JPY P&L per +1bp yield move
    hedge:
      - name: Hedge_Instrument
        # ... same structure
```

**Tips**:
- Design portfolios with different vulnerabilities (vol crush, FX mismatch, convexity gaps, etc.)
- Use realistic sensitivities based on actual derivative pricing
- Add comments explaining expected failure modes to guide evaluation

### Adjusting Evaluation Targets

Modify the `config` section in [scenarios.yaml](examples/nikkei_shock/scenarios.yaml):

```yaml
config:
  target_loss_ratio: 0.25   # 25% loss is "severe" (adjust based on risk tolerance)
  target_joint_sigma: 3.0   # 3σ joint shock is "crisis-like" (Mahalanobis distance)
```

Higher `target_loss_ratio` demands more damaging shocks; higher `target_joint_sigma` tolerates larger factor moves.

### Using Different LLM Models

Modify variant configs to use different models:

```yaml
# configs/variant/your_custom_variant.yaml
evaluate_function:
  llm_judge:
    model_names: "anthropic::claude-3.5-sonnet"  # Or "ollama::qwen2.5-coder:14b"
    temperatures: 0.0
    max_tokens: 8196

evo_config:
  llm_models:
    - "anthropic::claude-3.5-sonnet"  # Coder model
```

Supported prefixes: `openai::`, `anthropic::`, `google::`, `ollama::`

### Modifying Judge Criteria

Edit the `SYSTEM_MSG` in [feedback.py](examples/nikkei_shock/feedback.py:10-38) to change what the LLM judge evaluates. Current criteria:
1. Correctly identifies net exposures and hedge intent
2. Identifies structural weaknesses and failure modes
3. Consistency with data
4. Cross-asset interaction insights
5. Technical accuracy and clarity

Add domain-specific criteria (e.g., regulatory compliance, operational feasibility) as needed.

### Extending to Other Asset Classes

The framework is designed for cross-asset portfolios but can be adapted:

1. **Fixed Income**: Add duration, convexity, spread DV01 to `Instrument`
2. **Commodities**: Add commodity delta, curve risk, storage costs
3. **Credit**: Add default correlation, recovery rates, spread sensitivities
4. **Multi-Currency**: Extend FX sensitivities to multiple currency pairs

Modify [scenario.py](examples/nikkei_shock/scenario.py) dataclasses and [quant_utils.py](examples/nikkei_shock/quant_utils.py) P&L calculations accordingly.

## License & Credits

MIT license (see LICENSE). Based on [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve); please cite their [arXiv paper](https://arxiv.org/abs/2509.19349).
