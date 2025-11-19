import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="DBI – PLM to MCU", page_icon="📄")

st.title("📄 DBI – PLM Download to MCU Format Converter")


# --------------------------------------------------------
# FUNCTION: TRANSFORM PLM → MCU FORMAT
# --------------------------------------------------------
def transform_plm_to_mcu(df):

    # 1. REMOVE COLUMNS STARTING WITH "SUM"
    df = df.loc[:, ~df.columns.str.lower().str.startswith("sum")]

    # 2. DYNAMICALLY DETECT MONTH COLUMNS USING REGEX  
    month_pattern = r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-_ ]?\d{0,4}$"
    month_cols = [c for c in df.columns if re.match(month_pattern, c.lower())]

    # 3. NORMALIZE MONTH NAMES (jan24 → Jan, jan_2024 → Jan)
    clean_months = {}
    for col in month_cols:
        c = col.lower().replace("-", "").replace("_", "")
        month = c[:3].title()  # Jan, Feb, Mar...
        clean_months[col] = month

    df = df.rename(columns=clean_months)

    # 4. MASTER MCU MONTH LIST
    all_months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]

    # 5. ADD MISSING MONTHS WITH 0
    for m in all_months:
        if m not in df.columns:
            df[m] = 0

    # 6. REORDER COLUMNS (KEEP ALL NON-MONTH COLUMNS FIRST)
    fixed_cols = [c for c in df.columns if c not in all_months]
    df = df[fixed_cols + all_months]

    return df


# --------------------------------------------------------
# FILE UPLOAD SECTION
# --------------------------------------------------------
uploaded_file = st.file_uploader("Upload DBI PLM Download File", type=["xlsx", "xls"])


# --------------------------------------------------------
# PROCESS FILE
# --------------------------------------------------------
if uploaded_file is not None:
    try:
        df_plm = pd.read_excel(uploaded_file)

        st.subheader("📥 Raw PLM Download Preview")
        st.dataframe(df_plm.head())

        # APPLY TRANSFORMATION
        df_mcu = transform_plm_to_mcu(df_plm)

        st.subheader("📤 Transformed MCU Format")
        st.dataframe(df_mcu)

        # DOWNLOAD BUTTON
        output_file = "DBI_MCU_Format.xlsx"
        df_mcu.to_excel(output_file, index=False)

        with open(output_file, "rb") as f:
            st.download_button(
                label="⬇ Download MCU Format (Excel)",
                data=f,
                file_name=output_file,
                mime="application/octet-stream"
            )

        st.success("✔ DBI MCU File Successfully Generated!")

    except Exception as e:
        st.error(f"❌ Error processing DBI PLM file: {e}")
