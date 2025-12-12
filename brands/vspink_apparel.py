# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta
import unicodedata
import re

name = "VSPink Apparel - Bucket 03"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def clean_columns(df):
    """Fully sanitize all column names."""
    new_cols = {}
    for c in df.columns:
        col = unicodedata.normalize("NFKC", str(c))
        col = col.replace("–", "-").replace("—", "-")
        col = re.sub(r"\s+", " ", col).strip()
        new_cols[c] = col
    df.rename(columns=new_cols, inplace=True)
    return df

def transform_vspink_apparel(file) -> pd.DataFrame:
    df = pd.read_excel(file, header=0)

    # DEBUG → show raw headers
    st.write("🔍 Raw Columns Loaded:", list(df.columns))

    if df.iloc[0].isna().all():
        df = df.iloc[1:].copy()

    df = clean_columns(df)

    REQUIRED = ["Customer", "Supplier", "Supplier COO", "Program", "Article", "Qty (m)", "EX-mill"]
    for col in REQUIRED:
        if col not in df.columns:
            raise ValueError(f"❌ Required column missing: {col}")

    df["EX-mill"] = pd.to_datetime(df["EX-mill"], errors="coerce")
    df = df.dropna(subset=["EX-mill", "Article"])

    df["Sourcing Type"] = df["Supplier COO"].apply(lambda x: "LOCAL" if str(x).strip().upper() == "SL" else "FOREIGN")

    def compute_mcu_date(row):
        if row["Sourcing Type"] == "LOCAL":
            return row["EX-mill"] - relativedelta(months=3)
        else:
            return row["EX-mill"] - relativedelta(months=4)

    df["MCU Month"] = df.apply(compute_mcu_date, axis=1).dt.strftime("%b-%y")

    output_cols = ["Customer", "Supplier", "Supplier COO", "Program", "Article", "Qty (m)", "EX-mill", "MCU Month"]
    final_df = df[output_cols]

    pivot_df = final_df.pivot_table(
        index=["Customer", "Supplier", "Supplier COO", "Program", "Article"],
        columns="MCU Month",
        values="Qty (m)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    pivot_df.columns.name = None
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            df_out = transform_vspink_apparel(uploaded)

            st.subheader("📄 Preview Transformed MCU")
            st.dataframe(df_out.head())

            out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
            st.download_button(
                label="📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
