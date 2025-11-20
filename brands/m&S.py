import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# Brand name for sidebar
name = "M&S - Bucket 03"

# -------------------------------------------------------
#   TRANSFORMATION: PLM Download  →  MCU Format
# -------------------------------------------------------
def transform_ms_plm_to_mcu(df):
    """M&S PLM → MCU with HugoBoss-style logic."""

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop all columns starting with "sum"
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]

    # (Optional) fill month values with 0
    # Only if they are numeric months like Nov, Dec, Jan...
    month_cols = [c for c in df.columns if "-" in c or c[:3].isalpha()]
    df[month_cols] = df[month_cols].fillna(0)

    return df


# -------------------------------------------------------
#                  STREAMLIT UI
# -------------------------------------------------------
def render():
    st.header("M&S — PLM Download → MCU Format")

    uploaded_file = st.file_uploader(
        "Upload M&S PLM Download File",
        type=["xlsx", "xls"],
        key="ms_plm"
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)

            # Transform using HugoBoss-style MCU logic
            df_final = transform_ms_plm_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(df_final.head())

            out_bytes = excel_to_bytes(df_final)

            st.download_button(
                "📥 Download MCU Format",
                out_bytes,
                file_name="MCU_M&S.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing M&S PLM file: {e}")
