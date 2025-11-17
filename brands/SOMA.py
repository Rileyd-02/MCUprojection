# brands/soma.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "SOMA"

# -----------------------------
# PLM Download → MCU
# -----------------------------
def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    # Clean column names
    df.columns = df.columns.str.strip()

    # Identify month columns (Jun → Dec, etc.)
    month_cols = [c for c in df.columns if c.lower() in ['jun','jul','aug','sep','oct','nov','dec']]

    # Identify Style column
    style_col = 'Style Number' if 'Style Number' in df.columns else df.columns[0]

    # Keep only Style + Month columns
    df_out = df[[style_col] + month_cols].copy()
    df_out = df_out.rename(columns={style_col: 'Style'})

    # Optional: convert month columns to numeric
    for col in month_cols:
        df_out[col] = pd.to_numeric(df_out[col].astype(str).str.replace(",",""), errors='coerce').fillna(0)

    return df_out

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("SOMA — PLM Download → MCU")
    plm_file = st.file_uploader("Upload PLM Download file (SOMA)", type=["xlsx","xls"], key="soma_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button(
                "📥 Download MCU",
                out_bytes,
                file_name="MCU_soma.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
