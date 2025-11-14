import streamlit as st
import pandas as pd
from io import BytesIO

name = "VSPink Apparel"

# -----------------------------
# Excel Output Helper
# -----------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# -----------------------------
# Transform Logic
# -----------------------------
def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:

    # Normalize all column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace("__", "_")
    )

    # Detect required columns
    article_col = next((c for c in df.columns if "article" in c), None)
    exmill_col = next((c for c in df.columns if "ex_mill" in c or "exmill" in c), None)
    qty_col = next((c for c in df.columns if "qty" in c), None)

    if not article_col or not exmill_col or not qty_col:
        raise ValueError(
            f"Could not detect required columns.\n"
            f"Detected columns: {df.columns.tolist()}"
        )

    # Convert EX-mill to datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # Drop rows without EX-mill or Article
    df = df.dropna(subset=[exmill_col, article_col])
    if df.empty:
        raise ValueError("No valid rows after EX-mill + Article filtering.")

    # Clean Qty
    df[qty_col] = (
        df[qty_col]
        .astype(str)
        .str.replace(",", "")
        .str.replace(" ", "")
    )
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Add "Month" for pivoting
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Identify metadata columns (everything except qty/exmill/month)
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month", "month"]]

    # Group
    grouped = df.groupby(meta_cols + ["Month"], as_index=False)[qty_col].sum()

    # Pivot into MCU format
    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="Month",
        values=qty_col,
        fill_value=0
    ).reset_index()

    # Convert columns to strings
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

# -----------------------------
# Streamlit Render UI
# -----------------------------
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            # Read with second row as header
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded, header=1)
            else:
                df = pd.read_excel(uploaded, header=1)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            # Transform
            transformed_df = transform_vspink_apparel(df)

            st.subheader("✅ Transformed MCU Output")
            st.dataframe(transformed_df.head())

            # Download button
            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU")
            st.download_button(
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
