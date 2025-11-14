import streamlit as st
import pandas as pd
from io import BytesIO
import re

name = "VSPink Apparel"

# ------------------------------
# Helper: Save Excel
# ------------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# ------------------------------
# Helper: Clean column names deeply
# ------------------------------
def deep_clean(col):
    if pd.isna(col):
        return ""
    col = str(col)
    col = col.replace("\u00A0", "")  # non-breaking space
    col = col.replace("\u202F", "")  # narrow NBSP
    col = col.replace("\t", "")
    col = col.replace("\n", "")
    col = col.strip()
    return col

# ------------------------------
# Transformation Logic
# ------------------------------
def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:

    # 1. Clean all column names
    original_cols = list(df.columns)
    clean_map = {}
    for c in df.columns:
        cleaned = (
            deep_clean(c)
            .lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )
        clean_map[c] = cleaned

    df = df.rename(columns=clean_map)

    # 2. Detect required columns using fuzzy matching
    def find_col(keyword):
        for orig, cleaned in clean_map.items():
            if keyword in cleaned:
                return orig
        return None

    article_col = find_col("article")
    exmill_col = find_col("exmill")
    qty_col = find_col("qty")

    if not article_col or not exmill_col or not qty_col:
        raise ValueError(
            f"Column detection failed.\n"
            f"Detected cleaned columns:\n{clean_map}"
        )

    # 3. Convert EX-mill
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # 4. Clean Qty
    df[qty_col] = (
        df[qty_col]
        .astype(str)
        .str.replace(",", "")
        .str.replace(" ", "")
        .str.replace("\u00A0", "")
        .str.replace("\u202F", "")
    )
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # 5. Validate required rows exist
    df = df.dropna(subset=[exmill_col, article_col])
    if df.empty:
        raise ValueError("No valid rows found after filtering EX-mill + Article.")

    # 6. MCU month = EX-mill month (MMM-YY)
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # 7. Identify metadata columns
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]

    # 8. Group rows
    grouped = df.groupby(meta_cols + ["Month"], as_index=False)[qty_col].sum()

    # 9. Pivot to MCU format
    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="Month",
        values=qty_col,
        fill_value=0
    ).reset_index()

    # 10. Reorder month columns chronologically
    month_cols = [c for c in pivot_df.columns if c not in meta_cols]
    parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
    ordered = [m for _, m in sorted(zip(parsed, month_cols))]

    final_df = pivot_df[meta_cols + ordered]

    return final_df


# ------------------------------
# Streamlit UI
# ------------------------------
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            # Read with row 0 as header (your file has headers in row 0)
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_vspink_apparel(df)

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU")

            st.download_button(
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
