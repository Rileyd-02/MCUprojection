# brands/tommy_eu.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "Tommy EU"

# -----------------------------
# Transformations
# -----------------------------

def buy_to_plm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU Buy Sheet → PLM Upload format
    - Keeps Style number / U_OPTIONTYPE as first column
    - All buy month columns retained
    """
    df.columns = df.columns.str.strip()
    # Identify the first column containing "U_OPTIONTYPE" or "Style number"
    if "U_OPTIONTYPE (txt)|Buy (YYYYMMDD)" in df.columns:
        style_col = "U_OPTIONTYPE (txt)|Buy (YYYYMMDD)"
    else:
        style_col = df.columns[0]

    # Month columns start after style_col
    month_idx = df.columns.get_loc(style_col) + 1
    month_cols = df.columns[month_idx:]

    plm_df = df[[style_col] + list(month_cols)]
    plm_df = plm_df.rename(columns={style_col: "Style number"})
    return plm_df

def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU PLM Download → MCU Format
    - Keeps metadata columns
    - Month columns pivoted into MCU months
    """
    df.columns = df.columns.str.strip()

    # Drop "Sum of" columns if present
    month_cols = [c for c in df.columns if not c.lower().startswith("sum")]
    
    # Columns we want to keep in MCU index
    meta_cols = ["Style", "BOM", "Cycle", "Article", "Type of Const 1",
                 "Supplier", "UOM", "Composition", "Measurement", "Supplier Country", "Avg YY"]
    
    meta_cols = [c for c in meta_cols if c in df.columns]

    # Pivoting by meta columns
    pivot_df = df[meta_cols + month_cols].copy()

    # Ensure month columns are in correct order (JAN → DEC)
    month_order = ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"]
    existing_months = [m for m in month_order if m in pivot_df.columns]
    pivot_df = pivot_df[meta_cols + existing_months]

    return pivot_df

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("Tommy EU — Buy Sheet → PLM Upload")

    buy_file = st.file_uploader("Upload Tommy EU Buy Sheet", type=["xlsx","xls"], key="tommy_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file, header=0)
            plm_upload = buy_to_plm(df)
            st.subheader("Preview — PLM Upload")
            st.dataframe(plm_upload.head())
            out_bytes = excel_to_bytes(plm_upload)
            st.download_button("📥 Download PLM Upload", out_bytes, file_name="PLM_Upload_TommyEU.xlsx")
        except Exception as e:
            st.error(f"❌ Error processing Buy Sheet: {e}")

    st.markdown("---")
    st.header("Tommy EU — PLM Download → MCU Format")

    plm_file = st.file_uploader("Upload Tommy EU PLM Download", type=["xlsx","xls"], key="tommy_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file, header=0)
            mcu_df = plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(mcu_df.head())
            out_bytes = excel_to_bytes(mcu_df)
            st.download_button("📥 Download MCU", out_bytes, file_name="MCU_TommyEU.xlsx")
        except Exception as e:
            st.error(f"❌ Error processing PLM Download: {e}")
