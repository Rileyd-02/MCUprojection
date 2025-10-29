# brands/ckuw.py
import streamlit as st
import pandas as pd
from utils.helpers import excel_to_bytes

# ----------------------------
# CKUW PLM Download → MCU logic
# ----------------------------
def transform_ckuw_plm_to_mcu(df):
    df.columns = df.columns.str.strip()
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    return df.loc[:, mask_keep]

# ----------------------------
# Streamlit page
# ----------------------------
def run_page():
    st.header("CKUW — PLM Download → MCU")
    
    plm_file = st.file_uploader("Upload PLM Download file (CKUW)", type=["xlsx","xls"], key="ckuw_plm")
    
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = transform_ckuw_plm_to_mcu(df)
            
            st.subheader("Preview — MCU")
            st.dataframe(df_out.head())
            
            out_bytes = excel_to_bytes(df_out, "MCU")
            st.download_button(
                "📥 Download MCU - CKUW",
                out_bytes,
                file_name="MCU_ckuw.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error processing CKUW PLM file: {e}")
