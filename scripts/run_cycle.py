from __future__ import annotations

from stocks_analyser.config import Settings
from stocks_analyser.engine import build_engine


def main() -> None:
    settings = Settings.load()
    engine = build_engine(settings)
    counts = engine.run_cycle()
    print("Cycle summary:", counts)


if __name__ == "__main__":
    main()
