"""
Olist E-Commerce Dashboard — Streamlit App.

Interactive dashboard for the Olist Brazilian E-Commerce dataset.
Designed to be deployed on Streamlit Community Cloud.

Run locally:
    streamlit run streamlit_app/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

# ============================================================
# Page configuration
# ============================================================
st.set_page_config(
    page_title="Olist E-Commerce Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Styling
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e2d3e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    /* Metric cards: subtle gray background, dark text, left accent */
    div[data-testid="stMetric"] {
        background-color: #f5f7fa;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #1e2d3e;
    }
    div[data-testid="stMetricLabel"] {
        color: #4a5568 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #1e2d3e !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Data loading (cached)
# ============================================================
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data(show_spinner="Loading Olist dataset...")
def load_data():
    """Load and prepare the analytical dataset."""
    df_customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
    df_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    df_orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    df_products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
    df_sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    df_reviews = pd.read_csv(DATA_DIR / "olist_order_reviews_dataset.csv")
    df_category = pd.read_csv(DATA_DIR / "product_category_name_translation.csv")

    # Dates
    for col in [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")

    # Translate categories to English
    df_products = df_products.merge(df_category, on="product_category_name", how="left")

    # Master dataset (one row per order item)
    df = (
        df_items.merge(df_orders, on="order_id", how="left")
        .merge(df_customers, on="customer_id", how="left")
        .merge(
            df_products[["product_id", "product_category_name_english"]],
            on="product_id",
            how="left",
        )
        .merge(df_sellers, on="seller_id", how="left")
    )

    # Derived columns
    df["order_date"] = df["order_purchase_timestamp"].dt.date
    df["order_year_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["delivery_time_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["is_late"] = (
        df["order_delivered_customer_date"] > df["order_estimated_delivery_date"]
    )

    # Reviews at order level (avg score per order if multiple reviews)
    reviews_grouped = (
        df_reviews.groupby("order_id")["review_score"].mean().reset_index()
    )
    df = df.merge(reviews_grouped, on="order_id", how="left")

    return df


# ============================================================
# Sidebar — Filters
# ============================================================
def render_sidebar(df: pd.DataFrame) -> dict:
    st.sidebar.header("Filters")

    # Date range
    min_date = df["order_purchase_timestamp"].min().date()
    max_date = df["order_purchase_timestamp"].max().date()
    date_range = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # State (with All option)
    states = ["All"] + sorted(df["customer_state"].dropna().unique().tolist())
    state = st.sidebar.selectbox("Customer state", states)

    # Category
    cats = ["All"] + sorted(
        df["product_category_name_english"].dropna().unique().tolist()
    )
    category = st.sidebar.selectbox("Product category", cats)

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Built by [Agustín Lannoo](https://github.com/Alannoo6)**  \n"
        "Dataset: [Olist · Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)"
    )

    return {"date_range": date_range, "state": state, "category": category}


# ============================================================
# Filter application
# ============================================================
def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    if len(filters["date_range"]) == 2:
        start, end = filters["date_range"]
        out = out[
            (out["order_purchase_timestamp"].dt.date >= start)
            & (out["order_purchase_timestamp"].dt.date <= end)
        ]
    if filters["state"] != "All":
        out = out[out["customer_state"] == filters["state"]]
    if filters["category"] != "All":
        out = out[out["product_category_name_english"] == filters["category"]]
    return out


# ============================================================
# Sections
# ============================================================
def section_kpis(df: pd.DataFrame) -> None:
    orders = df.drop_duplicates(subset="order_id")
    total_revenue = df["price"].sum()
    total_orders = orders.shape[0]
    total_customers = df["customer_unique_id"].nunique()
    aov = total_revenue / total_orders if total_orders else 0
    avg_review = df["review_score"].mean()
    late_pct = 100 * df["is_late"].sum() / len(df) if len(df) else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Revenue", f"R$ {total_revenue/1e6:.2f}M")
    c2.metric("Orders", f"{total_orders:,}")
    c3.metric("Customers", f"{total_customers:,}")
    c4.metric("AOV", f"R$ {aov:.0f}")
    c5.metric("Avg review", f"{avg_review:.2f} ⭐")
    c6.metric("Late deliveries", f"{late_pct:.1f}%")


def section_temporal(df: pd.DataFrame) -> None:
    st.subheader("📈 Revenue & Orders Over Time")

    monthly = (
        df.drop_duplicates(subset="order_id")
        .groupby("order_year_month")
        .agg(orders=("order_id", "count"), revenue=("price", "sum"))
        .reset_index()
    )

    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(
            monthly,
            x="order_year_month",
            y="revenue",
            markers=True,
            title="Monthly Revenue",
            labels={"order_year_month": "Month", "revenue": "Revenue (R$)"},
        )
        fig.update_traces(line_color="#1e2d3e")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(
            monthly,
            x="order_year_month",
            y="orders",
            markers=True,
            title="Monthly Orders",
            labels={"order_year_month": "Month", "orders": "Orders"},
        )
        fig.update_traces(line_color="#e07b00")
        st.plotly_chart(fig, use_container_width=True)


def section_categories(df: pd.DataFrame) -> None:
    st.subheader("🛍️ Product Categories")

    cat_rev = (
        df.groupby("product_category_name_english")
        .agg(revenue=("price", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
        .head(15)
        .reset_index()
    )
    fig = px.bar(
        cat_rev,
        x="revenue",
        y="product_category_name_english",
        orientation="h",
        title="Top 15 Categories by Revenue",
        labels={"product_category_name_english": "Category", "revenue": "Revenue (R$)"},
        color_discrete_sequence=["#1e2d3e"],
    )
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)


def section_geography(df: pd.DataFrame) -> None:
    st.subheader("🗺️ Geographic Distribution")

    state_data = (
        df.groupby("customer_state")
        .agg(revenue=("price", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
        .reset_index()
    )

    fig = px.bar(
        state_data,
        x="customer_state",
        y="revenue",
        title="Revenue by State",
        labels={"customer_state": "State", "revenue": "Revenue (R$)"},
        color="revenue",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig, use_container_width=True)


def section_reviews(df: pd.DataFrame) -> None:
    st.subheader("⭐ Customer Satisfaction")

    c1, c2 = st.columns(2)
    with c1:
        reviews = df.dropna(subset=["review_score"]).drop_duplicates(subset="order_id")
        review_counts = reviews["review_score"].round().value_counts().sort_index()
        fig = px.bar(
            x=review_counts.index.astype(int),
            y=review_counts.values,
            labels={"x": "Review score", "y": "Reviews"},
            title="Review Score Distribution",
            color=review_counts.values,
            color_continuous_scale=["#c0392b", "#e67e22", "#f1c40f", "#27ae60", "#16a085"],
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        delivered = df.dropna(subset=["delivery_time_days", "review_score"]).drop_duplicates(
            subset="order_id"
        )
        delivered = delivered[delivered["delivery_time_days"].between(0, 60)]
        avg_by_score = (
            delivered.groupby(delivered["review_score"].round().astype(int))[
                "delivery_time_days"
            ]
            .mean()
            .reset_index()
        )
        fig = px.bar(
            avg_by_score,
            x="review_score",
            y="delivery_time_days",
            title="Avg Delivery Time by Review Score",
            labels={"review_score": "Review score", "delivery_time_days": "Avg delivery (days)"},
            color_discrete_sequence=["#e07b00"],
        )
        st.plotly_chart(fig, use_container_width=True)


def section_sellers(df: pd.DataFrame) -> None:
    st.subheader("🏪 Seller Concentration")

    seller_rev = (
        df.groupby("seller_id")["price"].sum().sort_values(ascending=False).reset_index()
    )
    seller_rev["cum_pct"] = (
        100 * seller_rev["price"].cumsum() / seller_rev["price"].sum()
    )
    seller_rev["rank"] = range(1, len(seller_rev) + 1)

    pareto = (seller_rev["cum_pct"] <= 80).sum() + 1
    total = len(seller_rev)

    fig = px.line(
        seller_rev,
        x="rank",
        y="cum_pct",
        title=f"Seller Pareto Curve — {pareto} sellers ({100*pareto/total:.1f}%) generate 80% of revenue",
        labels={"rank": "Sellers (ranked by revenue)", "cum_pct": "Cumulative % of revenue"},
    )
    fig.update_traces(line_color="#1e2d3e")
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80% threshold")
    fig.add_vline(x=pareto, line_dash="dot", line_color="red")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# Main
# ============================================================
def main() -> None:
    st.markdown(
        '<div class="main-header">🛒 Olist E-Commerce Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Interactive analytics over the Olist Brazilian marketplace '
        '(~100K orders · 2016–2018) · Built by Agustín Lannoo</div>',
        unsafe_allow_html=True,
    )

    try:
        df = load_data()
    except FileNotFoundError as e:
        st.error(
            "❌ Dataset not found. Please download the Olist CSVs into the `data/` folder.\n\n"
            "See instructions in `data/README.md`."
        )
        st.code(f"Missing: {e}")
        st.stop()

    filters = render_sidebar(df)
    filtered = apply_filters(df, filters)

    if filtered.empty:
        st.warning("No data for the selected filters. Try widening the range.")
        st.stop()

    section_kpis(filtered)
    st.markdown("---")
    section_temporal(filtered)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        section_categories(filtered)
    with c2:
        section_geography(filtered)

    st.markdown("---")
    section_reviews(filtered)
    st.markdown("---")
    section_sellers(filtered)


if __name__ == "__main__":
    main()
