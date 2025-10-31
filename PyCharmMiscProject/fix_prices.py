import pandas as pd
import numpy as np

# Path to your Excel file
excel_path = "/Users/Aarya/Downloads/Form 4 Raw Data.xlsx"

# Load all sheets from the workbook
sheets = pd.read_excel(excel_path, sheet_name=None, engine="openpyxl")

fixed_dataframes = []

for name, df in sheets.items():
    print(f"\n📄 Processing sheet: {name}")

    # Normalize column names
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Ensure expected columns exist
    required_cols = [
        "officer_name", "officer_title", "transaction_code", "transaction_type",
        "transaction_date", "shares", "price_per_share", "security_title"
    ]
    if not all(col in df.columns for col in required_cols):
        print(f"⚠️ Skipping {name}: missing required columns — found {list(df.columns)}")
        continue

    # Convert transaction_date to datetime
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # Force price column to be numeric
    df["price_per_share"] = pd.to_numeric(df["price_per_share"], errors="coerce")

    # Identify rows with missing or zero prices
    missing_mask = (df["price_per_share"].isna()) | (df["price_per_share"] == 0)

    # Fill 'A' transaction prices based on average price of same day
    a_mask = (
        (df["transaction_code"].astype(str).str.upper() == "A")
        & missing_mask
    )
    if a_mask.sum() > 0:
        # Compute average prices per day (excluding 0)
        date_avgs = (
            df[df["price_per_share"] > 0]
            .groupby("transaction_date")["price_per_share"]
            .mean()
        )

        # Assign the same-day average price
        df.loc[a_mask, "price_per_share"] = df.loc[a_mask].apply(
            lambda row: date_avgs.get(row["transaction_date"], np.nan), axis=1
        )

    # Forward-fill any remaining missing prices (same company)
    df["price_per_share"] = df["price_per_share"].replace(0, np.nan).ffill()

    # Fill any remaining missing prices with the overall average of the sheet
    if df["price_per_share"].isna().any():
        overall_avg = df["price_per_share"].mean(skipna=True)
        df["price_per_share"] = df["price_per_share"].fillna(overall_avg)

    # Final safety: make sure it's all numeric floats
    df["price_per_share"] = df["price_per_share"].astype(float)

    # Add sheet name for tracking
    df["sheet_name"] = name

    # Verify completeness
    if df["price_per_share"].isna().sum() == 0:
        print(f"✅ All prices filled in {name}")
    else:
        print(f"⚠️ Warning: still {df['price_per_share'].isna().sum()} missing in {name}")

    fixed_dataframes.append(df)

# Combine all sheets into one DataFrame
combined_df = pd.concat(fixed_dataframes, ignore_index=True)

# Save cleaned data
combined_df.to_csv("form4_data_fixed.csv", index=False)

print("\n🎉 All sheets cleaned and saved as 'form4_data_fixed.csv'")
print(f"✅ Total rows: {len(combined_df)} | Missing prices: {combined_df['price_per_share'].isna().sum()}")
