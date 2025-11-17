# brands/tommy_eu.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "Tommy EU"

# ---------- Helper function to convert DataFrame to Excel bytes ----------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# ---------- Transformation 1: Buy Sheet → PLM Upload ----------
def buy_to_plm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU Buy Sheet → PLM Upload format
    - Row 0: month headers (Buy month: Jul, Aug, etc.)
    - Row 1: PO Proposal (skip)
    - Row 2: actual column names
    """
    # Ensure all values are string
    df = df.astype(str)

    # Capture months from row 0 (ignore first column "Buy month:")
    months_row = df.iloc[0, 1:].tolist()
    
    # Drop first two rows (row0=months, row1=PO Proposal)
    df = df.drop([0, 1]).reset_index(drop=True)

    # Set third row (row2) as header
    new_header = df.iloc[0].astype(str).str.strip()
    df = df[1:].copy()
    df.columns = new_header
    df = df.reset_index(drop=True)

    # Identify style column
    style_col = "Generic Article"
    if style_col not in df.columns:
        style_col = df.columns[0]

    # Month columns: Use months_row
    plm_months = [m for m in months_row if m.strip() != ""]
    # Keep only style + month columns
    plm_df = df[[style_col] + list(plm_months)].copy()
    plm_df = plm_df.rename(columns={style_col: "Style number"})

    # Convert month columns to numeric
    for col in plm_months:
        plm_df[col] = pd.to_numeric(plm_df[col].str.replace(",", ""), errors="coerce").fillna(0)

    return plm_df

# ---------- Transformation 2: PLM Download → MCU ----------
def plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tommy EU PLM Download → MCU Format
    - Removes any 'Sum of' duplicate columns
    - Keeps month columns for MCU
    """
    df.columns = df.columns.str.strip()
    # Drop duplicate 'Sum of' columns if present
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]
    return df

# ---------- Streamlit UI ----------
def render():
    st.header("Tommy EU — Buy Sheet → PLM Upload")
    buy_file = st.file_uploader("Upload Tommy EU Buy Sheet", type=["xlsx", "xls"], key="tommy_buy")
    if buy_file:
        try:
            df = pd.read_excel(buy_file, header=None)  # read all rows as-is
            plm_df = buy_to_plm(df)
            st.subheader("Preview — PLM Upload")
            st.dataframe(plm_df.head())
            out_bytes = excel_to_bytes(plm_df)
            st.download_button(
                "📥 Download PLM Upload",
                out_bytes,
                file_name="PLM_Upload_Tommy_EU.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing Buy Sheet: {e}")

    st.markdown("---")
    st.header("Tommy EU — PLM Download → MCU")
    plm_file = st.file_uploader("Upload Tommy EU PLM Download", type=["xlsx", "xls"], key="tommy_plm")
    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            mcu_df = plm_to_mcu(df)
            st.subheader("Preview — MCU Format")
            st.dataframe(mcu_df.head())
            out_bytes = excel_to_bytes(mcu_df)
            st.download_button(
                "📥 Download MCU",
                out_bytes,
                file_name="MCU_Tommy_EU.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing PLM Download: {e}")
