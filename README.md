# Stocks Analyser

Python stock analysis and paper-trading agent for Indian equities.

## What it does

- Pulls fundamentals universe from Tickertape screener.
- Pulls historical OHLC candles from yfinance.
- Computes indicators: SMA(20/50), EMA, MACD, RSI(14), Bollinger Bands.
- Applies buy gate: indicators first, then fundamentals (PE, promoter holding, revenue growth, profit growth).
- Runs paper-trading logic and stores open positions.
- Re-evaluates held positions and triggers sell rules.
- Persists signals and decisions in SQLite.
- Provides a Streamlit dashboard for monitoring.

## Data strategy

- v1 indicator history source: yfinance.
- Production live minute data seam: Dhan adapter module.
- Default execution mode is paper (`APP_MODE=dev`); live order attempts are enabled in `APP_MODE=prod`.
- Optional LLM audit cross-check: NVIDIA build.nvidia.com compatible API.

## Runtime Modes

The app now supports two runtime modes via `APP_MODE`:

- `dev`: runs statistical strategy, performs a Dhan API-state health check, and executes paper buy/sell simulation.
- `prod`: runs statistical strategy, logs all actions, and attempts live Dhan market order execution for BUY/SELL.

For `prod` mode, set `DHAN_SYMBOL_SECURITY_MAP` in `.env` so symbols resolve to Dhan security IDs.
Example:

```dotenv
DHAN_SYMBOL_SECURITY_MAP={"TCS":"11536","INFY":"1594"}
```

## Optional LLM Cross-Check (Audit)

Use this only as a second opinion over the statistical decision engine.

1. Add values in `.env`:

	- `LLM_CROSSCHECK_MODE=audit_only`
	- `NVIDIA_API_KEY=<your_key>`
	- Optional: `NVIDIA_MODEL`, `NVIDIA_BASE_URL`, `NVIDIA_TIMEOUT_SECONDS`

2. Run a cycle as usual.

In `audit_only` mode, trading actions remain rule-based; LLM outputs are logged for comparison.

## Setup

1. Create virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and set values.
3. Run one cycle or start dashboard.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

Run one analysis cycle:

```bash
PYTHONPATH=src python scripts/run_cycle.py
```

Run hourly scheduler:

```bash
PYTHONPATH=src python scripts/run_scheduler.py
```

Run dashboard:

```bash
streamlit run app.py
```

## Project Documentation

- Planning and implementation notes: [Thought_process.md](Thought_process.md)
- Knowledge graph setup and usage: [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md)

## Knowledge Graph (Graphify)

This repo can be mapped into a knowledge graph using graphify.

Quick path:

```bash
pip install graphifyy
graphify install --platform codex
```

Then in your assistant, run:

```text
/graphify .
```

Expected outputs are created in `graphify-out/`, including `GRAPH_REPORT.md`, `graph.json`, and `graph.html`.

## Notes

- `.env` is ignored by git.
- Tickertape and yfinance are unofficial/public interfaces and may change.
- Dhan adapter is intentionally not wired for live trading in v1.
