# Thought Process and Build Notes

## 1) Objective

Build an Indian equities stock analyser agent that:

- Uses popular technical indicators to detect buy/sell opportunities.
- Uses market/fundamental checks (PE, promoter holding, revenue, profit).
- Buys only when technical + fundamental conditions pass.
- Continues monitoring held positions and triggers sell decisions for long-term strategy.
- Keeps sensitive configuration in .env and prevents accidental commits.

## 2) Requirement Summary Captured During Planning

- Market scope: India NSE/BSE equities.
- Indicator scope for v1: SMA(20/50), EMA, MACD, RSI, Bollinger Bands.
- Decision cadence: hourly evaluation.
- Execution mode in v1: paper trading only (no live order placement).
- UI preference: simple web dashboard.
- Data strategy finalization:
  - Historical indicator inputs: yfinance.
  - Production live minute data: broker API adapter, selected broker target is Dhan.

## 3) Initial External Repo Analysis (Tickertape-Screener-unofficial)

The starting reference repository was analyzed before implementation.

Key findings captured from that analysis:

- Source format is notebook-centric (single app.ipynb).
- Uses Tickertape screener endpoint with POST payload filters, projection fields, pagination and sorting.
- Has reusable patterns for:
  - pagination (offset + count)
  - JSON parsing
  - tabular conversion
- Risks identified up front:
  - unofficial API behavior can change
  - rate limits not well documented
  - uneven field naming in responses
  - technical indicator availability from Tickertape not guaranteed in one schema

Implication for architecture:

- Reuse Tickertape for fundamentals/universe discovery.
- Use yfinance as technical indicator candle source for v1 reliability/speed.
- Keep broker integration behind adapter boundary for production live mode.

## 4) Architecture Decisions and Why

### 4.1 Data source split

- Tickertape: universe + fundamentals.
- yfinance: historical OHLC used for indicator computation.
- Dhan: production live minute data seam, not active for live order flow in v1.

Reason:

- Fastest path to a working system while preserving a clean production migration path.

### 4.2 Strategy ordering

- Technical gate first (score threshold).
- Fundamentals gate second.

Reason:

- User requirement explicitly asked for indicator-based buy condition first, then market status checks.

### 4.3 Persistence choice

- SQLite for positions, signals, and decisions.

Reason:

- Lightweight, local, simple to inspect, adequate for v1 paper trading.

### 4.4 Product surface

- Streamlit dashboard.

Reason:

- Fastest way to deliver interactive monitoring and manual run trigger for v1.

## 5) Detailed Strategy Model Implemented

### 5.1 Indicators calculated

- SMA20, SMA50
- EMA20, EMA50
- MACD and MACD signal line
- RSI14
- Bollinger Bands (middle/upper/lower)

### 5.2 Indicator scoring checks

The score is currently a sum of 5 checks:

1. SMA trend check: SMA20 > SMA50 and close >= SMA20
2. EMA trend check: EMA20 > EMA50
3. MACD momentum check: MACD > signal
4. RSI regime check: RSI in [40, 70]
5. Bollinger location check: close between middle and upper band

### 5.3 Buy rule

- If score < MIN_SIGNAL_SCORE -> HOLD.
- If score threshold passes, then validate fundamentals:
  - PE <= MAX_PE
  - Promoter holding >= MIN_PROMOTER_HOLDING
  - Revenue growth >= MIN_REVENUE_GROWTH
  - Profit growth >= MIN_PROFIT_GROWTH
- If all pass -> BUY; else HOLD with explicit reasons.

### 5.4 Sell rule

For open positions, SELL if any of these are true:

- score <= SELL_SIGNAL_SCORE
- PnL <= -STOP_LOSS_PCT
- PnL >= TAKE_PROFIT_PCT

Else HOLD.

## 6) Repository Implementation Map

### Core configuration and models

- src/stocks_analyser/config.py
- src/stocks_analyser/models.py

### Data providers

- src/stocks_analyser/data/tickertape_client.py
- src/stocks_analyser/data/yfinance_provider.py
- src/stocks_analyser/data/dhan_adapter.py

### Analysis and strategy

- src/stocks_analyser/indicators.py
- src/stocks_analyser/strategy.py

### Execution and storage

- src/stocks_analyser/storage.py
- src/stocks_analyser/engine.py
- src/stocks_analyser/scheduler.py

### Run scripts and app

- scripts/run_cycle.py
- scripts/run_scheduler.py
- app.py

### Setup and docs

- .env.example
- .gitignore
- requirements.txt
- pyproject.toml
- README.md
- tests/test_indicators.py

## 7) End-to-End Runtime Flow (Current)

1. Load settings from .env.
2. Fetch fundamentals universe from Tickertape (paginated).
3. Merge with currently open position symbols.
4. Pull OHLC from yfinance per symbol and compute indicator snapshot.
5. If symbol not held: evaluate BUY policy.
6. If symbol held: evaluate SELL policy.
7. Persist signal row and decision log row.
8. Maintain open positions table accordingly.
9. Show state in Streamlit dashboard.

## 8) Configuration and Secret Handling

- .env.example defines all tunable values and placeholders.
- .env is expected locally and is git-ignored.
- Dhan credentials are represented as env variables and not hardcoded.

## 9) Validation Performed During Build

What was verified:

- Workspace diagnostics reported no editor errors.
- Python source compilation check passed over src, scripts, app, tests.

Constraint encountered:

- The execution environment lacked pip/ensurepip, so dependency-based unit test execution could not be completed there.
- This is an environment setup issue, not a source syntax issue.

## 10) Known Limitations in v1

- Tickertape is an unofficial/public interface and can change.
- yfinance minute/intraday characteristics can vary by symbol and availability window.
- Dhan adapter currently acts as production seam only; no live trading execution path is enabled in v1.
- No advanced portfolio sizing model yet (default quantity path is simple for paper mode).

## 11) Planned Next Iterations

1. Add robust Dhan instrument mapping and verified minute-candle contract for production mode.
2. Add integration tests with mocked Tickertape and yfinance responses.
3. Add backtest mode and performance metrics (win rate, drawdown, CAGR-like long-horizon reporting).
4. Add stronger risk controls (position sizing, max concurrent positions, sector exposure caps).
5. Add better observability (structured logs and failure dashboards).

## 12) Build Philosophy Used

- Keep v1 thin but complete end-to-end.
- Separate data providers from strategy logic.
- Make behavior threshold-driven via env settings.
- Persist every decision to allow traceability and later tuning.
- Avoid live execution until paper logic is stable.
