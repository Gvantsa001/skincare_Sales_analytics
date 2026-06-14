from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sales_forecasting.forecasting import run_forecasting


if __name__ == "__main__":
    print(run_forecasting())

