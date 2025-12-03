import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------
# Brand name (Sidebar)
# ---------------------------------------
name = "NDC"


# ---------------------------------------
# Helper: DataFrame → Excel Bytes
# ---------------------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "NDC_Adjusted"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


# ---------------------------------------
# Month Transformation Logic
# ---------------------------------------
def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    NDC Transformation:
    - Detects flexible month formats (NOV, Nov, november, Nov-25, NOV_2025)
    - Local suppliers (Sri Lanka) → shift -3 months
    - Foreign suppliers → shift -4 months
    """

    df = df.copy()
    df.columns = df.columns.str.strip()

    supplier_col = "Supplier"
    country_col = "Supplier Country"

    if supplier_col not in df.columns or country_col not in df.columns:
        raise ValueError("Missing required columns: Supplier / Supplier Country")

    # -----------------------------------
    # Month dictionary
    # -----------------------------------
    MONTH_MAP = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    def parse_month(col):
        c = col.lower()

        month_match = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
            r"january|february|march|april|june|july|august|"
            r"september|october|november|december)",
            c
        )

        if not month_match:
            return None

        month_num = MONTH_MAP[month_match.group(1)]

        year_match = re.search(r"(20\d{2}|\d{2})", c)
        if year_match:
            year = int(year_match.group())
            if year < 100:
                year += 2000
        else:
            year = datetime.today().year

        return datetime(year, month_num, 1)

    # -----------------------------------
    # Detect month columns
    # -----------------------------------
    month_cols = {}
    for col in df.columns:
        dt = parse_month(col)
        if dt:
            month_cols[col] = dt

    if not month_cols:
        raise ValueError("No valid month columns detected.")

    st.info(f"🗓 Detected month columns: {list(month_cols.keys())}")

    # -----------------------------------
    # Determine shift duration
    # -----------------------------------
    first_country = str(df[country_col].iloc[0]).lower()
    months_back = 3 if "sri lanka" in first_country else 4

    st.write(
        f"⏳ Supplier Country Detected: **{first_country.title()}** "
        f"→ Shift **-{months_back} months**"
    )

    # -----------------------------------
    # Rename month columns
    # -----------------------------------
    rename_map = {}
    for col, dt in month_cols.items():
        shifted = dt - relativedelta(months=months_back)
        rename_map[col] = shifted.strftime("%B-%y")

    df = df.rename(columns=rename_map)

    st.success("✅ Month columns successfully normalized & adjusted")

    return df


# ---------------------------------------
# STREAMLIT UI
# ---------------------------------------
def render():
    st.header("🧾 NDC — Month Back Calculation Tool")

    uploaded = st.file_uploader(
        "Upload NDC MCU / PLM File",
        type=["xlsx", "xls", "csv"],
        key="ndc_file"
    )

    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed = transform_ndc(df)

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed.head())

            output = excel_to_bytes(transformed)

            st.download_button(
                "📥 Download Adjusted NDC File",
                data=output,
                file_name="NDC_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
