from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from src.sales_forecasting.analytics import run_analytics
from src.sales_forecasting.cleaning import clean_and_process
from src.sales_forecasting.forecasting import run_forecasting
from src.sales_forecasting.validation import validate_data


def main() -> None:
    steps = [
        ("clean_and_process", clean_and_process),
        ("validate_data", validate_data),
        ("run_analytics", run_analytics),
        ("run_forecasting", run_forecasting)
    ]
    for name, func in steps:
        result = func()
        print(f"{name}: {result}")


if __name__ == "__main__":
    main()
