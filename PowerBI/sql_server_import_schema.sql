-- SQL Server import schema for the skincare synthetic analytics project.

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
