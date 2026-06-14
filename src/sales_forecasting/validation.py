from __future__ import annotations

from collections import defaultdict
from datetime import date

from .config import END_DATE, PROCESSED_DIR, RAW_DIR, START_DATE, TABLES_DIR, ensure_directories
from .io_utils import as_float, as_int, read_csv, write_csv


def status(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def validate_data() -> dict[str, int]:
    ensure_directories()
    customers = read_csv(RAW_DIR / "Customers.csv")
    products = read_csv(RAW_DIR / "Products.csv")
    orders = read_csv(RAW_DIR / "Orders.csv")
    order_items = read_csv(RAW_DIR / "Order_Items.csv")
    reviews = read_csv(RAW_DIR / "Reviews.csv")
    returns = read_csv(RAW_DIR / "Returns.csv")
    daily = read_csv(PROCESSED_DIR / "Daily_Sales_Features.csv")
    monthly = read_csv(PROCESSED_DIR / "Monthly_Sales_Features.csv")
    customer_features = read_csv(PROCESSED_DIR / "Customer_Features.csv")
    product_features = read_csv(PROCESSED_DIR / "Product_Features.csv")

    customer_ids = {row["customer_id"] for row in customers}
    product_ids = {row["product_id"] for row in products}
    order_ids = {row["order_id"] for row in orders}
    order_lookup = {row["order_id"]: row for row in orders}
    product_lookup = {row["product_id"]: row for row in products}
    delivered_orders = [row for row in orders if row["order_status"] == "Delivered"]

    checks: list[dict[str, str]] = []
    checks.extend(
        [
            {"check_name": "customers_exactly_5000", "status": status(len(customers) == 5000), "details": str(len(customers))},
            {"check_name": "products_exactly_300", "status": status(len(products) == 300), "details": str(len(products))},
            {"check_name": "orders_at_least_100000", "status": status(len(orders) >= 100000), "details": str(len(orders))},
            {"check_name": "customer_pk_unique", "status": status(len(customer_ids) == len(customers)), "details": f"{len(customer_ids)} unique"},
            {"check_name": "product_pk_unique", "status": status(len(product_ids) == len(products)), "details": f"{len(product_ids)} unique"},
            {"check_name": "order_pk_unique", "status": status(len(order_ids) == len(orders)), "details": f"{len(order_ids)} unique"},
            {
                "check_name": "customers_state_california",
                "status": status(all(row["state"] == "California" for row in customers)),
                "details": "all customers use state California",
            },
            {
                "check_name": "orders_customer_fk",
                "status": status(all(row["customer_id"] in customer_ids for row in orders)),
                "details": "Orders.customer_id references Customers",
            },
            {
                "check_name": "items_order_product_fk",
                "status": status(all(row["order_id"] in order_ids and row["product_id"] in product_ids for row in order_items)),
                "details": "Order_Items references Orders and Products",
            },
            {
                "check_name": "reviews_fk",
                "status": status(all(row["order_id"] in order_ids and row["product_id"] in product_ids and row["customer_id"] in customer_ids for row in reviews)),
                "details": "Reviews references Orders, Products, Customers",
            },
            {
                "check_name": "returns_fk",
                "status": status(all(row["order_id"] in order_ids and row["product_id"] in product_ids for row in returns)),
                "details": "Returns references Orders and Products",
            },
            {
                "check_name": "order_status_mix",
                "status": status(any(row["order_status"] == "Cancelled" for row in orders) and len(delivered_orders) / len(orders) > 0.90),
                "details": f"delivered_share={len(delivered_orders) / len(orders):.3f}",
            },
        ]
    )

    return_after_delivery = True
    for ret in returns:
        order = order_lookup.get(ret["order_id"])
        if not order or not order["delivered_date"]:
            return_after_delivery = False
            break
        if date.fromisoformat(ret["return_date"]) <= date.fromisoformat(order["delivered_date"]):
            return_after_delivery = False
            break
    checks.append(
        {
            "check_name": "returns_after_delivery",
            "status": status(return_after_delivery),
            "details": "all returns occur after delivered_date",
        }
    )

    ratings = [as_int(row["rating"]) for row in reviews]
    avg_rating = sum(ratings) / len(ratings)
    checks.append(
        {
            "check_name": "review_rating_average_around_4_2",
            "status": status(4.0 <= avg_rating <= 4.4),
            "details": f"avg_rating={avg_rating:.3f}",
        }
    )

    total_revenue = sum(as_float(row["total_sales"]) for row in customer_features)
    top_n = max(1, int(len(customer_features) * 0.20))
    top_revenue = sum(as_float(row["total_sales"]) for row in sorted(customer_features, key=lambda r: as_float(r["total_sales"]), reverse=True)[:top_n])
    top_share = top_revenue / total_revenue if total_revenue else 0.0
    checks.append(
        {
            "check_name": "top_20_percent_customers_generate_60_to_70_percent_revenue",
            "status": status(0.60 <= top_share <= 0.70),
            "details": f"top20_share={top_share:.3f}",
        }
    )

    item_units_by_category_month: dict[tuple[str, int], int] = defaultdict(int)
    for item in order_items:
        order = order_lookup[item["order_id"]]
        if order["order_status"] != "Delivered":
            continue
        product = product_lookup[item["product_id"]]
        month = int(order["order_date"][5:7])
        item_units_by_category_month[(product["category"], month)] += as_int(item["quantity"])

    sunscreen_summer = sum(item_units_by_category_month[("Sunscreens", month)] for month in [6, 7, 8]) / 3
    sunscreen_other = sum(item_units_by_category_month[("Sunscreens", month)] for month in [1, 2, 3, 4, 5, 9, 10, 11, 12]) / 9
    moisturizer_winter = sum(item_units_by_category_month[("Moisturizers", month)] for month in [11, 12, 1, 2]) / 4
    moisturizer_other = sum(item_units_by_category_month[("Moisturizers", month)] for month in [3, 4, 5, 6, 7, 8, 9, 10]) / 8
    checks.extend(
        [
            {
                "check_name": "sunscreen_summer_lift",
                "status": status(sunscreen_summer > sunscreen_other * 1.8),
                "details": f"summer_avg={sunscreen_summer:.1f}; other_avg={sunscreen_other:.1f}",
            },
            {
                "check_name": "moisturizer_winter_lift",
                "status": status(moisturizer_winter > moisturizer_other * 1.45),
                "details": f"winter_avg={moisturizer_winter:.1f}; other_avg={moisturizer_other:.1f}",
            },
        ]
    )

    daily_dates = [date.fromisoformat(row["date"]) for row in daily]
    checks.extend(
        [
            {
                "check_name": "daily_feature_full_date_coverage",
                "status": status(len(daily) == (END_DATE - START_DATE).days + 1 and min(daily_dates) == START_DATE and max(daily_dates) == END_DATE),
                "details": f"{len(daily)} rows from {min(daily_dates)} to {max(daily_dates)}",
            },
            {
                "check_name": "monthly_feature_36_rows",
                "status": status(len(monthly) == 36),
                "details": f"{len(monthly)} rows",
            },
            {
                "check_name": "product_feature_300_rows",
                "status": status(len(product_features) == 300),
                "details": f"{len(product_features)} rows",
            },
            {
                "check_name": "return_rate_low",
                "status": status(len(returns) / max(1, len(order_items)) < 0.06),
                "details": f"item_return_rate={len(returns) / max(1, len(order_items)):.4f}",
            },
        ]
    )

    validation_count = write_csv(TABLES_DIR / "validation_report.csv", checks, ["check_name", "status", "details"])
    failed = [row for row in checks if row["status"] != "PASS"]
    (TABLES_DIR / "validation_report.md").write_text(
        "# Validation Report\n\n"
        f"- Checks run: {len(checks)}\n"
        f"- Passed: {len(checks) - len(failed)}\n"
        f"- Failed: {len(failed)}\n\n"
        + "\n".join(f"- {row['status']}: {row['check_name']} ({row['details']})" for row in checks)
        + "\n",
        encoding="utf-8",
    )
    return {"validation_checks": validation_count, "failed_checks": len(failed)}

