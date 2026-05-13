# Dataset — Olist Brazilian E-Commerce

This folder should contain the 9 CSV files from the Olist public dataset on Kaggle.

## How to download

### Option A — Manual download (recommended, 5 min)

1. Sign in / sign up at **https://www.kaggle.com** (free)
2. Go to **https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce**
3. Click the **Download** button (top right) → you get a `archive.zip` (~45 MB)
4. Unzip the file and place all 9 CSVs in this `data/` folder

### Option B — Kaggle API (if you already have it configured)

```bash
pip install kaggle
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/ --unzip
```

## Expected files

After download, this folder should contain exactly these 9 files:

```
data/
├── olist_customers_dataset.csv
├── olist_geolocation_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_orders_dataset.csv
├── olist_products_dataset.csv
├── olist_sellers_dataset.csv
└── product_category_name_translation.csv
```

## Dataset overview

- **Period:** Sept 2016 – Oct 2018
- **Volume:** ~100,000 orders
- **Coverage:** Brazilian e-commerce marketplace
- **Origin:** Olist Store (real anonymized data, released by the company)
- **License:** CC BY-NC-SA 4.0 (free for non-commercial use)
