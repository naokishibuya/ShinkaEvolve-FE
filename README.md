# ShinkaEvolve-FE (Financial Engineering)

ShinkaEvolve-FE is a focused fork of [SakanaAI's ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) that applies its LLM-driven program evolution to Japanese financial engineering problems. The initial release ships with a Nikkei-225 option-hedging lab where Shinka mutates hedging policies against a Monte Carlo simulator and validates winners on held-out market scenarios. All upstream examples remain, but this README spotlights the FE workflow and the new Ollama integration for local LLMs.

## Feature Highlights

- **Nikkei Hedging Task** (`examples/nikkei_hedger/`): simulator, scenario generators, evaluator, evolution runner, and visualization helpers.
- **Hold-out evaluation hook** built into `examples/nikkei_hedger/run_evo.py` so the best program is automatically tested on unseen scenarios.
- **Native Ollama support** (`shinka/llm/models/ollama.py`): use `ollama::model-name` in any config to run local chat or embedding models alongside cloud providers.

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
ollama pull nomic-embed-text
ollama pull codegemma:7b
```

## Choosing LLMs & Embeddings

- Cloud keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) still apply. 
- Ollama honors `OLLAMA_BASE_URL` / `OLLAMA_TIMEOUT` env vars.

## Nikkei Hedging Quick Start

1. Generate market scenarios (train + hold-out).

```bash
python examples/nikkei_hedger/scenarios.py
```

This creates `examples/nikkei_hedger/.scenarios/nikkei_day21/` and `nikkei_day21_holdout/`.

2. Run evolution with hold-out evaluation.

```bash
python examples/nikkei_hedger/run_evo.py
```

The results will be generated under `results/nikkei_hedger/`.

3. Using shinka_launch.

To run FE tasks via Hydra configs (`configs/task/nikkei_hedger.yaml`):

```bash
shinka_launch variant=nikkei_hedger
```

## Directory Highlights

| Path | Purpose |
|------|---------|
| `examples/nikkei_hedger/` | Monte Carlo hedger lab (simulator, evaluator, runner, viz). |
| `shinka/llm/models/ollama.py` | Ollama chat/embedding adapter. |
| `examples/circle_packing`, `examples/ale_bench`, ... | Upstream examples (unchanged). |
| `docs/` | Upstream docs (Getting Started, WebUI, Configuration, etc.). |

## License & Credits

MIT license (see LICENSE). Based on [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve); please cite their [arXiv paper](https://arxiv.org/abs/2509.19349).
