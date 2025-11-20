import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# Brand name for sidebar
name = "M&S - Bucket 03"

# Base required PLM columns
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

# -------------------------------------------------------
#   TRANSFORMATION: PLM Download  →  MCU Format
# -------------------------------------------------------
def transform_plm_to_mcu(df):
    """Transforms PLM Download → MCU format for M&S."""

    # Clean header names
    df.columns = df.columns.str.strip()

    # Remove SUM columns
    df = df[[c for c in df.columns if not c.lower().startswith("sum")]]

    # Detect month columns dynamically (columns containing "-")
    month_cols = [c for c in df.columns if "-" in c]

    # Validate missing columns
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required PLM columns: {missing}")

    # Extract required columns + months
    df_out = df[
        ["Season", "Style", "BOM", "Cycle", "Article", "Type of Const 1",
         "Supplier", "UOM", "Composition", "Measurement",
         "Supplier Country", "Avg YY"] + month_cols
    ]

    # Insert sheet name as first column
    df_out.insert(0, "Sheet Names", "Fabrics")

    # Fill missing month values with 0
    df_out[month_cols] = df_out[month_cols].fillna(0)

    return df_out


# -------------------------------------------------------
#                  STREAMLIT UI
# -------------------------------------------------------
def render():
    st.header("M&S — PLM Download → MCU Format")

    uploaded_file = st.file_uploader(
        "Upload M&S PLM Download File", 
        type=["xlsx", "xls"], 
        key="ms_plm"
    )

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)

            # Transform file
            df_final = transform_plm_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(df_final.head())

            output = excel_to_bytes(df_final)

            st.download_button(
                "📥 Download MCU Format",
                output,
                file_name="MCU_M&S.xlsx"
            )

        except Exception as e:
            st.error(f"❌ Error processing PLM Download file: {e}")
