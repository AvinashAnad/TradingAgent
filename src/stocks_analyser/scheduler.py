from __future__ import annotations

import time
from datetime import datetime, timezone

from stocks_analyser.engine import StockAnalyserEngine


class HourlyScheduler:
    def __init__(self, engine: StockAnalyserEngine, interval_minutes: int = 60) -> None:
        self.engine = engine
        self.interval_seconds = max(1, interval_minutes * 60)

    def run_forever(self) -> None:
        while True:
            started = datetime.now(timezone.utc)
            counts = self.engine.run_cycle()
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            print(f"[{started.isoformat()}] cycle complete: {counts} in {duration:.1f}s")
            time.sleep(self.interval_seconds)
