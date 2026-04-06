"""Seed local SQLite history store with 2+ years of daily session ranges."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from data.historical_store import HistoricalStore


def main() -> None:
    store = HistoricalStore()
    db_path = str(store.db_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    store = HistoricalStore()
    print(f"Seeded history DB at {store.db_path}")


if __name__ == "__main__":
    main()
