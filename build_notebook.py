"""
Build the Olist EDA Jupyter notebook programmatically.
"""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text))


# ==========================================================================
# 1. Title & introduction
# ==========================================================================
md("""# Olist Brazilian E-Commerce — Exploratory Data Analysis

**Author:** Agustín Lannoo
**Dataset:** [Olist Brazilian E-Commerce on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
**Period covered:** September 2016 – October 2018

---

## Business questions addressed

1. **Sales evolution** — How did GMV and order volume grow over time?
2. **Product mix** — Which categories drive most of the revenue?
3. **Geography** — Where are customers concentrated and where is the opportunity?
4. **Delivery performance** — How fast is the marketplace and how does it impact satisfaction?
5. **Seller concentration** — Is GMV concentrated in a few sellers (Pareto)?
6. **Customer satisfaction** — What predicts a 5-star vs 1-star review?

---

## Methodology

- Data loading and inspection of 9 relational tables
- Data quality audit (missing values, duplicates, anomalies)
- Joining transactional tables into an analytical dataset
- Univariate, bivariate and multivariate analysis
- Time series and geographic analysis
- Conclusions translated into business recommendations
""")

# ==========================================================================
# 2. Setup
# ==========================================================================
md("## 1. Setup & Imports")

code("""# Core
import pandas as pd
import numpy as np
from pathlib import Path

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# Settings
pd.set_option('display.max_columns', 50)
pd.set_option('display.width', 200)
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 100
sns.set_style('whitegrid')
sns.set_palette('viridis')

# Paths
DATA_DIR = Path('../data')
FIG_DIR = Path('../outputs/figures')
FIG_DIR.mkdir(parents=True, exist_ok=True)

print('Setup complete.')""")

# ==========================================================================
# 3. Data Loading
# ==========================================================================
md("""## 2. Data Loading

The Olist dataset is normalized across 8 tables plus a translation table. We'll load all of them and inspect the relationships.""")

code("""# Load all 9 CSV files
df_customers  = pd.read_csv(DATA_DIR / 'olist_customers_dataset.csv')
df_geo        = pd.read_csv(DATA_DIR / 'olist_geolocation_dataset.csv')
df_items      = pd.read_csv(DATA_DIR / 'olist_order_items_dataset.csv')
df_payments   = pd.read_csv(DATA_DIR / 'olist_order_payments_dataset.csv')
df_reviews    = pd.read_csv(DATA_DIR / 'olist_order_reviews_dataset.csv')
df_orders     = pd.read_csv(DATA_DIR / 'olist_orders_dataset.csv')
df_products   = pd.read_csv(DATA_DIR / 'olist_products_dataset.csv')
df_sellers    = pd.read_csv(DATA_DIR / 'olist_sellers_dataset.csv')
df_category   = pd.read_csv(DATA_DIR / 'product_category_name_translation.csv')

# Quick check
tables = {
    'customers':  df_customers,
    'geolocation': df_geo,
    'order_items': df_items,
    'payments':   df_payments,
    'reviews':    df_reviews,
    'orders':     df_orders,
    'products':   df_products,
    'sellers':    df_sellers,
    'category':   df_category,
}

summary = pd.DataFrame({
    'table': list(tables.keys()),
    'rows':  [df.shape[0] for df in tables.values()],
    'cols':  [df.shape[1] for df in tables.values()],
    'memory_mb': [round(df.memory_usage(deep=True).sum() / 1024**2, 2) for df in tables.values()],
})
print('Tables loaded:')
display(summary)""")

# ==========================================================================
# 4. Data Quality Audit
# ==========================================================================
md("""## 3. Data Quality Audit

Before any analysis, we audit each table for missing values, duplicates, and inconsistencies. This is non-negotiable in any real-world dataset.""")

code("""# Missing values across tables
print('Missing values by table:\\n')
for name, df in tables.items():
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        print(f'  {name}:')
        for col, n in missing.items():
            pct = 100 * n / len(df)
            print(f'    - {col}: {n:,} ({pct:.1f}%)')
        print()
    else:
        print(f'  {name}: no missing values')
        print()""")

code("""# Duplicate detection on primary keys
print('Duplicate primary keys:\\n')
checks = [
    ('orders',    df_orders,    'order_id'),
    ('customers', df_customers, 'customer_id'),
    ('products',  df_products,  'product_id'),
    ('sellers',   df_sellers,   'seller_id'),
]
for name, df, key in checks:
    dups = df[key].duplicated().sum()
    status = '✅ OK' if dups == 0 else f'⚠️  {dups} duplicates'
    print(f'  {name}.{key}: {status}')""")

# ==========================================================================
# 5. Data Preparation
# ==========================================================================
md("""## 4. Data Preparation

We build a wide analytical dataset by joining the main tables. The grain is **one row per order item**, which is the lowest meaningful unit for revenue and product-level analysis.""")

code("""# Convert date columns to datetime
date_cols = [
    'order_purchase_timestamp',
    'order_approved_at',
    'order_delivered_carrier_date',
    'order_delivered_customer_date',
    'order_estimated_delivery_date',
]
for col in date_cols:
    df_orders[col] = pd.to_datetime(df_orders[col], errors='coerce')

df_reviews['review_creation_date'] = pd.to_datetime(df_reviews['review_creation_date'], errors='coerce')
df_reviews['review_answer_timestamp'] = pd.to_datetime(df_reviews['review_answer_timestamp'], errors='coerce')

print('Date columns converted.')
print('\\nOrder date range:')
print(f'  From: {df_orders[\"order_purchase_timestamp\"].min()}')
print(f'  To:   {df_orders[\"order_purchase_timestamp\"].max()}')""")

code("""# Translate Portuguese category names to English
df_products = df_products.merge(df_category, on='product_category_name', how='left')

# Build the master analytical dataset (one row per order item)
df = (
    df_items
    .merge(df_orders, on='order_id', how='left')
    .merge(df_customers, on='customer_id', how='left')
    .merge(df_products[['product_id', 'product_category_name_english']], on='product_id', how='left')
    .merge(df_sellers, on='seller_id', how='left')
)

# Derived columns
df['order_year_month'] = df['order_purchase_timestamp'].dt.to_period('M').astype(str)
df['order_year'] = df['order_purchase_timestamp'].dt.year
df['order_month'] = df['order_purchase_timestamp'].dt.month
df['order_dow'] = df['order_purchase_timestamp'].dt.dayofweek
df['order_hour'] = df['order_purchase_timestamp'].dt.hour
df['delivery_time_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
df['estimated_vs_actual_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.days
df['is_late'] = df['estimated_vs_actual_days'] > 0
df['total_item_value'] = df['price'] + df['freight_value']

print(f'Master dataset: {df.shape[0]:,} rows × {df.shape[1]} columns')
df.head(3)""")

# ==========================================================================
# 6. Sales Overview
# ==========================================================================
md("""## 5. Sales Overview

High-level KPIs that any e-commerce stakeholder would ask for first.""")

code("""# Headline KPIs (deduplicate orders for order-level metrics)
orders_unique = df.drop_duplicates(subset='order_id')

total_revenue = df['price'].sum()
total_freight = df['freight_value'].sum()
total_orders = orders_unique['order_id'].nunique()
total_items = df.shape[0]
total_customers = df['customer_unique_id'].nunique()
aov = total_revenue / total_orders
items_per_order = total_items / total_orders

print('HEADLINE KPIs')
print('=' * 50)
print(f'  Total revenue (price)   :  R$ {total_revenue:>15,.2f}')
print(f'  Total freight           :  R$ {total_freight:>15,.2f}')
print(f'  Total orders            :  {total_orders:>18,}')
print(f'  Total items sold        :  {total_items:>18,}')
print(f'  Unique customers        :  {total_customers:>18,}')
print(f'  Average order value     :  R$ {aov:>15,.2f}')
print(f'  Avg items per order     :  {items_per_order:>18,.2f}')""")

# ==========================================================================
# 7. Temporal Analysis
# ==========================================================================
md("""## 6. Temporal Analysis

How did the marketplace evolve month over month? Is there seasonality? Which days of the week and hours concentrate orders?""")

code("""# Monthly revenue and order count
monthly = (
    df.drop_duplicates(subset='order_id')
    .groupby('order_year_month')
    .agg(orders=('order_id', 'count'), revenue=('price', 'sum'))
    .reset_index()
)

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
axes[0].plot(monthly['order_year_month'], monthly['revenue'], marker='o', color='#2e7eb8')
axes[0].set_title('Monthly Revenue', fontsize=14, fontweight='bold')
axes[0].set_ylabel('Revenue (R$)')
axes[0].grid(True, alpha=0.3)

axes[1].plot(monthly['order_year_month'], monthly['orders'], marker='o', color='#e07b00')
axes[1].set_title('Monthly Orders', fontsize=14, fontweight='bold')
axes[1].set_ylabel('Number of orders')
axes[1].set_xlabel('Year-Month')
plt.xticks(rotation=45)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(FIG_DIR / '01_monthly_evolution.png', dpi=150, bbox_inches='tight')
plt.show()

print(f\"\\nGrowth: {monthly['revenue'].iloc[-1]/monthly['revenue'].iloc[0]:.1f}x from {monthly['order_year_month'].iloc[0]} to {monthly['order_year_month'].iloc[-1]}\")""")

code("""# Day-of-week and hour-of-day patterns
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
dow_counts = df.drop_duplicates(subset='order_id').groupby('order_dow').size()
axes[0].bar(dow_names, dow_counts.values, color='#2e7eb8')
axes[0].set_title('Orders by Day of Week', fontweight='bold')
axes[0].set_ylabel('Orders')

hour_counts = df.drop_duplicates(subset='order_id').groupby('order_hour').size()
axes[1].bar(hour_counts.index, hour_counts.values, color='#e07b00')
axes[1].set_title('Orders by Hour of Day', fontweight='bold')
axes[1].set_xlabel('Hour')
axes[1].set_ylabel('Orders')

plt.tight_layout()
plt.savefig(FIG_DIR / '02_temporal_patterns.png', dpi=150, bbox_inches='tight')
plt.show()""")

# ==========================================================================
# 8. Product Categories
# ==========================================================================
md("""## 7. Product Category Mix

Where does the revenue come from? Is there a Pareto pattern (80% of revenue from 20% of categories)?""")

code("""# Top categories by revenue
cat_revenue = (
    df.groupby('product_category_name_english')
    .agg(revenue=('price', 'sum'), orders=('order_id', 'nunique'))
    .sort_values('revenue', ascending=False)
)
cat_revenue['revenue_pct'] = 100 * cat_revenue['revenue'] / cat_revenue['revenue'].sum()
cat_revenue['cumulative_pct'] = cat_revenue['revenue_pct'].cumsum()

# Pareto: which N categories make up 80% of revenue?
pareto_80 = (cat_revenue['cumulative_pct'] <= 80).sum() + 1

fig, ax = plt.subplots(figsize=(14, 6))
top15 = cat_revenue.head(15)
ax.barh(top15.index[::-1], top15['revenue'].values[::-1], color='#2e7eb8')
ax.set_title('Top 15 Categories by Revenue', fontweight='bold')
ax.set_xlabel('Revenue (R$)')
plt.tight_layout()
plt.savefig(FIG_DIR / '03_top_categories.png', dpi=150, bbox_inches='tight')
plt.show()

print(f'\\n📊 Pareto: {pareto_80} out of {len(cat_revenue)} categories ({100*pareto_80/len(cat_revenue):.1f}%) account for ~80% of revenue.')""")

# ==========================================================================
# 9. Geographic Analysis
# ==========================================================================
md("""## 8. Geographic Distribution

Brazil has 26 states + DF. How concentrated is the customer base geographically? Which regions are underexploited?""")

code("""# Customers and revenue by state
state_data = (
    df.groupby('customer_state')
    .agg(orders=('order_id', 'nunique'),
         customers=('customer_unique_id', 'nunique'),
         revenue=('price', 'sum'))
    .sort_values('revenue', ascending=False)
)
state_data['revenue_pct'] = 100 * state_data['revenue'] / state_data['revenue'].sum()

fig, ax = plt.subplots(figsize=(14, 6))
top15 = state_data.head(15)
ax.bar(top15.index, top15['revenue'].values, color='#2e7eb8')
ax.set_title('Top 15 States by Revenue', fontweight='bold')
ax.set_xlabel('State')
ax.set_ylabel('Revenue (R$)')
plt.tight_layout()
plt.savefig(FIG_DIR / '04_revenue_by_state.png', dpi=150, bbox_inches='tight')
plt.show()

top3_pct = state_data.head(3)['revenue_pct'].sum()
print(f'\\n📍 Top 3 states account for {top3_pct:.1f}% of revenue.')
print(f'    {state_data.head(3).index.tolist()}')""")

# ==========================================================================
# 10. Delivery Analysis
# ==========================================================================
md("""## 9. Delivery Performance

How long does it take to deliver? How does delivery time impact customer satisfaction (review scores)?""")

code("""# Delivery time distribution and impact on reviews
delivered = df[df['delivery_time_days'].notna() & (df['delivery_time_days'] >= 0)].copy()
delivered = delivered.drop_duplicates(subset='order_id')

# Merge reviews
delivered = delivered.merge(df_reviews[['order_id', 'review_score']], on='order_id', how='left')

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(delivered['delivery_time_days'].clip(0, 60), bins=60, color='#2e7eb8', edgecolor='white')
axes[0].axvline(delivered['delivery_time_days'].median(), color='red', linestyle='--', label=f\"Median: {delivered['delivery_time_days'].median():.0f} days\")
axes[0].set_title('Delivery Time Distribution (capped at 60 days)', fontweight='bold')
axes[0].set_xlabel('Days to deliver')
axes[0].set_ylabel('Orders')
axes[0].legend()

review_by_delivery = delivered.groupby('review_score')['delivery_time_days'].mean()
axes[1].bar(review_by_delivery.index.astype(int), review_by_delivery.values, color='#e07b00')
axes[1].set_title('Average Delivery Time by Review Score', fontweight='bold')
axes[1].set_xlabel('Review score (stars)')
axes[1].set_ylabel('Avg delivery days')

plt.tight_layout()
plt.savefig(FIG_DIR / '05_delivery_analysis.png', dpi=150, bbox_inches='tight')
plt.show()

late_pct = 100 * delivered['is_late'].sum() / len(delivered)
print(f'\\n📦 Median delivery time: {delivered[\"delivery_time_days\"].median():.0f} days')
print(f'⏰ Orders delivered LATE (vs estimate): {late_pct:.1f}%')""")

# ==========================================================================
# 11. Seller Analysis
# ==========================================================================
md("""## 10. Seller Concentration

Are sales evenly distributed across sellers, or do a few sellers drive the majority of revenue? This impacts marketplace strategy.""")

code("""# Seller revenue Pareto
seller_revenue = (
    df.groupby('seller_id')
    .agg(revenue=('price', 'sum'), orders=('order_id', 'nunique'))
    .sort_values('revenue', ascending=False)
)
seller_revenue['revenue_pct'] = 100 * seller_revenue['revenue'] / seller_revenue['revenue'].sum()
seller_revenue['cumulative_pct'] = seller_revenue['revenue_pct'].cumsum()

pareto_seller = (seller_revenue['cumulative_pct'] <= 80).sum() + 1
total_sellers = len(seller_revenue)

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(range(1, len(seller_revenue) + 1), seller_revenue['cumulative_pct'].values, color='#2e7eb8')
ax.axhline(80, color='red', linestyle='--', alpha=0.7, label='80% of revenue')
ax.axvline(pareto_seller, color='red', linestyle=':', alpha=0.7, label=f'{pareto_seller} sellers')
ax.set_title('Seller Concentration (Pareto Curve)', fontweight='bold')
ax.set_xlabel('Number of sellers (sorted by revenue)')
ax.set_ylabel('Cumulative % of revenue')
ax.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / '06_seller_pareto.png', dpi=150, bbox_inches='tight')
plt.show()

print(f'\\n🏪 Total sellers: {total_sellers:,}')
print(f'   Top {pareto_seller} sellers ({100*pareto_seller/total_sellers:.1f}%) generate 80% of revenue.')""")

# ==========================================================================
# 12. Reviews
# ==========================================================================
md("""## 11. Customer Satisfaction (Reviews)

How are review scores distributed? What variables correlate with high or low scores?""")

code("""# Review score distribution
fig, ax = plt.subplots(figsize=(10, 5))
review_counts = df_reviews['review_score'].value_counts().sort_index()
ax.bar(review_counts.index, review_counts.values, color=['#c0392b','#e67e22','#f1c40f','#27ae60','#16a085'])
ax.set_title('Distribution of Review Scores', fontweight='bold')
ax.set_xlabel('Score (1 to 5 stars)')
ax.set_ylabel('Number of reviews')
for i, v in enumerate(review_counts.values):
    ax.text(review_counts.index[i], v + 500, f'{100*v/review_counts.sum():.0f}%', ha='center')
plt.tight_layout()
plt.savefig(FIG_DIR / '07_review_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

avg_score = df_reviews['review_score'].mean()
positive_pct = 100 * (df_reviews['review_score'] >= 4).sum() / len(df_reviews)
print(f'\\n⭐ Average review score: {avg_score:.2f}')
print(f'   Positive reviews (4-5 stars): {positive_pct:.1f}%')""")

# ==========================================================================
# 13. Key Findings
# ==========================================================================
md("""## 12. Key Findings

> *Concrete numbers from this analysis (fill in after running the notebook).*

1. **Growth:** the marketplace grew approximately [X]× in monthly revenue between [Sept 2016] and [Aug 2018], with the strongest growth period being [period].
2. **Category mix:** [N] categories ([X%] of catalog) generate ~80% of revenue — a classic Pareto distribution that supports a tiered category management strategy.
3. **Geographic concentration:** São Paulo, Rio de Janeiro and Minas Gerais together represent ~[X%] of revenue, leaving the North and Northeast regions underexploited.
4. **Delivery impact on satisfaction:** orders delivered in <10 days average a [X]-star rating, while orders over 30 days drop to [Y] stars — delivery time is the strongest operational driver of CSAT.
5. **Seller Pareto:** [X] sellers (~[X%] of the seller base) generate 80% of GMV, indicating a "long tail" supply side with massive concentration in top performers.
6. **Review skew:** [X%] of reviews are 4 or 5 stars — the average customer is satisfied, but the [Y%] of 1-star reviews are heavily correlated with late deliveries.
""")

# ==========================================================================
# 14. Next Steps
# ==========================================================================
md("""## 13. Next Steps

- 📊 Build an interactive Streamlit dashboard for stakeholders ([see `streamlit_app/app.py`](../streamlit_app/app.py))
- 🤖 Predictive model: estimate review score from order features (delivery time, freight, category)
- 🗺️ Geographic visualization with a real Brazilian map (folium / geopandas)
- 📅 Cohort analysis: customer retention by acquisition month
- 💰 Margin analysis (would require cost data, not in the public dataset)
""")

# ==========================================================================
# Save
# ==========================================================================
nb['cells'] = cells

# Add metadata
nb.metadata = {
    'kernelspec': {
        'display_name': 'Python 3',
        'language': 'python',
        'name': 'python3',
    },
    'language_info': {
        'name': 'python',
        'version': '3.11',
    },
}

out_path = Path('notebooks/01_olist_eda.ipynb')
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, 'w') as f:
    nbf.write(nb, f)

code_count = sum(1 for c in cells if c.cell_type == 'code')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
print(f'Notebook written: {out_path}')
print(f'Total cells: {len(cells)} ({code_count} code, {md_count} markdown)')
