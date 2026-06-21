from __future__ import annotations

import math
from collections import defaultdict

from .charts import svg_bar_chart, svg_line_chart, svg_scatter_chart
from .config import FIGURES_DIR, PROCESSED_DIR, RAW_DIR, TABLES_DIR, ensure_directories
from .io_utils import as_float, as_int, money, read_csv, write_csv


def pearson_corr(x_values: list[float], y_values: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(x_values, y_values)]

    if len(pairs) < 2:
        return 0.0

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if denominator_x == 0 or denominator_y == 0:
        return 0.0

    return numerator / (denominator_x * denominator_y)


def correlation_strength(value: float) -> str:
    abs_value = abs(value)

    if abs_value >= 0.70:
        return "Strong"
    if abs_value >= 0.40:
        return "Moderate"
    if abs_value >= 0.20:
        return "Weak"

    return "Very weak"


def add_correlation_row(
    rows: list[dict],
    analysis: str,
    variable_1: str,
    variable_2: str,
    correlation: float,
    business_question: str,
) -> None:
    rows.append(
        {
            "analysis": analysis,
            "variable_1": variable_1,
            "variable_2": variable_2,
            "correlation": f"{correlation:.4f}",
            "direction": "Positive" if correlation > 0 else "Negative" if correlation < 0 else "No relationship",
            "strength": correlation_strength(correlation),
            "business_question": business_question,
        }
    )


def build_correlation_rows(
    daily: list[dict],
    product_features: list[dict],
    customer_features: list[dict],
) -> list[dict]:
    rows: list[dict] = []

    corr = pearson_corr(
        [as_float(row["total_discount"]) for row in daily],
        [as_float(row["total_sales"]) for row in daily],
    )
    add_correlation_row(
        rows,
        "Daily Discount vs Daily Sales",
        "total_discount",
        "total_sales",
        corr,
        "Do higher discounts increase daily sales?",
    )

    corr = pearson_corr(
        [as_float(row["total_orders"]) for row in daily],
        [as_float(row["total_sales"]) for row in daily],
    )
    add_correlation_row(
        rows,
        "Daily Orders vs Daily Sales",
        "total_orders",
        "total_sales",
        corr,
        "Do more orders lead to higher revenue?",
    )

    corr = pearson_corr(
        [as_float(row["avg_discount_pct"]) for row in product_features],
        [as_float(row["total_sales"]) for row in product_features],
    )
    add_correlation_row(
        rows,
        "Product Discount vs Product Revenue",
        "avg_discount_pct",
        "total_sales",
        corr,
        "Do discounted products generate more revenue?",
    )

    corr = pearson_corr(
        [as_float(row["avg_unit_price"]) for row in product_features],
        [as_float(row["units_sold"]) for row in product_features],
    )
    add_correlation_row(
        rows,
        "Product Price vs Units Sold",
        "avg_unit_price",
        "units_sold",
        corr,
        "Do expensive products sell fewer units?",
    )

    corr = pearson_corr(
        [as_float(row["avg_rating"]) for row in product_features],
        [as_float(row["return_rate_by_order"]) for row in product_features],
    )
    add_correlation_row(
        rows,
        "Product Rating vs Return Rate",
        "avg_rating",
        "return_rate_by_order",
        corr,
        "Do lower-rated products have higher return rates?",
    )

    corr = pearson_corr(
        [as_float(row["avg_rating"]) for row in product_features],
        [as_float(row["total_sales"]) for row in product_features],
    )
    add_correlation_row(
        rows,
        "Product Rating vs Product Revenue",
        "avg_rating",
        "total_sales",
        corr,
        "Do higher-rated products generate more revenue?",
    )

    corr = pearson_corr(
        [as_float(row["popularity_score"]) for row in product_features],
        [as_float(row["total_sales"]) for row in product_features],
    )
    add_correlation_row(
        rows,
        "Popularity Score vs Revenue",
        "popularity_score",
        "total_sales",
        corr,
        "Does product popularity explain revenue?",
    )

    corr = pearson_corr(
        [as_float(row["total_orders"]) for row in customer_features],
        [as_float(row["customer_lifetime_value"]) for row in customer_features],
    )
    add_correlation_row(
        rows,
        "Customer Orders vs Customer Lifetime Value",
        "total_orders",
        "customer_lifetime_value",
        corr,
        "Do frequent customers generate higher lifetime value?",
    )

    corr = pearson_corr(
        [as_float(row["recency_days"]) for row in customer_features],
        [as_float(row["total_sales"]) for row in customer_features],
    )
    add_correlation_row(
        rows,
        "Customer Recency vs Revenue",
        "recency_days",
        "total_sales",
        corr,
        "Do recently active customers generate more revenue?",
    )

    return rows


def run_analytics() -> dict[str, int]:
    ensure_directories()

    monthly = read_csv(PROCESSED_DIR / "Monthly_Sales_Features.csv")
    daily = read_csv(PROCESSED_DIR / "Daily_Sales_Features.csv")
    product_features = read_csv(PROCESSED_DIR / "Product_Features.csv")
    customer_features = read_csv(PROCESSED_DIR / "Customer_Features.csv")

    orders = read_csv(RAW_DIR / "Orders.csv")
    order_items = read_csv(RAW_DIR / "Order_Items.csv")
    products = {row["product_id"]: row for row in read_csv(RAW_DIR / "Products.csv")}
    orders_by_id = {row["order_id"]: row for row in orders}

    category_rows = []
    by_category: dict[str, dict] = defaultdict(
        lambda: {
            "units": 0,
            "sales": 0.0,
            "orders": 0,
            "returns": 0,
            "reviews": 0,
            "rating_total": 0.0,
        }
    )

    for product in product_features:
        bucket = by_category[product["category"]]
        bucket["units"] += as_int(product["units_sold"])
        bucket["sales"] += as_float(product["total_sales"])
        bucket["orders"] += as_int(product["order_count"])
        bucket["returns"] += as_int(product["return_count"])
        bucket["reviews"] += as_int(product["review_count"])

        if product["avg_rating"]:
            bucket["rating_total"] += as_float(product["avg_rating"]) * as_int(product["review_count"])

    for category, bucket in sorted(by_category.items()):
        category_rows.append(
            {
                "category": category,
                "units_sold": bucket["units"],
                "total_sales": money(bucket["sales"]),
                "order_count": bucket["orders"],
                "return_count": bucket["returns"],
                "review_count": bucket["reviews"],
                "avg_rating": f"{bucket['rating_total'] / bucket['reviews']:.2f}" if bucket["reviews"] else "",
                "return_rate_by_order": f"{bucket['returns'] / bucket['orders']:.4f}" if bucket["orders"] else "0.0000",
            }
        )

    channel: dict[str, dict] = defaultdict(
        lambda: {
            "orders": 0,
            "gross": 0.0,
            "discount": 0.0,
            "sales": 0.0,
        }
    )

    for order in orders:
        if order["order_status"] != "Delivered":
            continue

        bucket = channel[order["sales_channel"]]
        bucket["orders"] += 1
        bucket["gross"] += as_float(order["gross_amount"])
        bucket["discount"] += as_float(order["discount_amount"])
        bucket["sales"] += as_float(order["final_amount"])

    channel_rows = [
        {
            "sales_channel": key,
            "total_orders": value["orders"],
            "gross_sales": money(value["gross"]),
            "total_discount": money(value["discount"]),
            "total_sales": money(value["sales"]),
            "avg_order_value": money(value["sales"] / value["orders"]) if value["orders"] else "0.00",
        }
        for key, value in sorted(channel.items())
    ]

    segment: dict[str, dict] = defaultdict(
        lambda: {
            "customers": 0,
            "orders": 0,
            "sales": 0.0,
            "returns": 0,
        }
    )

    for customer in customer_features:
        bucket = segment[customer["customer_segment"]]
        bucket["customers"] += 1
        bucket["orders"] += as_int(customer["total_orders"])
        bucket["sales"] += as_float(customer["total_sales"])
        bucket["returns"] += as_int(customer["return_count"])

    segment_rows = [
        {
            "customer_segment": key,
            "customers": value["customers"],
            "total_orders": value["orders"],
            "total_sales": money(value["sales"]),
            "return_count": value["returns"],
            "avg_customer_value": money(value["sales"] / value["customers"]) if value["customers"] else "0.00",
        }
        for key, value in sorted(segment.items())
    ]

    top_products = sorted(
        product_features,
        key=lambda row: as_float(row["popularity_score"]),
        reverse=True,
    )[:25]

    long_tail_products = sorted(
        product_features,
        key=lambda row: as_float(row["popularity_score"]),
    )[:25]

    product_rank_rows = [
        {
            "rank_type": "Top 25",
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "category": row["category"],
            "total_sales": row["total_sales"],
            "units_sold": row["units_sold"],
            "popularity_score": row["popularity_score"],
        }
        for row in top_products
    ] + [
        {
            "rank_type": "Long Tail 25",
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "category": row["category"],
            "total_sales": row["total_sales"],
            "units_sold": row["units_sold"],
            "popularity_score": row["popularity_score"],
        }
        for row in long_tail_products
    ]

    combination_counts: dict[tuple[str, str], int] = defaultdict(int)
    order_categories: dict[str, set[str]] = defaultdict(set)

    for item in order_items:
        order = orders_by_id[item["order_id"]]

        if order["order_status"] == "Delivered":
            order_categories[item["order_id"]].add(products[item["product_id"]]["category"])

    for categories in order_categories.values():
        sorted_categories = sorted(categories)

        for idx, first in enumerate(sorted_categories):
            for second in sorted_categories[idx + 1 :]:
                combination_counts[(first, second)] += 1

    combination_rows = [
        {
            "category_1": first,
            "category_2": second,
            "order_count": count,
        }
        for (first, second), count in sorted(
            combination_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:30]
    ]

    correlation_rows = build_correlation_rows(
        daily=daily,
        product_features=product_features,
        customer_features=customer_features,
    )

    counts = {
        "monthly_sales_summary": write_csv(
            TABLES_DIR / "monthly_sales_summary.csv",
            monthly,
            [
                "month_start",
                "total_sales",
                "total_orders",
                "gross_sales",
                "total_discount",
                "units_sold",
                "return_count",
                "review_count",
                "avg_rating",
                "avg_order_value",
                "return_rate",
                "sales_lag_1m",
                "sales_lag_3m",
                "sales_lag_12m",
                "rolling_3m_sales",
                "rolling_6m_sales",
                "sales_growth_mom_pct",
                "seasonality_index",
            ],
        ),
        "category_summary": write_csv(
            TABLES_DIR / "category_summary.csv",
            category_rows,
            [
                "category",
                "units_sold",
                "total_sales",
                "order_count",
                "return_count",
                "review_count",
                "avg_rating",
                "return_rate_by_order",
            ],
        ),
        "channel_summary": write_csv(
            TABLES_DIR / "channel_summary.csv",
            channel_rows,
            [
                "sales_channel",
                "total_orders",
                "gross_sales",
                "total_discount",
                "total_sales",
                "avg_order_value",
            ],
        ),
        "customer_segment_summary": write_csv(
            TABLES_DIR / "customer_segment_summary.csv",
            segment_rows,
            [
                "customer_segment",
                "customers",
                "total_orders",
                "total_sales",
                "return_count",
                "avg_customer_value",
            ],
        ),
        "product_rank_summary": write_csv(
            TABLES_DIR / "product_rank_summary.csv",
            product_rank_rows,
            [
                "rank_type",
                "product_id",
                "product_name",
                "category",
                "total_sales",
                "units_sold",
                "popularity_score",
            ],
        ),
        "product_combination_summary": write_csv(
            TABLES_DIR / "product_combination_summary.csv",
            combination_rows,
            [
                "category_1",
                "category_2",
                "order_count",
            ],
        ),
        "correlation_analysis": write_csv(
            TABLES_DIR / "correlation_analysis.csv",
            correlation_rows,
            [
                "analysis",
                "variable_1",
                "variable_2",
                "correlation",
                "direction",
                "strength",
                "business_question",
            ],
        ),
    }

    svg_line_chart(
        FIGURES_DIR / "daily_total_sales.svg",
        [(row["date"], as_float(row["total_sales"])) for row in daily],
        "Daily Total Sales, 2023-2025",
    )

    svg_bar_chart(
        FIGURES_DIR / "monthly_total_sales.svg",
        [(row["month_start"], as_float(row["total_sales"])) for row in monthly],
        "Monthly Total Sales",
        width=1200,
    )

    svg_bar_chart(
        FIGURES_DIR / "category_total_sales.svg",
        [(row["category"], as_float(row["total_sales"])) for row in category_rows],
        "Total Sales by Category",
    )

    svg_scatter_chart(
        FIGURES_DIR / "discount_vs_sales.svg",
        [
            (as_float(row["total_discount"]), as_float(row["total_sales"]))
            for row in daily
            if as_float(row["total_sales"]) > 0
        ],
        "Discount vs Sales",
        "Total Discount",
        "Total Sales",
    )
    return counts

