# Validation Report

- Checks run: 21
- Passed: 21
- Failed: 0

- PASS: customers_exactly_5000 (5000)
- PASS: products_exactly_300 (300)
- PASS: orders_at_least_100000 (151517)
- PASS: customer_pk_unique (5000 unique)
- PASS: product_pk_unique (300 unique)
- PASS: order_pk_unique (151517 unique)
- PASS: customers_state_california (all customers use state California)
- PASS: orders_customer_fk (Orders.customer_id references Customers)
- PASS: items_order_product_fk (Order_Items references Orders and Products)
- PASS: reviews_fk (Reviews references Orders, Products, Customers)
- PASS: returns_fk (Returns references Orders and Products)
- PASS: order_status_mix (delivered_share=0.945)
- PASS: returns_after_delivery (all returns occur after delivered_date)
- PASS: review_rating_average_around_4_2 (avg_rating=4.252)
- PASS: top_20_percent_customers_generate_60_to_70_percent_revenue (top20_share=0.686)
- PASS: sunscreen_summer_lift (summer_avg=5703.3; other_avg=3046.4)
- PASS: moisturizer_winter_lift (winter_avg=7360.2; other_avg=4005.0)
- PASS: daily_feature_full_date_coverage (1096 rows from 2023-01-01 to 2025-12-31)
- PASS: monthly_feature_36_rows (36 rows)
- PASS: product_feature_300_rows (300 rows)
- PASS: return_rate_low (item_return_rate=0.0269)
