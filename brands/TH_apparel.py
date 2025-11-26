import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "TH Apparel - Bucket 02"

# -------------------------------------------------------
#   TRANSFORMATION: PLM Download  →  MCU Format
# -------------------------------------------------------
def transform_th_plm_to_mcu(df):
    """TH Apparel PLM → MCU using HugoBoss logic."""

    # Clean header names
    df.columns = df.columns.str.strip()

    # Drop columns starting with "sum"
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]

    # Detect month columns (e.g., Nov, Oct, Jan, Feb, Mar, etc.)
    month_cols = [
        c for c in df.columns
        if "-" in c or c[:3].isalpha()     # captures Nov, Dec, Jan, Feb, etc.
    ]

    # Replace missing values in month columns with 0
    df[month_cols] = df[month_cols].fillna(0)

    return df


# -------------------------------------------------------
#                  STREAMLIT UI
# -------------------------------------------------------
def render():
    st.header("TH Apparel — PLM Download → MCU Format")

    uploaded_file = st.file_uploader(
        "Upload TH Apparel PLM Download File",
        type=["xlsx", "xls"],
        key="th_plm"
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)

            # Transform using simplified HugoBoss logic
            df_final = transform_th_plm_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(df_final.head())

            output = excel_to_bytes(df_final)
            st.download_button(
                "📥 Download MCU Format",
                output,
                file_name="MCU_TH_Apparel.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
