import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="E-Commerce Sales & Customer Insights",
    page_icon="📊",
    layout="wide"
)

# --- Data Loading and Cleaning ---
@st.cache_data
def load_and_clean_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df.drop_duplicates(inplace=True)
    # Filter out cancelled orders; retain refunds for accounting view
    df = df[df["status"] != "Cancelled"]
    df["net_sales"] = df.apply(
        lambda row: 0 if row["status"] == "Refunded" else row["gross_sales"], axis=1
    )
    df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
    return df

df = load_and_clean_data("data/ecommerce_data.csv")

# --- Sidebar Filters ---
st.sidebar.header("Global Filters")
selected_regions = st.sidebar.multiselect(
    "Select Region",
    options=df["region"].unique(),
    default=df["region"].unique()
)
selected_categories = st.sidebar.multiselect(
    "Select Category",
    options=df["product_category"].unique(),
    default=df["product_category"].unique()
)

filtered_df = df[
    (df["region"].isin(selected_regions)) &
    (df["product_category"].isin(selected_categories))
]

# --- Main Dashboard Header ---
st.title("📊 E-commerce Sales & Customer Insights Dashboard")
st.markdown("Monitor revenue drivers, regional metrics, category health, and customer retention.")

# --- Step 3 KPIs ---
completed_df = filtered_df[filtered_df["status"] == "Completed"]
total_revenue = completed_df["net_sales"].sum()
total_orders = completed_df["order_id"].nunique()
aov = total_revenue / total_orders if total_orders > 0 else 0
total_profit = completed_df["profit"].sum()
profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

# Repeat customer rate
orders_per_cust = completed_df.groupby("customer_id")["order_id"].nunique()
repeat_customers = (orders_per_cust > 1).sum()
total_customers = orders_per_cust.count()
repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Revenue", f"${total_revenue:,.2f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Avg Order Value (AOV)", f"${aov:,.2f}")
col4.metric("Profit Margin", f"{profit_margin:.1f}%")
col5.metric("Repeat Customer Rate", f"{repeat_rate:.1f}%")

st.divider()

# --- Visualizations ---
tab1, tab2, tab3 = st.tabs(["Sales Trends & Geography", "Category & Product Performance", "Customer Segmentation"])

with tab1:
    col_left, col_right = st.columns(2)
    
    # Monthly Revenue Trend
    monthly_trend = (
        completed_df.groupby("order_month")["net_sales"]
        .sum()
        .reset_index()
        .sort_values("order_month")
    )
    fig_trend = px.line(
        monthly_trend,
        x="order_month",
        y="net_sales",
        markers=True,
        title="Monthly Net Revenue Trend",
        labels={"order_month": "Month", "net_sales": "Revenue ($)"}
    )
    col_left.plotly_chart(fig_trend, use_container_width=True)

    # Regional Distribution
    reg_sales = completed_df.groupby("region")["net_sales"].sum().reset_index()
    fig_reg = px.pie(
        reg_sales,
        values="net_sales",
        names="region",
        title="Revenue by Region",
        hole=0.4
    )
    col_right.plotly_chart(fig_reg, use_container_width=True)

with tab2:
    col_left2, col_right2 = st.columns(2)
    
    # Revenue & Margin by Category
    cat_summary = (
        completed_df.groupby("product_category")
        .agg(Revenue=("net_sales", "sum"), Profit=("profit", "sum"))
        .reset_index()
    )
    fig_cat = px.bar(
        cat_summary,
        x="product_category",
        y=["Revenue", "Profit"],
        barmode="group",
        title="Revenue vs. Profit by Category",
        labels={"value": "Amount ($)", "product_category": "Category"}
    )
    col_left2.plotly_chart(fig_cat, use_container_width=True)

    # Refund Rate by Category
    refund_counts = (
        filtered_df.groupby("product_category")["status"]
        .apply(lambda s: (s == "Refunded").mean() * 100)
        .reset_index(name="refund_rate_pct")
    )
    fig_ref = px.bar(
        refund_counts,
        x="product_category",
        y="refund_rate_pct",
        color="refund_rate_pct",
        color_continuous_scale="Reds",
        title="Refund Rate by Category (%)",
        labels={"refund_rate_pct": "Refund Rate (%)", "product_category": "Category"}
    )
    col_right2.plotly_chart(fig_ref, use_container_width=True)

with tab3:
    # RFM Scoring & Behavior
    snapshot_date = df["order_date"].max()
    rfm = completed_df.groupby("customer_id").agg({
        "order_date": lambda x: (snapshot_date - x.max()).days,
        "order_id": "nunique",
        "net_sales": "sum"
    }).rename(columns={"order_date": "Recency", "order_id": "Frequency", "net_sales": "Monetary"})

    def assign_segment(row):
        if row["Monetary"] > rfm["Monetary"].quantile(0.75) and row["Frequency"] > 1:
            return "VIP High-Value"
        elif row["Frequency"] > 1:
            return "Loyal Regular"
        elif row["Recency"] > 180:
            return "At-Risk / Inactive"
        return "Standard / New"

    rfm["Segment"] = rfm.apply(assign_segment, axis=1)
    seg_counts = rfm["Segment"].value_counts().reset_index()
    seg_counts.columns = ["Segment", "Count"]

    fig_rfm = px.bar(
        seg_counts,
        x="Segment",
        y="Count",
        color="Segment",
        title="Customer Segmentation Breakdown",
        text_auto=True
    )
    st.plotly_chart(fig_rfm, use_container_width=True)

st.divider()

# --- Strategic Recommendations ---
st.subheader("📌 Key Findings & Data-Backed Recommendations")
st.markdown("""
* **Prioritize High-Margin Categories:** Reallocate digital ad spend toward categories generating the highest net margin per dollar spent.
* **Target At-Risk Customers:** Launch automated win-back discount sequences for customers in the *At-Risk / Inactive* cohort before recency crosses 200 days.
* **Investigate High-Refund Drivers:** Inspect product return reasons for categories showing elevated refund rates to reduce inventory and logistics losses.
* **Capitalize on Regional Leaders:** Double down on inventory fulfillment centers in the top-performing sales regions to lower transit times and increase conversion.
""")