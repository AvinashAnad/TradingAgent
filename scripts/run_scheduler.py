from __future__ import annotations

from stocks_analyser.config import Settings
from stocks_analyser.engine import build_engine
from stocks_analyser.scheduler import HourlyScheduler


def main() -> None:
    settings = Settings.load()
    engine = build_engine(settings)
    scheduler = HourlyScheduler(engine=engine, interval_minutes=settings.schedule_interval_minutes)
    scheduler.run_forever()


if __name__ == "__main__":
    main()
