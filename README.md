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
- v1 execution mode: paper trading only (no live order placement).

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

## Notes

- `.env` is ignored by git.
- Tickertape and yfinance are unofficial/public interfaces and may change.
- Dhan adapter is intentionally not wired for live trading in v1.
