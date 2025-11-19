# brands/soma.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "SOMA - Bucket 02"

def plm_to_mcu_all_sheets(file) -> pd.DataFrame:
    """Read all sheets and transform into MCU format with all months filled."""
    all_sheets = pd.read_excel(file, sheet_name=None)  # read all sheets
    mcu_list = []
    all_months_set = set()

    # First pass: collect all month columns across all sheets
    for sheet_name, df in all_sheets.items():
        df = df.copy()
        df.columns = df.columns.str.strip()
        month_cols = [c for c in df.columns if '-' in c and not c.lower().startswith('sum')]
        all_months_set.update(month_cols)

    # Sort all months chronologically
    parsed_months = pd.to_datetime(list(all_months_set), format="%b-%y", errors="coerce")
    all_months_sorted = [c for _, c in sorted(zip(parsed_months, all_months_set)) if not pd.isna(_)]

    # Second pass: process sheets and align month columns
    for sheet_name, df in all_sheets.items():
        df = df.copy()
        df.columns = df.columns.str.strip()

        # Metadata columns
        desired_cols = [
            'Season','Style','BOM','Cycle','Article','Type of Const 1','Supplier',
            'UOM','Composition','Measurement','Supplier Country','Avg YY'
        ]
        keep_cols = [c for c in desired_cols if c in df.columns]

        # Month columns in this sheet
        month_cols = [c for c in df.columns if '-' in c and not c.lower().startswith('sum')]

        # Keep metadata + month columns
        df_mcu = df[keep_cols + month_cols]

        # Add missing month columns with 0
        for m in all_months_sorted:
            if m not in df_mcu.columns:
                df_mcu[m] = 0

        # Reorder columns: metadata first, then months
        df_mcu = df_mcu[keep_cols + all_months_sorted]

        # Add 'Sheet Names' column at the front
        df_mcu.insert(0, 'Sheet Names', 'Fabrics')

        mcu_list.append(df_mcu)

    # Concatenate all sheets
    final_df = pd.concat(mcu_list, ignore_index=True)
    return final_df

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("SOMA — PLM Download → MCU")
    plm_file = st.file_uploader("Upload PLM Download file (SOMA)", type=["xlsx","xls"], key="soma_plm")
    if plm_file:
        try:
            df_out = plm_to_mcu_all_sheets(plm_file)
            if df_out.empty:
                st.warning("⚠️ No valid rows found in the PLM Download file.")
                return
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

