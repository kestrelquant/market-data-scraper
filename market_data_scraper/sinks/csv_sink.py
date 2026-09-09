from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


class CsvSink:
    def __init__(self, path: str | Path, fieldnames: list[str]):
        self.path = Path(path)
        self.fieldnames = fieldnames
        is_new = not self.path.exists()
        self._file = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        if is_new:
            self._writer.writeheader()

    def write(self, rows: Iterable[dict]) -> None:
        for row in rows:
            self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
