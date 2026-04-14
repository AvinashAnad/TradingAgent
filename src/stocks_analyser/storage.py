from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from stocks_analyser.models import AnalysisResult, DecisionLog, Position


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
                    reasons_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    price REAL NOT NULL,
                    score INTEGER NOT NULL,
                    reasons_json TEXT NOT NULL
                );
                """
            )

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
                    snapshot_json, fundamentals_json, action, reasons_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

    def log_decision(self, decision: DecisionLog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions(symbol, action, ts, price, score, reasons_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.symbol,
                    decision.action,
                    decision.timestamp.isoformat(),
                    decision.price,
                    decision.score,
                    json.dumps(decision.reasons),
                ),
            )

    def latest_signals(self, limit: int = 200) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT symbol, name, ts, price, score, action, reasons_json
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
                SELECT symbol, action, ts, price, score, reasons_json
                FROM decisions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
