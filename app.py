from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stocks_analyser.config import Settings
from stocks_analyser.engine import build_engine
from stocks_analyser.storage import SQLiteStore


st.set_page_config(page_title="Stocks Analyser", layout="wide")
st.title("Stocks Analyser - Mode Aware Dashboard")

settings = Settings.load()
store = SQLiteStore(settings.sqlite_path)

with st.sidebar:
    st.subheader("Runtime")
    st.write(f"Mode: {settings.app_mode}")
    st.write(f"Execution: {'LIVE' if settings.app_mode.strip().lower() == 'prod' else 'PAPER'}")
    st.write(f"Max Stocks: {settings.max_stocks}")
    st.write(f"Interval: {settings.schedule_interval_minutes} min")

    if st.button("Run Analysis Cycle Now", type="primary"):
        engine = build_engine(settings)
        with st.spinner("Running analysis cycle..."):
            counts = engine.run_cycle()
        st.success(f"Cycle complete: {counts}")

positions = store.get_open_positions()
position_df = pd.DataFrame(
    [
        {
            "symbol": p.symbol,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "entry_time": p.entry_time.isoformat(),
        }
        for p in positions
    ]
)

signals = store.latest_signals(limit=200)
signals_df = pd.DataFrame(
    [
        {
            "symbol": row["symbol"],
            "name": row["name"],
            "timestamp": row["ts"],
            "price": row["price"],
            "score": row["score"],
            "action": row["action"],
            "llm_action": row["llm_action"],
            "llm_confidence": row["llm_confidence"],
            "reasons": "; ".join(json.loads(row["reasons_json"])),
        }
        for row in signals
    ]
)

decisions = store.latest_decisions(limit=200)
decisions_df = pd.DataFrame(
    [
        {
            "symbol": row["symbol"],
            "timestamp": row["ts"],
            "action": row["action"],
            "llm_action": row["llm_action"],
            "llm_confidence": row["llm_confidence"],
            "price": row["price"],
            "score": row["score"],
            "reasons": "; ".join(json.loads(row["reasons_json"])),
            "llm_rationale": row["llm_rationale"],
        }
        for row in decisions
    ]
)

executions = store.latest_executions(limit=200)
executions_df = pd.DataFrame(
    [
        {
            "timestamp": row["ts"],
            "symbol": row["symbol"],
            "action": row["action"],
            "mode": row["mode"],
            "execution_type": row["execution_type"],
            "status": row["status"],
            "message": row["message"],
            "broker_order_id": row["broker_order_id"],
        }
        for row in executions
    ]
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Open Positions")
    if position_df.empty:
        st.info("No open paper positions")
    else:
        st.dataframe(position_df, use_container_width=True)

with col2:
    st.subheader("Latest Decisions")
    if decisions_df.empty:
        st.info("No decisions logged yet")
    else:
        st.dataframe(decisions_df, use_container_width=True)

st.subheader("Latest Signals")
if signals_df.empty:
    st.info("No signals logged yet")
else:
    st.dataframe(signals_df, use_container_width=True)

st.subheader("Execution Logs")
if executions_df.empty:
    st.info("No execution logs yet")
else:
    st.dataframe(executions_df, use_container_width=True)
