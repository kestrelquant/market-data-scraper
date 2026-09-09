from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class SqliteSink:
    def __init__(self, path: str | Path, table: str, fieldnames: list[str]):
        self.table = table
        self._conn = sqlite3.connect(path)
        cols = ", ".join(f'"{f}" REAL' if f != "asset" else f'"{f}" TEXT' for f in fieldnames)
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})')
        self._conn.commit()
        self._fieldnames = fieldnames

    def write(self, rows: Iterable[dict]) -> None:
        placeholders = ", ".join("?" for _ in self._fieldnames)
        cols = ", ".join(f'"{f}"' for f in self._fieldnames)
        for row in rows:
            values = [row[f] for f in self._fieldnames]
            self._conn.execute(f'INSERT INTO "{self.table}" ({cols}) VALUES ({placeholders})', values)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
