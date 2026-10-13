import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="E-Commerce Insights & Custom Dataset Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 E-Commerce Insights & Custom Dataset Analyzer")
st.markdown("Analyze sales performance or upload your own dataset to inspect its structure, KPIs, and summaries.")

# --- Sidebar: Data Source Selection ---
st.sidebar.header("📁 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload your own CSV dataset", type=["csv"])

@st.cache_data
def load_default_data():
    file_path = "data/ecommerce_data.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df["order_date"] = pd.to_datetime(df["order_date"])
        df.drop_duplicates(inplace=True)
        df = df[df["status"] != "Cancelled"]
        df["net_sales"] = df.apply(lambda r: 0 if r["status"] == "Refunded" else r["gross_sales"], axis=1)
        df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
        return df, True
    return None, False

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        is_default_schema = False
        st.sidebar.success("Custom CSV successfully loaded!")
    except Exception as e:
        st.error(f"Error loading uploaded file: {e}")
        st.stop()
else:
    df, is_default_schema = load_default_data()
    if df is None:
        st.warning("No default dataset found. Please upload a CSV file from the sidebar.")
        st.stop()
    st.sidebar.info("Using default e-commerce dataset. Upload a file above to analyze custom data.")

# --- Mode 1: Generic Dataset Analyzer (For any uploaded dataset) ---
st.subheader("📋 Dataset Overview & Metadata")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Rows", f"{df.shape[0]:,}")
col_m2.metric("Total Columns", f"{df.shape[1]:,}")
col_m3.metric("Missing Values", f"{df.isna().sum().sum():,}")
col_m4.metric("Duplicate Rows", f"{df.duplicated().sum():,}")

with st.expander("🔍 View Raw Data Sample & Column Data Types", expanded=False):
    st.dataframe(df.head(10), use_container_width=True)
    type_df = pd.DataFrame({"Column": df.columns, "Data Type": [str(t) for t in df.dtypes]})
    st.table(type_df)

# --- Mode 2: Standard E-Commerce Dashboard (If schema matches) ---
required_ecommerce_cols = {"order_id", "customer_id", "order_date", "product_category", "region", "net_sales", "profit", "status"}
if required_ecommerce_cols.issubset(set(df.columns)):
    st.divider()
    st.subheader("📈 E-Commerce Performance Dashboard")

    st.sidebar.header("Filter Analytics")
    selected_regions = st.sidebar.multiselect(
        "Select Region",
        options=df["region"].dropna().unique(),
        default=df["region"].dropna().unique()
    )
    selected_categories = st.sidebar.multiselect(
        "Select Category",
        options=df["product_category"].dropna().unique(),
        default=df["product_category"].dropna().unique()
    )

    filtered_df = df[
        (df["region"].isin(selected_regions)) &
        (df["product_category"].isin(selected_categories))
    ]

    completed_df = filtered_df[filtered_df["status"] == "Completed"]
    total_revenue = completed_df["net_sales"].sum()
    total_orders = completed_df["order_id"].nunique()
    aov = total_revenue / total_orders if total_orders > 0 else 0
    total_profit = completed_df["profit"].sum()
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    orders_per_cust = completed_df.groupby("customer_id")["order_id"].nunique()
    repeat_rate = ((orders_per_cust > 1).sum() / orders_per_cust.count() * 100) if orders_per_cust.count() > 0 else 0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Total Revenue", f"${total_revenue:,.2f}")
    kpi2.metric("Total Orders", f"{total_orders:,}")
    kpi3.metric("Avg Order Value", f"${aov:,.2f}")
    kpi4.metric("Profit Margin", f"{profit_margin:.1f}%")
    kpi5.metric("Repeat Customer Rate", f"{repeat_rate:.1f}%")

    tab1, tab2, tab3 = st.tabs(["Sales Trends & Geography", "Category Breakdown", "Customer Cohorts"])

    with tab1:
        c1, c2 = st.columns(2)
        if "order_month" in completed_df.columns:
            m_trend = completed_df.groupby("order_month")["net_sales"].sum().reset_index().sort_values("order_month")
            fig1 = px.line(m_trend, x="order_month", y="net_sales", markers=True, title="Monthly Net Sales")
            c1.plotly_chart(fig1, use_container_width=True)
        reg_df = completed_df.groupby("region")["net_sales"].sum().reset_index()
        fig2 = px.pie(reg_df, values="net_sales", names="region", title="Revenue by Region", hole=0.4)
        c2.plotly_chart(fig2, use_container_width=True)

    with tab2:
        c3, c4 = st.columns(2)
        cat_summary = completed_df.groupby("product_category").agg(Revenue=("net_sales", "sum"), Profit=("profit", "sum")).reset_index()
        fig3 = px.bar(cat_summary, x="product_category", y=["Revenue", "Profit"], barmode="group", title="Revenue vs Profit by Category")
        c3.plotly_chart(fig3, use_container_width=True)

        ref_summary = filtered_df.groupby("product_category")["status"].apply(lambda s: (s == "Refunded").mean() * 100).reset_index(name="refund_pct")
        fig4 = px.bar(ref_summary, x="product_category", y="refund_pct", title="Refund Rate by Category (%)", color="refund_pct", color_continuous_scale="Reds")
        c4.plotly_chart(fig4, use_container_width=True)

    with tab3:
        snapshot_date = pd.to_datetime(completed_df["order_date"]).max()
        rfm = completed_df.groupby("customer_id").agg({
            "order_date": lambda x: (snapshot_date - pd.to_datetime(x).max()).days,
            "order_id": "nunique",
            "net_sales": "sum"
        }).rename(columns={"order_date": "Recency", "order_id": "Frequency", "net_sales": "Monetary"})

        def segment_rfm(row):
            if row["Monetary"] > rfm["Monetary"].quantile(0.75) and row["Frequency"] > 1:
                return "VIP High-Value"
            elif row["Frequency"] > 1:
                return "Loyal Regular"
            elif row["Recency"] > 180:
                return "At-Risk / Inactive"
            return "Standard / New"

        rfm["Segment"] = rfm.apply(segment_rfm, axis=1)
        seg_counts = rfm["Segment"].value_counts().reset_index()
        seg_counts.columns = ["Segment", "Count"]
        fig5 = px.bar(seg_counts, x="Segment", y="Count", color="Segment", title="RFM Customer Segmentation", text_auto=True)
        st.plotly_chart(fig5, use_container_width=True)

else:
    # --- Mode 3: Custom Dataset Generic Visualizer ---
    st.divider()
    st.subheader("📊 Interactive Data Visualizer (Custom Dataset)")
    st.info("The uploaded file has unique columns. Select columns below to automatically generate plots.")

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if numeric_cols and categorical_cols:
        viz_col1, viz_col2 = st.columns(2)
        cat_select = viz_col1.selectbox("Select Categorical Column (Grouping)", categorical_cols)
        num_select = viz_col2.selectbox("Select Numeric Column (Metric)", numeric_cols)

        agg_df = df.groupby(cat_select)[num_select].sum().reset_index().sort_values(num_select, ascending=False).head(15)
        fig_custom = px.bar(agg_df, x=cat_select, y=num_select, title=f"Top 15: {num_select} by {cat_select}", color=num_select)
        st.plotly_chart(fig_custom, use_container_width=True)
    elif numeric_cols:
        selected_metric = st.selectbox("Select Numeric Metric to view distribution", numeric_cols)
        fig_hist = px.histogram(df, x=selected_metric, title=f"Distribution of {selected_metric}")
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.write("No numeric fields available to plot.")