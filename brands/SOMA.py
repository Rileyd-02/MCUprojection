# brands/soma.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "SOMA"

def plm_to_mcu_all_sheets(file) -> pd.DataFrame:
    """Read all sheets and transform into MCU format."""
    all_sheets = pd.read_excel(file, sheet_name=None)  # read all sheets
    mcu_list = []

    for sheet_name, df in all_sheets.items():
        df = df.copy()

        # Strip column names to remove hidden spaces
        df.columns = df.columns.str.strip()

        # All metadata columns we care about
        desired_cols = [
            'Season','Style','BOM','Cycle','Article','Type of Const 1','Supplier',
            'UOM','Composition','Measurement','Supplier Country','Avg YY'
        ]

        # Keep only columns that exist in the dataframe
        keep_cols = [c for c in desired_cols if c in df.columns]

        # Dynamically detect month columns: columns containing '-' and not starting with 'Sum'
        month_cols = [c for c in df.columns if '-' in c and not c.lower().startswith('sum')]

        # Select relevant columns
        df_mcu = df[keep_cols + month_cols]

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
