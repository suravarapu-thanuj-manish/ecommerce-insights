import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)
n_records = 2500

categories = ["Electronics", "Home & Kitchen", "Apparel", "Beauty", "Sports"]
regions = ["North", "South", "East", "West", "Central"]
customer_ids = [f"CUST_{i:04d}" for i in range(1, 350)]

start_date = datetime(2025, 1, 1)
dates = [start_date + timedelta(days=int(d)) for d in np.random.randint(0, 365, n_records)]

data = {
    "order_id": [f"ORD_{i:05d}" for i in range(1, n_records + 1)],
    "customer_id": np.random.choice(customer_ids, n_records),
    "order_date": dates,
    "product_category": np.random.choice(categories, n_records, p=[0.25, 0.20, 0.25, 0.15, 0.15]),
    "region": np.random.choice(regions, n_records),
    "quantity": np.random.randint(1, 5, n_records),
    "unit_price": np.random.uniform(15.0, 250.0, n_records).round(2),
    "status": np.random.choice(["Completed", "Refunded", "Cancelled"], n_records, p=[0.88, 0.08, 0.04]),
}

df = pd.DataFrame(data)
df["gross_sales"] = (df["quantity"] * df["unit_price"]).round(2)
df["profit_margin_pct"] = np.random.uniform(0.15, 0.45, n_records).round(2)
df["profit"] = (df["gross_sales"] * df["profit_margin_pct"]).round(2)

df.to_csv("data/ecommerce_data.csv", index=False)
print("Dataset created: data/ecommerce_data.csv")