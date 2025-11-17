import streamlit as st
import pandas as pd
from io import BytesIO
from utils import excel_to_bytes

# --------------------------
# Transformations
# --------------------------

def buy_to_plm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU Buy Sheet → PLM Upload
    - Row 0: month names (Jul, Aug, ...)
    - Row 1: PO Proposal (skip)
    - Row 2: actual headers
    - Keep only Style number and month columns
    - Trim style numbers to first 8 characters
    """
    # Capture months from row 0 (columns 1 to 13)
    months = df.iloc[0, 1:13].tolist()
    months = [str(m).strip() for m in months]

    # Drop first two rows
    df = df.drop([0,1]).reset_index(drop=True)

    # Set row 0 as header safely
    header_row = df.iloc[0].tolist()
    header_row = [str(h).strip() for h in header_row]
    df = df[1:].reset_index(drop=True)
    df.columns = header_row

    # Style column
    style_col = "Generic Article"
    if style_col not in df.columns:
        style_col = df.columns[0]

    # Keep only style + month columns
    style_series = df[style_col].astype(str).str[:8]  # trim to 8 chars
    df_months = df.iloc[:, df.columns.get_loc(style_col)+1 : df.columns.get_loc(style_col)+1+len(months)]
    df_months.columns = months

    plm_df = pd.concat([style_series.reset_index(drop=True), df_months.reset_index(drop=True)], axis=1)
    
    # Ensure month columns are numeric
    for col in months:
        plm_df[col] = pd.to_numeric(df_months[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    plm_df = plm_df.rename(columns={style_col: "Style number"})
    return plm_df

def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU PLM Download → MCU Format
    - Drops 'Sum of ' prefixed columns
    - Keeps only actual month columns (Jul–Jun)
    """
    df.columns = df.columns.str.strip()
    # Drop 'Sum of ' columns if exist
    df = df.loc[:, ~df.columns.str.lower().str.startswith("sum of")]
    return df

# --------------------------
# Streamlit UI
# --------------------------
name = "Tommy EU"

def render():
    st.header("Tommy EU — Buy Sheet → PLM Upload")
    buy_file = st.file_uploader("Upload Buy Sheet (Tommy EU)", type=["xlsx","xls"], key="tommy_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file, header=None)  # read without header
            df_out = buy_to_plm(df)
            st.subheader("Preview — PLM Upload")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button(
                "📥 Download PLM Upload",
                out_bytes,
                file_name="plm_upload_tommy_eu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
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
            st.download_button(
                "📥 Download MCU",
                out_bytes,
                file_name="MCU_tommy_eu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
