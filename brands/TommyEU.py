# brands/tommy_eu.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "Tommy EU"

# -----------------------------
# Transformation function
# -----------------------------
def transform_tommy_eu_buy_to_mcu(df):
    """
    Converts Tommy EU buy sheet to MCU format.
    - RM Ex Mill (column U) → Month columns
    - Qty column (Y) fills the month quantities
    """
    # Clean column names
    df.columns = df.columns.str.strip()

    # Ensure expected columns exist
    expected_cols = ["Supplier", "Article No", "Measurement", "Supplier Country", 
                     "Type of Cons1", "Plant", "RM Ex Mill", "Qty"]
    for col in expected_cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in uploaded file.")

    df = df[expected_cols]

    # Convert RM Ex Mill to datetime
    df["RM Ex Mill"] = pd.to_datetime(df["RM Ex Mill"], errors="coerce")
    df = df.dropna(subset=["RM Ex Mill"])

    # Extract month labels
    df["Month"] = df["RM Ex Mill"].dt.strftime("%b").str.upper()

    # Pivot so months become columns, quantities fill cells
    pivot_df = df.pivot_table(
        index=["Supplier", "Article No", "Measurement", "Supplier Country", 
               "Type of Cons1", "Plant"],
        columns="Month",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Ensure all months exist in order
    month_order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    for m in month_order:
        if m not in pivot_df.columns:
            pivot_df[m] = 0

    pivot_df = pivot_df[["Supplier", "Article No", "Measurement", "Supplier Country", 
                         "Type of Cons1", "Plant"] + month_order]

    return pivot_df

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("Tommy EU — Buy Sheet → MCU Format")

    uploaded_file = st.file_uploader("Upload Tommy EU Buy Sheet", 
                                     type=["xlsx", "xls"], 
                                     key="tommy_eu_file")

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, header=0)

            transformed_df = transform_tommy_eu_buy_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df)

            st.download_button(
                "📥 Download MCU",
                out_bytes,
                file_name="MCU_TommyEU.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing Tommy EU file: {e}")
