from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from stocks_analyser.models import AnalysisResult, DecisionLog, ExecutionLog, Position


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    price REAL NOT NULL,
                    score INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    fundamentals_json TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    llm_action TEXT,
                    llm_confidence REAL,
                    llm_rationale TEXT,
                    llm_provider TEXT,
                    llm_model TEXT,
                    llm_mode TEXT
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    price REAL NOT NULL,
                    score INTEGER NOT NULL,
                    reasons_json TEXT NOT NULL,
                    llm_action TEXT,
                    llm_confidence REAL,
                    llm_rationale TEXT,
                    llm_provider TEXT,
                    llm_model TEXT,
                    llm_mode TEXT
                );

                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    execution_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    broker_order_id TEXT
                );
                """
            )
            self._ensure_column(conn, "signals", "llm_action", "TEXT")
            self._ensure_column(conn, "signals", "llm_confidence", "REAL")
            self._ensure_column(conn, "signals", "llm_rationale", "TEXT")
            self._ensure_column(conn, "signals", "llm_provider", "TEXT")
            self._ensure_column(conn, "signals", "llm_model", "TEXT")
            self._ensure_column(conn, "signals", "llm_mode", "TEXT")
            self._ensure_column(conn, "decisions", "llm_action", "TEXT")
            self._ensure_column(conn, "decisions", "llm_confidence", "REAL")
            self._ensure_column(conn, "decisions", "llm_rationale", "TEXT")
            self._ensure_column(conn, "decisions", "llm_provider", "TEXT")
            self._ensure_column(conn, "decisions", "llm_model", "TEXT")
            self._ensure_column(conn, "decisions", "llm_mode", "TEXT")

    def log_execution(self, execution: ExecutionLog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO executions(
                    symbol, action, ts, mode, execution_type, status, message, broker_order_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.symbol,
                    execution.action,
                    execution.timestamp.isoformat(),
                    execution.mode,
                    execution.execution_type,
                    execution.status,
                    execution.message,
                    execution.broker_order_id,
                ),
            )

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")

    def get_open_positions(self) -> list[Position]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT symbol, quantity, entry_price, entry_time FROM positions"
            ).fetchall()

        return [
            Position(
                symbol=row["symbol"],
                quantity=row["quantity"],
                entry_price=row["entry_price"],
                entry_time=datetime.fromisoformat(row["entry_time"]),
            )
            for row in rows
        ]

    def upsert_position(self, position: Position) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO positions(symbol, quantity, entry_price, entry_time)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol)
                DO UPDATE SET quantity=excluded.quantity, entry_price=excluded.entry_price, entry_time=excluded.entry_time
                """,
                (
                    position.symbol,
                    position.quantity,
                    position.entry_price,
                    position.entry_time.isoformat(),
                ),
            )

    def close_position(self, symbol: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))

    def save_signal(self, result: AnalysisResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO signals(
                    symbol, name, ts, price, score,
                    snapshot_json, fundamentals_json, action, reasons_json,
                    llm_action, llm_confidence, llm_rationale, llm_provider, llm_model, llm_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.symbol,
                    result.name,
                    result.timestamp.isoformat(),
                    result.price,
                    result.snapshot.score,
                    json.dumps(result.snapshot.__dict__),
                    json.dumps(result.fundamentals.__dict__),
                    result.action,
                    json.dumps(result.reasons),
                    result.llm_action,
                    result.llm_confidence,
                    result.llm_rationale,
                    result.llm_provider,
                    result.llm_model,
                    result.llm_mode,
                ),
            )

    def log_decision(self, decision: DecisionLog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions(
                    symbol, action, ts, price, score, reasons_json,
                    llm_action, llm_confidence, llm_rationale, llm_provider, llm_model, llm_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.symbol,
                    decision.action,
                    decision.timestamp.isoformat(),
                    decision.price,
                    decision.score,
                    json.dumps(decision.reasons),
                    decision.llm_action,
                    decision.llm_confidence,
                    decision.llm_rationale,
                    decision.llm_provider,
                    decision.llm_model,
                    decision.llm_mode,
                ),
            )

    def latest_signals(self, limit: int = 200) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    symbol, name, ts, price, score, action, reasons_json,
                    llm_action, llm_confidence, llm_rationale, llm_provider, llm_model, llm_mode
                FROM signals
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def latest_decisions(self, limit: int = 200) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    symbol, action, ts, price, score, reasons_json,
                    llm_action, llm_confidence, llm_rationale, llm_provider, llm_model, llm_mode
                FROM decisions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def latest_executions(self, limit: int = 200) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    symbol, action, ts, mode, execution_type, status, message, broker_order_id
                FROM executions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
