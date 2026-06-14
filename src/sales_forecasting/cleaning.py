from __future__ import annotations

from collections import defaultdict
from datetime import date

from .config import END_DATE, PROCESSED_DIR, RAW_DIR, START_DATE, ensure_directories
from .io_utils import as_float, as_int, money, read_csv, write_csv


def date_range(start: date = START_DATE, end: date = END_DATE):
    current = start
    while current <= end:
        yield current
        current = date.fromordinal(current.toordinal() + 1)


def month_start(value: str) -> str:
    return value[:7] + "-01"


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def read_required_raw() -> tuple[list[dict], dict[str, dict], dict[str, dict], list[dict], list[dict], list[dict]]:
    customers = {row["customer_id"]: row for row in read_csv(RAW_DIR / "Customers.csv")}
    products = {row["product_id"]: row for row in read_csv(RAW_DIR / "Products.csv")}
    orders = read_csv(RAW_DIR / "Orders.csv")
    order_items = read_csv(RAW_DIR / "Order_Items.csv")
    reviews = read_csv(RAW_DIR / "Reviews.csv")
    returns = read_csv(RAW_DIR / "Returns.csv")
    return orders, customers, products, order_items, reviews, returns


def clean_and_process() -> dict[str, int]:
    ensure_directories()
    orders, customers, products, order_items, reviews, returns = read_required_raw()
    orders_by_id = {row["order_id"]: row for row in orders}
    items_by_order: dict[str, list[dict]] = defaultdict(list)
    for item in order_items:
        items_by_order[item["order_id"]].append(item)

    reviews_by_order_product: dict[tuple[str, str], list[dict]] = defaultdict(list)
    reviews_by_customer: dict[str, list[dict]] = defaultdict(list)
    reviews_by_product: dict[str, list[dict]] = defaultdict(list)
    reviews_by_date: dict[str, list[dict]] = defaultdict(list)
    for review in reviews:
        key = (review["order_id"], review["product_id"])
        reviews_by_order_product[key].append(review)
        reviews_by_customer[review["customer_id"]].append(review)
        reviews_by_product[review["product_id"]].append(review)
        reviews_by_date[review["review_date"]].append(review)

    returns_by_order_product: dict[tuple[str, str], list[dict]] = defaultdict(list)
    returns_by_product: dict[str, list[dict]] = defaultdict(list)
    returns_by_date: dict[str, list[dict]] = defaultdict(list)
    returns_by_customer: dict[str, list[dict]] = defaultdict(list)
    for ret in returns:
        order = orders_by_id.get(ret["order_id"])
        key = (ret["order_id"], ret["product_id"])
        returns_by_order_product[key].append(ret)
        returns_by_product[ret["product_id"]].append(ret)
        returns_by_date[ret["return_date"]].append(ret)
        if order:
            returns_by_customer[order["customer_id"]].append(ret)

    daily: dict[str, dict] = {
        day.isoformat(): {
            "total_sales": 0.0,
            "total_orders": 0,
            "units_sold": 0,
            "gross_sales": 0.0,
            "total_discount": 0.0,
            "return_count": 0,
            "review_count": 0,
            "rating_total": 0.0,
        }
        for day in date_range(START_DATE, END_DATE)
    }
    monthly: dict[str, dict] = {}
    customer_features: dict[str, dict] = {
        customer_id: {
            "customer_id": customer_id,
            "total_orders": 0,
            "total_sales": 0.0,
            "units": 0,
            "first_order_date": "",
            "last_order_date": "",
            "return_count": 0,
            "review_count": 0,
            "rating_total": 0.0,
            "customer_segment": customer["customer_segment"],
        }
        for customer_id, customer in customers.items()
    }
    product_features: dict[str, dict] = {
        product_id: {
            "product_id": product_id,
            "product_name": product["product_name"],
            "brand": product["brand"],
            "category": product["category"],
            "units_sold": 0,
            "total_sales": 0.0,
            "order_ids": set(),
            "unit_price_total": 0.0,
            "unit_price_count": 0,
            "discount_pct_total": 0.0,
            "discount_pct_count": 0,
            "return_count": 0,
            "review_count": 0,
            "rating_total": 0.0,
            "cost_total": 0.0,
        }
        for product_id, product in products.items()
    }
    sales_transactions: list[dict] = []

    for order in orders:
        if order["order_status"] != "Delivered":
            continue
        day_key = order["order_date"]
        if day_key not in daily:
            continue
        bucket = daily[day_key]
        bucket["total_sales"] += as_float(order["final_amount"])
        bucket["total_orders"] += 1
        bucket["gross_sales"] += as_float(order["gross_amount"])
        bucket["total_discount"] += as_float(order["discount_amount"])

        cf = customer_features[order["customer_id"]]
        cf["total_orders"] += 1
        cf["total_sales"] += as_float(order["final_amount"])
        cf["first_order_date"] = min(cf["first_order_date"], day_key) if cf["first_order_date"] else day_key
        cf["last_order_date"] = max(cf["last_order_date"], day_key)

        for item in items_by_order[order["order_id"]]:
            product = products[item["product_id"]]
            quantity = as_int(item["quantity"])
            item_total = as_float(item["item_total"])
            unit_price = as_float(item["unit_price"])
            discount_pct = as_float(item["discount_pct"])
            cost = as_float(product["cost_price"]) * quantity
            return_count = len(returns_by_order_product.get((item["order_id"], item["product_id"]), []))
            item_reviews = reviews_by_order_product.get((item["order_id"], item["product_id"]), [])
            rating_total = sum(as_int(review["rating"]) for review in item_reviews)

            bucket["units_sold"] += quantity
            cf["units"] += quantity

            pf = product_features[item["product_id"]]
            pf["units_sold"] += quantity
            pf["total_sales"] += item_total
            pf["order_ids"].add(order["order_id"])
            pf["unit_price_total"] += unit_price
            pf["unit_price_count"] += 1
            pf["discount_pct_total"] += discount_pct
            pf["discount_pct_count"] += 1
            pf["cost_total"] += cost

            sales_transactions.append(
                {
                    "order_item_id": item["order_item_id"],
                    "order_id": item["order_id"],
                    "order_date": order["order_date"],
                    "customer_id": order["customer_id"],
                    "customer_segment": customers[order["customer_id"]]["customer_segment"],
                    "sales_channel": order["sales_channel"],
                    "product_id": item["product_id"],
                    "product_name": product["product_name"],
                    "brand": product["brand"],
                    "category": product["category"],
                    "quantity": quantity,
                    "unit_price": money(unit_price),
                    "discount_pct": f"{discount_pct:.2f}",
                    "item_total": money(item_total),
                    "cost_price": product["cost_price"],
                    "gross_margin": money(item_total - cost),
                    "return_count": return_count,
                    "review_count": len(item_reviews),
                    "avg_rating": f"{rating_total / len(item_reviews):.2f}" if item_reviews else "",
                }
            )

    for date_key, day_reviews in reviews_by_date.items():
        if date_key in daily:
            daily[date_key]["review_count"] += len(day_reviews)
            daily[date_key]["rating_total"] += sum(as_int(review["rating"]) for review in day_reviews)
    for date_key, day_returns in returns_by_date.items():
        if date_key in daily:
            daily[date_key]["return_count"] += len(day_returns)
    for customer_id, customer_reviews in reviews_by_customer.items():
        cf = customer_features.get(customer_id)
        if cf:
            cf["review_count"] = len(customer_reviews)
            cf["rating_total"] = sum(as_int(review["rating"]) for review in customer_reviews)
    for customer_id, customer_returns in returns_by_customer.items():
        cf = customer_features.get(customer_id)
        if cf:
            cf["return_count"] = len(customer_returns)
    for product_id, product_reviews in reviews_by_product.items():
        pf = product_features.get(product_id)
        if pf:
            pf["review_count"] = len(product_reviews)
            pf["rating_total"] = sum(as_int(review["rating"]) for review in product_reviews)
    for product_id, product_returns in returns_by_product.items():
        pf = product_features.get(product_id)
        if pf:
            pf["return_count"] = len(product_returns)

    daily_rows: list[dict] = []
    day_keys = [day.isoformat() for day in date_range(START_DATE, END_DATE)]
    sales_values = [daily[key]["total_sales"] for key in day_keys]
    order_values = [daily[key]["total_orders"] for key in day_keys]
    for idx, key in enumerate(day_keys):
        bucket = daily[key]
        avg_rating = safe_div(bucket["rating_total"], bucket["review_count"])
        row = {
            "date": key,
            "total_sales": money(bucket["total_sales"]),
            "total_orders": bucket["total_orders"],
            "units_sold": bucket["units_sold"],
            "gross_sales": money(bucket["gross_sales"]),
            "total_discount": money(bucket["total_discount"]),
            "avg_order_value": money(safe_div(bucket["total_sales"], bucket["total_orders"])),
            "return_count": bucket["return_count"],
            "return_rate": f"{safe_div(bucket['return_count'], bucket['total_orders']):.4f}",
            "avg_rating": f"{avg_rating:.2f}" if bucket["review_count"] else "",
            "sales_lag_7d": money(sales_values[idx - 7]) if idx >= 7 else "0.00",
            "sales_lag_14d": money(sales_values[idx - 14]) if idx >= 14 else "0.00",
            "sales_lag_30d": money(sales_values[idx - 30]) if idx >= 30 else "0.00",
            "rolling_7d_sales": money(sum(sales_values[max(0, idx - 6) : idx + 1])),
            "rolling_30d_sales": money(sum(sales_values[max(0, idx - 29) : idx + 1])),
            "rolling_7d_orders": sum(order_values[max(0, idx - 6) : idx + 1]),
        }
        daily_rows.append(row)

    for row in daily_rows:
        key = month_start(row["date"])
        monthly.setdefault(
            key,
            {
                "total_sales": 0.0,
                "total_orders": 0,
                "gross_sales": 0.0,
                "total_discount": 0.0,
                "units_sold": 0,
                "return_count": 0,
                "review_count": 0,
                "rating_total": 0.0,
            },
        )
        bucket = monthly[key]
        bucket["total_sales"] += as_float(row["total_sales"])
        bucket["total_orders"] += as_int(row["total_orders"])
        bucket["gross_sales"] += as_float(row["gross_sales"])
        bucket["total_discount"] += as_float(row["total_discount"])
        bucket["units_sold"] += as_int(row["units_sold"])
        bucket["return_count"] += as_int(row["return_count"])

    for review in reviews:
        key = month_start(review["review_date"])
        if key in monthly:
            monthly[key]["review_count"] += 1
            monthly[key]["rating_total"] += as_int(review["rating"])

    month_keys = sorted(monthly)
    monthly_sales = [monthly[key]["total_sales"] for key in month_keys]
    calendar_month_avg: dict[str, float] = {}
    grand_avg = safe_div(sum(monthly_sales), len(monthly_sales))
    for month_num in range(1, 13):
        values = [monthly[key]["total_sales"] for key in month_keys if int(key[5:7]) == month_num]
        calendar_month_avg[f"{month_num:02d}"] = safe_div(sum(values), len(values))

    monthly_rows: list[dict] = []
    for idx, key in enumerate(month_keys):
        bucket = monthly[key]
        total_sales = bucket["total_sales"]
        total_orders = bucket["total_orders"]
        prior = monthly_sales[idx - 1] if idx >= 1 else 0.0
        monthly_rows.append(
            {
                "month_start": key,
                "total_sales": money(total_sales),
                "total_orders": total_orders,
                "gross_sales": money(bucket["gross_sales"]),
                "total_discount": money(bucket["total_discount"]),
                "units_sold": bucket["units_sold"],
                "return_count": bucket["return_count"],
                "review_count": bucket["review_count"],
                "avg_rating": f"{safe_div(bucket['rating_total'], bucket['review_count']):.2f}" if bucket["review_count"] else "",
                "avg_order_value": money(safe_div(total_sales, total_orders)),
                "return_rate": f"{safe_div(bucket['return_count'], total_orders):.4f}",
                "sales_lag_1m": money(monthly_sales[idx - 1]) if idx >= 1 else "0.00",
                "sales_lag_3m": money(monthly_sales[idx - 3]) if idx >= 3 else "0.00",
                "sales_lag_12m": money(monthly_sales[idx - 12]) if idx >= 12 else "0.00",
                "rolling_3m_sales": money(sum(monthly_sales[max(0, idx - 2) : idx + 1])),
                "rolling_6m_sales": money(sum(monthly_sales[max(0, idx - 5) : idx + 1])),
                "sales_growth_mom_pct": f"{safe_div(total_sales - prior, prior):.4f}" if idx >= 1 and prior else "0.0000",
                "seasonality_index": f"{safe_div(calendar_month_avg[key[5:7]], grand_avg):.4f}",
            }
        )

    customer_rows: list[dict] = []
    for customer_id, cf in sorted(customer_features.items()):
        total_orders = cf["total_orders"]
        avg_rating = safe_div(cf["rating_total"], cf["review_count"])
        recency = (END_DATE - date.fromisoformat(cf["last_order_date"])).days if cf["last_order_date"] else ""
        customer_rows.append(
            {
                "customer_id": customer_id,
                "total_orders": total_orders,
                "total_sales": money(cf["total_sales"]),
                "avg_order_value": money(safe_div(cf["total_sales"], total_orders)),
                "first_order_date": cf["first_order_date"],
                "last_order_date": cf["last_order_date"],
                "recency_days": recency,
                "return_count": cf["return_count"],
                "review_count": cf["review_count"],
                "avg_rating": f"{avg_rating:.2f}" if cf["review_count"] else "",
                "customer_lifetime_value": money(cf["total_sales"]),
                "customer_segment": cf["customer_segment"],
            }
        )

    max_units = max((pf["units_sold"] for pf in product_features.values()), default=1)
    max_sales = max((pf["total_sales"] for pf in product_features.values()), default=1)
    max_reviews = max((pf["review_count"] for pf in product_features.values()), default=1)
    product_rows: list[dict] = []
    for product_id, pf in sorted(product_features.items()):
        order_count = len(pf["order_ids"])
        total_sales = pf["total_sales"]
        gross_margin = total_sales - pf["cost_total"]
        popularity_score = (
            safe_div(pf["units_sold"], max_units) * 0.45
            + safe_div(total_sales, max_sales) * 0.35
            + safe_div(pf["review_count"], max_reviews) * 0.20
        ) * 100
        product_rows.append(
            {
                "product_id": product_id,
                "product_name": pf["product_name"],
                "brand": pf["brand"],
                "category": pf["category"],
                "units_sold": pf["units_sold"],
                "total_sales": money(total_sales),
                "order_count": order_count,
                "avg_unit_price": money(safe_div(pf["unit_price_total"], pf["unit_price_count"])),
                "avg_discount_pct": f"{safe_div(pf['discount_pct_total'], pf['discount_pct_count']):.4f}",
                "return_count": pf["return_count"],
                "review_count": pf["review_count"],
                "avg_rating": f"{safe_div(pf['rating_total'], pf['review_count']):.2f}" if pf["review_count"] else "",
                "return_rate_by_order": f"{safe_div(pf['return_count'], order_count):.4f}",
                "gross_margin_per_unit": money(safe_div(gross_margin, pf["units_sold"])),
                "gross_margin_pct": f"{safe_div(gross_margin, total_sales):.4f}",
                "popularity_score": f"{popularity_score:.2f}",
            }
        )

    daily_fields = [
        "date",
        "total_sales",
        "total_orders",
        "units_sold",
        "gross_sales",
        "total_discount",
        "avg_order_value",
        "return_count",
        "return_rate",
        "avg_rating",
        "sales_lag_7d",
        "sales_lag_14d",
        "sales_lag_30d",
        "rolling_7d_sales",
        "rolling_30d_sales",
        "rolling_7d_orders",
    ]
    monthly_fields = [
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
    ]
    customer_fields = [
        "customer_id",
        "total_orders",
        "total_sales",
        "avg_order_value",
        "first_order_date",
        "last_order_date",
        "recency_days",
        "return_count",
        "review_count",
        "avg_rating",
        "customer_lifetime_value",
        "customer_segment",
    ]
    product_fields = [
        "product_id",
        "product_name",
        "brand",
        "category",
        "units_sold",
        "total_sales",
        "order_count",
        "avg_unit_price",
        "avg_discount_pct",
        "return_count",
        "review_count",
        "avg_rating",
        "return_rate_by_order",
        "gross_margin_per_unit",
        "gross_margin_pct",
        "popularity_score",
    ]
    transaction_fields = [
        "order_item_id",
        "order_id",
        "order_date",
        "customer_id",
        "customer_segment",
        "sales_channel",
        "product_id",
        "product_name",
        "brand",
        "category",
        "quantity",
        "unit_price",
        "discount_pct",
        "item_total",
        "cost_price",
        "gross_margin",
        "return_count",
        "review_count",
        "avg_rating",
    ]

    counts = {
        "Daily_Sales_Features": write_csv(PROCESSED_DIR / "Daily_Sales_Features.csv", daily_rows, daily_fields),
        "Monthly_Sales_Features": write_csv(PROCESSED_DIR / "Monthly_Sales_Features.csv", monthly_rows, monthly_fields),
        "Customer_Features": write_csv(PROCESSED_DIR / "Customer_Features.csv", customer_rows, customer_fields),
        "Product_Features": write_csv(PROCESSED_DIR / "Product_Features.csv", product_rows, product_fields),
        "Sales_Transactions": write_csv(PROCESSED_DIR / "Sales_Transactions.csv", sales_transactions, transaction_fields),
    }
    # Compatibility copies for earlier scripts or exploratory notebooks.
    write_csv(PROCESSED_DIR / "daily_sales.csv", daily_rows, daily_fields)
    write_csv(PROCESSED_DIR / "monthly_sales_features.csv", monthly_rows, monthly_fields)
    write_csv(PROCESSED_DIR / "customer_features.csv", customer_rows, customer_fields)
    write_csv(PROCESSED_DIR / "product_features.csv", product_rows, product_fields)
    write_csv(PROCESSED_DIR / "sales_transactions.csv", sales_transactions, transaction_fields)
    return counts
