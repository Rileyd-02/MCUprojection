import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta

name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    """Convert DataFrame to downloadable Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    NDC Transformation — back-calculates months for local/foreign suppliers.
    - Local suppliers (Sri Lanka): shift months -3
    - Foreign suppliers: shift months -4
    """

    df = df.copy()
    df.columns = df.columns.str.strip()

    supplier_col = "Supplier"
    country_col = "Supplier Country"

    if supplier_col not in df.columns or country_col not in df.columns:
        raise ValueError("❌ Missing 'Supplier' or 'Supplier Country' columns in file.")

    # Detect month columns like "November-25"
    month_cols = [
        c for c in df.columns if "-" in c and any(m in c for m in [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ])
    ]
    if not month_cols:
        raise ValueError("❌ No valid month columns detected (e.g., 'November-25').")

    st.info(f"🗓 Detected month columns: {month_cols}")

    # Parse month headers into datetime objects
    month_dates = pd.to_datetime(month_cols, format="%B-%y", errors="coerce")

    # Check the supplier country for each row
    first_country = str(df[country_col].iloc[0]).lower()
    months_back = 3 if "sri lanka" in first_country else 4

    st.write(f"⏳ Detected supplier country: **{first_country.title()}**, shifting months by **-{months_back} months**")

    # Create adjusted month column names
    adjusted_months = [
        (d - relativedelta(months=months_back)).strftime("%B-%y") if pd.notnull(d) else c
        for c, d in zip(month_cols, month_dates)
    ]

    # Rename columns
    rename_map = dict(zip(month_cols, adjusted_months))
    df = df.rename(columns=rename_map)

    st.success("✅ Month headers successfully back-calculated.")

    return df


def render():
    st.header("🧾 NDC — Month Back Calculation Tool")

    uploaded = st.file_uploader("Upload NDC MCU File", type=["xlsx", "xls", "csv"], key="ndc_file")

    if uploaded:
        try:
            # Load file
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded, header=0)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            # Transform
            transformed = transform_ndc(df)

            st.subheader("✅ Transformed Output (Months Adjusted)")
            st.dataframe(transformed.head())

            # Download output
            out_bytes = excel_to_bytes(transformed, sheet_name="NDC_Adjusted")

            st.download_button(
                label="📥 Download Adjusted NDC File",
                data=out_bytes,
                file_name="NDC_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
