import streamlit as st
import pandas as pd
from io import BytesIO

name = "CKUW - Bucket 01"  

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    """Convert DataFrame to downloadable Excel bytes."""
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def transform_ckuw_plm_to_mcu(df):
    """Same logic as other PLM → MCU transformations."""
    df.columns = df.columns.str.strip()
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]
    return df

def render():
    st.header("CKUW — PLM Upload → MCU Format")
    uploaded = st.file_uploader("Upload CKUW PLM Upload file", type=["xlsx", "xls"], key="ckuw_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            df_out = transform_ckuw_plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(df_out.head())

            out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
            st.download_button(
                label="📥 Download MCU - CKUW.xlsx",
                data=out_bytes,
                file_name="MCU_CKUW.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error processing CKUW file: {e}")

