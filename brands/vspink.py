import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# ---------- Transformation ----------
def transform_vspink_data(df):
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")
    exmill_col = [c for c in df.columns if "ex-mill" in c.lower()][0]
    qty_col = [c for c in df.columns if "qty" in c.lower()][0]
    article_col = [c for c in df.columns if "article" in c.lower()][0]

    metadata_cols = [
        "Customer", "Supplier", "Supplier COO", "Production Plant (region)",
        "Program", "Construction", article_col,
        "# of repeats in Article ( optional)", "Composition",
        "If Yarn Dyed/ Piece Dyed", exmill_col
    ]
    metadata_cols = [c for c in metadata_cols if c in df.columns]

    df["EX-mill_dt"] = pd.to_datetime(df[exmill_col], errors="coerce")
    df["Month-Year"] = df["EX-mill_dt"].dt.strftime("%b-%y")

    df[qty_col] = df[qty_col].astype(str).str.replace(",", "", regex=False).str.strip()
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    grouped = df.groupby([article_col, "Month-Year"], as_index=False)[qty_col].sum()
    pivot_df = grouped.pivot_table(index=article_col, columns="Month-Year", values=qty_col, fill_value=0).reset_index()

    parsed_months = pd.to_datetime(pivot_df.columns[1:], format="%b-%y", errors="coerce")
    month_order = parsed_months.sort_values().strftime("%b-%y").tolist()
    pivot_df = pivot_df[[article_col] + month_order]

    meta = df.groupby(article_col, as_index=False)[metadata_cols].first()
    final_df = pd.merge(meta, pivot_df, on=article_col, how="left")

    return final_df

# ---------- Streamlit UI ----------
name = "VSPINK Brief - Bucket 03"

def render():
    st.header("VSPINK Brief")
    up = st.file_uploader("Upload VSPINK file", type=["xlsx","xls"], key="vspink_file")
    if up:
        try:
            df = pd.read_excel(up)
            df_v = transform_vspink_data(df)
            st.subheader("Preview — VSPINK MCU")
            st.dataframe(df_v.head())
            out_bytes = excel_to_bytes(df_v)
            st.download_button("📥 Download VSPINK MCU", out_bytes, file_name="vspink_mcu.xlsx")
        except Exception as e:
            st.error(f"Error processing VSPINK file: {e}")
