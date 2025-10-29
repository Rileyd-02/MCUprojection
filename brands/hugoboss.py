import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# ---------- Transformations ----------
def transform_hugoboss_buy_to_plm(df):
    df.columns = df.columns.str.strip()
    material_idx = df.columns.get_loc("Material Number")
    month_cols = df.columns[material_idx+1:]
    final_df = df[["Material Number"] + list(month_cols)]
    return final_df

def transform_hugoboss_plm_to_mcu(df):
    df.columns = df.columns.str.strip()
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]
    return df

# ---------- Streamlit UI ----------
name = "HugoBoss - Bucket 02"

def render():
    st.header("Hugo Boss — Buy Sheet → PLM Download")
    buy_file = st.file_uploader("Upload Buy Sheet (HugoBoss)", type=["xlsx","xls"], key="hb_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file)
            df_out = transform_hugoboss_buy_to_plm(df)
            st.subheader("Preview — PLM Download")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download PLM Download", out_bytes, file_name="plm_download_hugoboss.xlsx")
        except Exception as e:
            st.error(f"Error processing HugoBoss Buy file: {e}")

    st.markdown("---")
    st.header("Hugo Boss — PLM Upload → MCU")
    plm_file = st.file_uploader("Upload PLM Upload file (HugoBoss)", type=["xlsx","xls"], key="hb_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = transform_hugoboss_plm_to_mcu(df)
            st.subheader("Preview — MCU")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download MCU", out_bytes, file_name="MCU_hugoboss.xlsx")
        except Exception as e:
            st.error(f"Error processing HugoBoss PLM upload: {e}")
