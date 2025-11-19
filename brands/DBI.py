import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# Brand name for sidebar
name = "DBI - Bucket 02"

# Base columns expected in the PLM download
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
    """Transforms PLM Download → Final MCU format for DBI."""

    # Clean column names
    df.columns = df.columns.str.strip()

    # Remove SUM columns
    df = df[[c for c in df.columns if not c.lower().startswith("sum")]]

    # Detect dynamic month columns (Nov-25, Dec-25, etc.)
    month_cols = [c for c in df.columns if "-" in c]

    # Validate required columns
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Keep required columns + detected months
    df_out = df[
        ["Season", "Style", "BOM", "Cycle", "Article", "Type of Const 1",
         "Supplier", "UOM", "Composition", "Measurement",
         "Supplier Country", "Avg YY"] + month_cols
    ]

    # Insert sheet name column
    df_out.insert(0, "Sheet Names", "Fabrics")

    # Fill empty month values with zero
    df_out[month_cols] = df_out[month_cols].fillna(0)

    return df_out


# --------------------
# STREAMLIT UI
# --------------------
def render():
    st.header("DBI — PLM Download → MCU Format")
    st.mrkdown("Get the initial PLM Download transformation from the shared folder")

    uploaded_file = st.file_uploader(
        "Upload DBI PLM Download File",
        type=["xlsx", "xls"],
        key="dbi_plm"
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            df_final = transform_plm_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(df_final.head())

            output = excel_to_bytes(df_final)

            st.download_button(
                "📥 Download MCU Format",
                output,
                file_name="MCU_DBI.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")


