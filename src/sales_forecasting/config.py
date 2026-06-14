from __future__ import annotations

from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TABLES_DIR = BASE_DIR / "reports" / "tables"
FIGURES_DIR = BASE_DIR / "reports" / "figures"
POWERBI_DIR = BASE_DIR / "PowerBI"

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
SEED = 42731

TAX_RATE = 0.0825
FREE_SHIPPING_THRESHOLD = 55.0
BASE_SHIPPING_FEE = 5.95


def ensure_directories() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, TABLES_DIR, FIGURES_DIR, POWERBI_DIR]:
        path.mkdir(parents=True, exist_ok=True)

