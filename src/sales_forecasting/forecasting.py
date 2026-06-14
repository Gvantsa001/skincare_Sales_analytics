from __future__ import annotations

import math
from datetime import date

from .charts import png_bar_chart, svg_line_chart
from .config import FIGURES_DIR, PROCESSED_DIR, TABLES_DIR, ensure_directories
from .io_utils import as_float, money, read_csv, write_csv


TEST_MONTHS = 6
SEASONAL_PERIOD = 12


def mae(actual: list[float], predicted: list[float]) -> float:
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def rmse(actual: list[float], predicted: list[float]) -> float:
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))


def mape(actual: list[float], predicted: list[float]) -> float:
    usable = [(a, p) for a, p in zip(actual, predicted) if a]
    return sum(abs((a - p) / a) for a, p in usable) / len(usable) * 100


def add_months(month: str, offset: int) -> str:
    year = int(month[:4])
    month_num = int(month[5:7]) + offset
    year += (month_num - 1) // 12
    month_num = ((month_num - 1) % 12) + 1
    return f"{year:04d}-{month_num:02d}-01"


def seasonal_naive(history: list[float], horizon: int, period: int = SEASONAL_PERIOD) -> list[float]:
    if len(history) < period:
        return [history[-1]] * horizon
    return [history[-period + (idx % period)] for idx in range(horizon)]


def arima_fallback(history: list[float], horizon: int) -> tuple[list[float], str]:
    if len(history) < 4:
        return [history[-1]] * horizon, "fallback: naive due to short history"
    diffs = [history[idx] - history[idx - 1] for idx in range(1, len(history))]
    x_values = diffs[:-1]
    y_values = diffs[1:]
    denominator = sum(x * x for x in x_values)
    phi = sum(x * y for x, y in zip(x_values, y_values)) / denominator if denominator else 0.0
    phi = max(-0.85, min(0.85, phi))
    last_value = history[-1]
    last_diff = diffs[-1]
    forecast = []
    for _ in range(horizon):
        next_diff = phi * last_diff
        last_value = max(0.0, last_value + next_diff)
        forecast.append(last_value)
        last_diff = next_diff
    return forecast, f"standard-library ARIMA(1,1,0) fallback; phi={phi:.3f}"


def arima_forecast(history: list[float], horizon: int) -> tuple[list[float], str]:
    try:
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore

        model = ARIMA(history, order=(1, 1, 1))
        results = model.fit()
        return [max(0.0, float(value)) for value in results.forecast(horizon)], "statsmodels ARIMA(1,1,1)"
    except Exception:
        return arima_fallback(history, horizon)


def holt_winters(history: list[float], horizon: int, period: int = SEASONAL_PERIOD) -> tuple[list[float], str]:
    if len(history) < period * 2:
        return seasonal_naive(history, horizon, min(period, len(history))), "fallback: seasonal naive due to short history"
    candidates = [
        (0.25, 0.03, 0.05),
        (0.35, 0.05, 0.08),
        (0.45, 0.08, 0.10),
        (0.55, 0.10, 0.12),
    ]
    best_score = float("inf")
    best_forecast: list[float] = []
    best_params = candidates[0]

    initial_level = sum(history[:period]) / period
    initial_trend = (sum(history[period : 2 * period]) / period - initial_level) / period
    for alpha, beta, gamma in candidates:
        level = initial_level
        trend = initial_trend
        seasonals = [history[idx] - initial_level for idx in range(period)]
        fitted = []
        for idx, value in enumerate(history):
            season = seasonals[idx % period]
            fitted.append(level + trend + season)
            previous_level = level
            level = alpha * (value - season) + (1 - alpha) * (level + trend)
            trend = beta * (level - previous_level) + (1 - beta) * trend
            seasonals[idx % period] = gamma * (value - level) + (1 - gamma) * season
        score = mae(history[period:], fitted[period:])
        if score < best_score:
            best_score = score
            best_params = (alpha, beta, gamma)
            best_forecast = [
                max(0.0, level + (step + 1) * trend + seasonals[(len(history) + step) % period])
                for step in range(horizon)
            ]
    return best_forecast, f"additive Holt-Winters alpha={best_params[0]:.2f}, beta={best_params[1]:.2f}, gamma={best_params[2]:.2f}"


def prophet_forecast(months: list[str], history: list[float], horizon: int) -> tuple[list[float] | None, str]:
    try:
        import pandas as pd  # type: ignore
        from prophet import Prophet  # type: ignore

        frame = pd.DataFrame({"ds": months, "y": history})
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(frame)
        future = model.make_future_dataframe(periods=horizon, freq="MS")
        forecast = model.predict(future).tail(horizon)
        return [max(0.0, float(value)) for value in forecast["yhat"].tolist()], "prophet available"
    except Exception as exc:
        return None, f"skipped: {exc.__class__.__name__}"


def build_model_forecasts(months: list[str], values: list[float], horizon: int) -> dict[str, tuple[list[float], str]]:
    forecasts: dict[str, tuple[list[float], str]] = {
        "Seasonal Naive": (seasonal_naive(values, horizon), "previous-year same-month sales"),
    }
    arima_values, arima_note = arima_forecast(values, horizon)
    forecasts["ARIMA"] = (arima_values, arima_note)
    hw_values, hw_note = holt_winters(values, horizon)
    forecasts["Holt-Winters Exponential Smoothing"] = (hw_values, hw_note)
    prophet_values, prophet_note = prophet_forecast(months, values, horizon)
    if prophet_values is not None:
        forecasts["Prophet"] = (prophet_values, prophet_note)
    else:
        forecasts["Prophet"] = ([], prophet_note)
    return forecasts


def run_forecasting() -> dict[str, int]:
    ensure_directories()
    monthly_rows = read_csv(PROCESSED_DIR / "Monthly_Sales_Features.csv")
    months = [row["month_start"] for row in monthly_rows]
    sales = [as_float(row["total_sales"]) for row in monthly_rows]
    split_idx = len(sales) - TEST_MONTHS
    train_months = months[:split_idx]
    train = sales[:split_idx]
    test_months = months[split_idx:]
    test = sales[split_idx:]

    test_forecasts = build_model_forecasts(train_months, train, TEST_MONTHS)
    prediction_rows: list[dict] = []
    metric_rows: list[dict] = []
    forecast_columns = ["seasonal_naive", "arima", "holt_winters_exponential_smoothing", "prophet"]

    for idx, month in enumerate(test_months):
        row = {
            "month_start": month,
            "actual_sales": money(test[idx]),
            "seasonal_naive": "",
            "arima": "",
            "holt_winters_exponential_smoothing": "",
            "prophet": "",
        }
        for model_name, (forecast, _) in test_forecasts.items():
            column = model_name.lower().replace(" ", "_").replace("-", "_")
            if forecast:
                row[column] = money(forecast[idx])
        prediction_rows.append(row)

    for model_name, (forecast, note) in test_forecasts.items():
        if forecast:
            metric_rows.append(
                {
                    "model_name": model_name,
                    "train_start": train_months[0],
                    "train_end": train_months[-1],
                    "test_start": test_months[0],
                    "test_end": test_months[-1],
                    "mae": money(mae(test, forecast)),
                    "rmse": money(rmse(test, forecast)),
                    "mape": f"{mape(test, forecast):.2f}",
                    "notes": note,
                }
            )
        else:
            metric_rows.append(
                {
                    "model_name": model_name,
                    "train_start": train_months[0],
                    "train_end": train_months[-1],
                    "test_start": test_months[0],
                    "test_end": test_months[-1],
                    "mae": "",
                    "rmse": "",
                    "mape": "",
                    "notes": note,
                }
            )

    available_metrics = [row for row in metric_rows if row["rmse"]]
    best_model = min(available_metrics, key=lambda row: as_float(row["rmse"]))["model_name"]
    future_horizon = 12
    full_forecasts = build_model_forecasts(months, sales, future_horizon)
    future_rows: list[dict] = []
    for model_name, (forecast, note) in full_forecasts.items():
        if not forecast:
            future_rows.append({"month_start": "", "model_name": model_name, "forecast_sales": "", "notes": note})
            continue
        for idx, value in enumerate(forecast, start=1):
            future_rows.append(
                {
                    "month_start": add_months(months[-1], idx),
                    "model_name": model_name,
                    "forecast_sales": money(value),
                    "notes": note,
                }
            )

    counts = {
        "forecasting_metrics": write_csv(
            TABLES_DIR / "forecasting_metrics.csv",
            metric_rows,
            ["model_name", "train_start", "train_end", "test_start", "test_end", "mae", "rmse", "mape", "notes"],
        ),
        "forecast_predictions": write_csv(
            TABLES_DIR / "forecast_predictions.csv",
            prediction_rows,
            ["month_start", "actual_sales", *forecast_columns],
        ),
        "future_forecast": write_csv(TABLES_DIR / "future_forecast.csv", future_rows, ["month_start", "model_name", "forecast_sales", "notes"]),
    }
    # Compatibility copies for earlier project naming.
    write_csv(TABLES_DIR / "forecast_accuracy.csv", metric_rows, ["model_name", "train_start", "train_end", "test_start", "test_end", "mae", "rmse", "mape", "notes"])
    write_csv(PROCESSED_DIR / "forecast_predictions.csv", prediction_rows, ["month_start", "actual_sales", *forecast_columns])
    write_csv(PROCESSED_DIR / "future_forecast.csv", future_rows, ["month_start", "model_name", "forecast_sales", "notes"])

    png_bar_chart(
        FIGURES_DIR / "model_comparison_chart.png",
        [(row["model_name"], as_float(row["rmse"])) for row in available_metrics],
    )
    svg_line_chart(
        FIGURES_DIR / "monthly_sales_forecast_test_actuals.svg",
        [(row["month_start"], as_float(row["actual_sales"])) for row in prediction_rows],
        f"Monthly Forecast Test Actuals, Best Model: {best_model}",
        width=900,
    )
    (TABLES_DIR / "model_run_notes.md").write_text(
        "# Forecast Model Notes\n\n"
        f"- Classical forecasting grain: monthly sales.\n"
        f"- Train window: {train_months[0]} through {train_months[-1]}.\n"
        f"- Test window: {test_months[0]} through {test_months[-1]}.\n"
        f"- Best available model by RMSE: {best_model}.\n"
        "- Prophet is attempted automatically when `prophet` and `pandas` are installed.\n",
        encoding="utf-8",
    )
    return counts

