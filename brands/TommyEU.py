import streamlit as st
import pandas as pd
from io import BytesIO
from utils import excel_to_bytes

name = "Tommy EU - Bucket 02"

# -----------------------------
# Transform Buy Sheet → PLM Upload
# -----------------------------
def buy_to_plm(df: pd.DataFrame) -> pd.DataFrame:
    # --- Step 1: Extract month names from first row ---
    month_row = df.iloc[0, 1:13].tolist()  # Jul to Jun
    months = [str(m).strip() for m in month_row]

    # --- Step 2: Real headers are in row 2 ---
    df.columns = df.iloc[2]
    df = df[3:].reset_index(drop=True)

    # --- Step 3: Keep only Style and month columns ---
    style_col = "Generic Article"
    if style_col not in df.columns:
        style_col = df.columns[0]  # fallback

    # --- Step 4: Trim Style numbers to first 8 chars ---
    df[style_col] = df[style_col].astype(str).str[:8]

    # --- Step 5: Keep only Style + month quantities ---
    month_indices = list(range(df.columns.get_loc(style_col)+1, df.columns.get_loc(style_col)+1+len(months)))
    df_months = df.iloc[:, month_indices].copy()
    df_months.columns = months

    # --- Step 6: Convert quantities to numeric ---
    for col in months:
        df_months[col] = pd.to_numeric(df_months[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    plm_df = pd.concat([df[[style_col]].reset_index(drop=True), df_months.reset_index(drop=True)], axis=1)
    plm_df = plm_df.rename(columns={style_col: "Style number"})
    return plm_df

# -----------------------------
# Transform PLM Download → MCU
# -----------------------------
def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    # Drop 'Sum of ' prefixed columns if present
    df = df.loc[:, ~df.columns.str.lower().str.startswith("sum of")]
    return df

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("Tommy EU — Buy Sheet → PLM Upload")
    buy_file = st.file_uploader("Upload Buy Sheet (Tommy EU)", type=["xlsx","xls"], key="tommy_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file, header=None)
            df_out = buy_to_plm(df)
            st.subheader("Preview — PLM Upload")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download PLM Upload",
                               out_bytes,
                               file_name="plm_upload_tommy_eu.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"❌ Error processing Buy Sheet: {e}")

    st.markdown("---")
    st.header("Tommy EU — PLM Download → MCU")
    plm_file = st.file_uploader("Upload PLM Download file (Tommy EU)", type=["xlsx","xls"], key="tommy_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download MCU",
                               out_bytes,
                               file_name="MCU_tommy_eu.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")

