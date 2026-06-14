from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
            count += 1
    return count


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(value: str | int | float | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def as_int(value: str | int | float | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def money(value: float) -> str:
    return f"{value:.2f}"

