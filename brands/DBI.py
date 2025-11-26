import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# Brand name for sidebar
name = "DBI - Bucket 02"

# -------------------------------------------------------
#   TRANSFORMATION: PLM Download  →  MCU Format
# -------------------------------------------------------
def transform_dbi_plm_to_mcu(df):
    """DBI PLM → MCU using simplified HugoBoss logic."""

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop SUM columns
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]

    # Detect month columns (Nov, Dec, Jan, Feb, etc.)
    month_cols = [
        c for c in df.columns
        if "-" in c or c[:3].isalpha()
    ]

    # Fill missing month values with 0
    if month_cols:
        df[month_cols] = df[month_cols].fillna(0)

    return df


# -------------------------------------------------------
#                       STREAMLIT UI
# -------------------------------------------------------
def render():
    st.header("DBI — PLM Download → MCU Format")

    uploaded_file = st.file_uploader(
        "Upload DBI PLM Download File",
        type=["xlsx", "xls"],
        key="dbi_plm"
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)

            # Apply HugoBoss-style transformation
            df_out = transform_dbi_plm_to_mcu(df)

            st.subheader("Preview — MCU Output")
            st.dataframe(df_out.head())

            output = excel_to_bytes(df_out)
            st.download_button(
                "📥 Download MCU Format",
                output,
                file_name="MCU_DBI.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
