# brands/vspink_brief.py
import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta

name = "VSPink Brief - Bucket 03"

# -------------------------
# Utilities
# -------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def clean_columns(df):
    """Clean hidden spaces and normalize column names"""
    cleaned = {}
    for c in df.columns:
        new_c = str(c).strip().replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
        cleaned[c] = new_c
    df.rename(columns=cleaned, inplace=True)
    return df

def detect_column(df, keywords):
    """Detect column by keywords (case-insensitive)."""
    for c in df.columns:
        low = str(c).lower()
        for kw in keywords:
            if kw.lower() in low:
                return c
    return None

# -------------------------
# Transformation
# -------------------------
def transform_vspink_brief(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform VSPink Brief Buy Sheet → MCU Format
    - Converts EX-mill dates to Month columns (e.g., Oct-25, Nov-25)
    - Pivots quantities under respective months
    - Preserves metadata columns
    """
    df = df.copy()
    df = clean_columns(df)

    # Detect key columns
    article_col = detect_column(df, ["article"])
    exmill_col = detect_column(df, ["ex-mill", "ex mill", "exmill"])
    qty_col = detect_column(df, ["qty", "qty (m)"])
    
    if not article_col or not exmill_col or not qty_col:
        raise ValueError(f"Could not detect required columns. Found: {list(df.columns)}")

    # Parse EX-mill to datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")
    # Drop rows without EX-mill or Article
    df = df.dropna(subset=[exmill_col, article_col])
    if df.empty:
        return pd.DataFrame()

    # Normalize quantity
    df[qty_col] = pd.to_numeric(df[qty_col].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)

    # Create Month column from EX-mill date
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")  # e.g., Oct-25

    # Determine metadata columns (all except Qty, EX-mill, Month)
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]
    if not meta_cols:
        meta_cols = [article_col]

    # Group by metadata + Month, sum Qty
    grouped = df.groupby(meta_cols + ["Month"], dropna=False, as_index=False)[qty_col].sum()

    # Pivot Month into columns
    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="Month",
        values=qty_col,
        fill_value=0
    ).reset_index()

    # Sort month columns chronologically
    month_cols = [c for c in pivot_df.columns if c not in meta_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        order = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[meta_cols + order]

    # Flatten columns
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

# -------------------------
# Streamlit UI
# -------------------------
def render():
    st.header("VSPink Brief — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Brief Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_brief_file"
    )

    if uploaded:
        try:
            # Load CSV or Excel
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded, header=0)
                # If first row is blank (all Unnamed), skip it
                if df.columns.str.contains("Unnamed").all():
                    df = pd.read_excel(uploaded, header=1)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_vspink_brief(df)

            if transformed_df.empty:
                st.warning("No valid rows after parsing EX-mill dates or Article values.")
                return

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU")
            st.download_button(
                label="📥 Download MCU - VSPink Brief.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Brief.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Brief file: {e}")
