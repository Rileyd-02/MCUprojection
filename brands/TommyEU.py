# brands/tommy_eu.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "Tommy EU"

# -------------------- Helpers --------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name="Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# -------------------- Transformations --------------------
def buy_to_plm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU Buy Sheet → PLM Upload
    - Row 0: month names (Jul, Aug, ...)
    - Row 1: PO Proposal (skip)
    - Row 2: actual headers
    - Keep only Style number and month columns
    """
    # Capture months from row 0 (columns 1 to 13)
    months = df.iloc[0, 1:13].tolist()
    months = [str(m).strip() for m in months]

    # Drop first two rows
    df = df.drop([0,1]).reset_index(drop=True)

    # Set row 0 as header
    df.columns = df.iloc[0].astype(str).str.strip()
    df = df[1:].reset_index(drop=True)

    # Style column
    style_col = "Generic Article"
    if style_col not in df.columns:
        style_col = df.columns[0]

    # Keep only style + month columns
    # The month values are usually numeric in columns starting from col 7 (adjust as needed)
    month_cols = months
    df_months = df.iloc[:,  df.columns.get_loc(style_col)+1 : df.columns.get_loc(style_col)+1+len(months)]
    df_months.columns = month_cols

    plm_df = pd.concat([df[[style_col]].reset_index(drop=True), df_months.reset_index(drop=True)], axis=1)
    plm_df = plm_df.rename(columns={style_col: "Style number"})

    # Ensure month columns are numeric
    for col in month_cols:
        plm_df[col] = pd.to_numeric(plm_df[col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

    return plm_df

def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU PLM Download → MCU format
    """
    df.columns = df.columns.str.strip()

    # Drop 'Sum of' columns
    keep_cols = [c for c in df.columns if not c.lower().startswith("sum of")]
    df = df[keep_cols].copy()

    # Ensure month columns are numeric
    month_cols = [c for c in df.columns if c[:3].capitalize() in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]]
    for col in month_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# -------------------- Streamlit UI --------------------
def render():
    st.header("Tommy EU — Buy Sheet → PLM Upload")
    buy_file = st.file_uploader("Upload Tommy EU Buy Sheet", type=["xlsx","xls"], key="tommy_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file, header=None)
            df_out = buy_to_plm(df)
            st.subheader("Preview — PLM Upload")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download PLM Upload", out_bytes, file_name="PLM_Upload_TommyEU.xlsx")
        except Exception as e:
            st.error(f"❌ Error processing Buy Sheet: {e}")

    st.markdown("---")
    st.header("Tommy EU — PLM Download → MCU")
    plm_file = st.file_uploader("Upload PLM Download file", type=["xlsx","xls"], key="tommy_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download MCU", out_bytes, file_name="MCU_TommyEU.xlsx")
        except Exception as e:
            st.error(f"❌ Error processing PLM Download: {e}")
