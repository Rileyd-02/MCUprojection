import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# Brand name for sidebar
name = "TH Apparel"

# Required base columns (always kept)
REQUIRED_COLS = [
    "Season",
    "Style",
    "BOM",
    "Cycle",
    "Article",
    "Type of Const 1",
    "Supplier",
    "UOM",
    "Composition",
    "Measurement",
    "Supplier Country",
    "Avg YY",
]

def transform_plm_to_mcu(df):
    """Transforms PLM Download → Final MCU format for TH Apparel."""

    df.columns = df.columns.str.strip()

    # Remove columns starting with "Sum"
    df = df[[c for c in df.columns if not c.lower().startswith("sum")]]

    # Identify all month columns dynamically (e.g., "Nov-25", "Dec-25", etc.)
    month_cols = [c for c in df.columns if "-" in c]

    # Ensure base columns exist
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Select only needed columns
    df_final = df[["Season", "Style", "BOM", "Cycle", "Article",
                   "Type of Const 1", "Supplier", "UOM",
                   "Composition", "Measurement",
                   "Supplier Country", "Avg YY"] + month_cols]

    # Add Sheet Name column
    df_final.insert(0, "Sheet Names", "Fabrics")

    # Fill missing month values with zeros
    df_final[month_cols] = df_final[month_cols].fillna(0)

    return df_final


# ----------------------
# STREAMLIT UI
# ----------------------
def render():
    st.header("TH Apparel — PLM Download → MCU Format")

    plm_file = st.file_uploader("Upload PLM Download File (Excel)", type=["xlsx", "xls"], key="th_plm")

    if plm_file:
        try:
            df = pd.read_excel(plm_file)
            df_out = transform_plm_to_mcu(df)

            st.subheader("Preview — MCU Output")
            st.dataframe(df_out.head())

            output = excel_to_bytes(df_out)
            st.download_button("📥 Download MCU Format", output, file_name="MCU_TH_Apparel.xlsx")

        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
