# Power BI Model Notes

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
