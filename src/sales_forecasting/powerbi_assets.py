from __future__ import annotations

from .config import POWERBI_DIR, ensure_directories
from .io_utils import write_csv


DATA_DICTIONARY_ROWS = [
    ("Customers", "customer_id", "varchar(10)", "Customer primary key"),
    ("Customers", "customer_name", "varchar(100)", "Synthetic customer full name"),
    ("Customers", "city", "varchar(60)", "California city"),
    ("Customers", "state", "varchar(20)", "Always California"),
    ("Customers", "gender", "varchar(30)", "Synthetic gender"),
    ("Customers", "age", "int", "Customer age"),
    ("Customers", "age_group", "varchar(10)", "Age bucket"),
    ("Customers", "signup_date", "date", "Customer signup date"),
    ("Customers", "acquisition_channel", "varchar(40)", "Marketing acquisition channel"),
    ("Customers", "customer_segment", "varchar(20)", "New, Regular, Loyal, or VIP"),
    ("Products", "product_id", "varchar(10)", "Product primary key"),
    ("Products", "product_name", "varchar(120)", "Synthetic product name"),
    ("Products", "brand", "varchar(60)", "Synthetic skincare brand"),
    ("Products", "category", "varchar(40)", "Skincare category"),
    ("Products", "concern", "varchar(60)", "Primary skincare concern"),
    ("Products", "skin_type", "varchar(30)", "Recommended skin type"),
    ("Products", "key_ingredient", "varchar(60)", "Hero ingredient"),
    ("Products", "size", "varchar(20)", "Product size"),
    ("Products", "mrp", "decimal(12,2)", "List price"),
    ("Products", "cost_price", "decimal(12,2)", "Unit cost"),
    ("Products", "stock_qty", "int", "Synthetic stock quantity"),
    ("Products", "launch_date", "date", "Launch date"),
    ("Orders", "order_id", "varchar(12)", "Order primary key"),
    ("Orders", "customer_id", "varchar(10)", "Customer foreign key"),
    ("Orders", "order_date", "date", "Order date"),
    ("Orders", "order_status", "varchar(20)", "Delivered, Cancelled, or Processing"),
    ("Orders", "payment_method", "varchar(30)", "Payment method"),
    ("Orders", "sales_channel", "varchar(30)", "Sales channel"),
    ("Orders", "gross_amount", "decimal(12,2)", "Order gross amount"),
    ("Orders", "discount_amount", "decimal(12,2)", "Order discount amount"),
    ("Orders", "shipping_fee", "decimal(12,2)", "Shipping fee"),
    ("Orders", "final_amount", "decimal(12,2)", "Final paid amount"),
    ("Orders", "delivered_date", "date", "Delivery date for delivered orders"),
    ("Order_Items", "order_item_id", "varchar(14)", "Order item primary key"),
    ("Order_Items", "order_id", "varchar(12)", "Order foreign key"),
    ("Order_Items", "product_id", "varchar(10)", "Product foreign key"),
    ("Order_Items", "quantity", "int", "Units purchased"),
    ("Order_Items", "unit_price", "decimal(12,2)", "Unit selling price"),
    ("Order_Items", "discount_pct", "decimal(6,4)", "Line discount percent"),
    ("Order_Items", "item_total", "decimal(12,2)", "Line total after discount"),
    ("Reviews", "review_id", "varchar(12)", "Review primary key"),
    ("Reviews", "rating", "int", "Rating from 1 to 5"),
    ("Returns", "return_id", "varchar(12)", "Return primary key"),
    ("Returns", "return_reason", "varchar(40)", "Return reason"),
    ("Daily_Sales_Features", "date", "date", "Daily feature date"),
    ("Monthly_Sales_Features", "month_start", "date", "Month-start feature date"),
    ("Customer_Features", "customer_lifetime_value", "decimal(12,2)", "Customer total sales"),
    ("Product_Features", "popularity_score", "decimal(8,2)", "Normalized long-tail popularity score"),
]


SQL_SCHEMA = """-- SQL Server import schema for the skincare synthetic analytics project.

CREATE TABLE dbo.Customers (
    customer_id varchar(10) NOT NULL PRIMARY KEY,
    customer_name varchar(100) NOT NULL,
    city varchar(60) NOT NULL,
    state varchar(20) NOT NULL,
    gender varchar(30) NOT NULL,
    age int NOT NULL,
    age_group varchar(10) NOT NULL,
    signup_date date NOT NULL,
    acquisition_channel varchar(40) NOT NULL,
    customer_segment varchar(20) NOT NULL
);

CREATE TABLE dbo.Products (
    product_id varchar(10) NOT NULL PRIMARY KEY,
    product_name varchar(120) NOT NULL,
    brand varchar(60) NOT NULL,
    category varchar(40) NOT NULL,
    concern varchar(60) NOT NULL,
    skin_type varchar(30) NOT NULL,
    key_ingredient varchar(60) NOT NULL,
    size varchar(20) NOT NULL,
    mrp decimal(12,2) NOT NULL,
    cost_price decimal(12,2) NOT NULL,
    stock_qty int NOT NULL,
    launch_date date NOT NULL
);

CREATE TABLE dbo.Orders (
    order_id varchar(12) NOT NULL PRIMARY KEY,
    customer_id varchar(10) NOT NULL,
    order_date date NOT NULL,
    order_status varchar(20) NOT NULL,
    payment_method varchar(30) NOT NULL,
    sales_channel varchar(30) NOT NULL,
    gross_amount decimal(12,2) NOT NULL,
    discount_amount decimal(12,2) NOT NULL,
    shipping_fee decimal(12,2) NOT NULL,
    final_amount decimal(12,2) NOT NULL,
    delivered_date date NULL,
    CONSTRAINT FK_Orders_Customers FOREIGN KEY (customer_id) REFERENCES dbo.Customers(customer_id)
);

CREATE TABLE dbo.Order_Items (
    order_item_id varchar(14) NOT NULL PRIMARY KEY,
    order_id varchar(12) NOT NULL,
    product_id varchar(10) NOT NULL,
    quantity int NOT NULL,
    unit_price decimal(12,2) NOT NULL,
    discount_pct decimal(6,4) NOT NULL,
    item_total decimal(12,2) NOT NULL,
    CONSTRAINT FK_OrderItems_Orders FOREIGN KEY (order_id) REFERENCES dbo.Orders(order_id),
    CONSTRAINT FK_OrderItems_Products FOREIGN KEY (product_id) REFERENCES dbo.Products(product_id)
);

CREATE TABLE dbo.Reviews (
    review_id varchar(12) NOT NULL PRIMARY KEY,
    order_id varchar(12) NOT NULL,
    product_id varchar(10) NOT NULL,
    customer_id varchar(10) NOT NULL,
    rating int NOT NULL,
    review_date date NOT NULL
);

CREATE TABLE dbo.Returns (
    return_id varchar(12) NOT NULL PRIMARY KEY,
    order_id varchar(12) NOT NULL,
    product_id varchar(10) NOT NULL,
    return_date date NOT NULL,
    return_reason varchar(40) NOT NULL
);
"""


POWERBI_NOTES = """# Power BI Model Notes

Recommended relationships:

- Customers[customer_id] 1:* Orders[customer_id]
- Orders[order_id] 1:* Order_Items[order_id]
- Products[product_id] 1:* Order_Items[product_id]
- Products[product_id] 1:* Reviews[product_id]
- Products[product_id] 1:* Returns[product_id]
- Date[date] 1:* Daily_Sales_Features[date]
- Date[date] 1:* Orders[order_date]

Recommended measures:

```DAX
Total Sales = SUM(Daily_Sales_Features[total_sales])
Gross Sales = SUM(Daily_Sales_Features[gross_sales])
Total Discount = SUM(Daily_Sales_Features[total_discount])
Average Order Value = DIVIDE([Total Sales], SUM(Daily_Sales_Features[total_orders]))
Return Rate = DIVIDE(SUM(Daily_Sales_Features[return_count]), SUM(Daily_Sales_Features[total_orders]))
MoM Sales Growth = AVERAGE(Monthly_Sales_Features[sales_growth_mom_pct])
```

Suggested pages:

- Executive sales overview
- Seasonality and promotion spikes
- Customer segment revenue concentration
- Product long-tail and category trends
- Reviews, ratings, and returns
- Monthly forecasting comparison
"""


def write_powerbi_assets() -> dict[str, int]:
    ensure_directories()
    rows = [
        {"table_name": table, "column_name": column, "sql_type": sql_type, "description": description}
        for table, column, sql_type, description in DATA_DICTIONARY_ROWS
    ]
    count = write_csv(POWERBI_DIR / "data_dictionary.csv", rows, ["table_name", "column_name", "sql_type", "description"])
    (POWERBI_DIR / "sql_server_import_schema.sql").write_text(SQL_SCHEMA, encoding="utf-8")
    (POWERBI_DIR / "powerbi_model_notes.md").write_text(POWERBI_NOTES, encoding="utf-8")
    return {"data_dictionary": count, "powerbi_documents": 2}

