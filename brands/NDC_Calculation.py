import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta

# Display name in sidebar
name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    """Convert DataFrame to Excel bytes for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    NDC transformation:
    - Detects month columns (like 'November-25', 'December-25')
    - Adjusts quantities backward by 3 months (local) or 4 months (foreign)
    based on Supplier Country
    """

    df = df.copy()

    # Normalize column names
    df.columns = df.columns.str.strip()

    # Identify key columns
    supplier_col = "Supplier"
    country_col = "Supplier Country"

    if supplier_col not in df.columns or country_col not in df.columns:
        raise ValueError("Required columns 'Supplier' or 'Supplier Country' not found.")

    # Detect month columns like "November-25"
    month_cols = [
        c for c in df.columns if "-" in c and any(m in c for m in [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
            "Aug", "Sep", "Oct", "Nov", "Dec"
        ])
    ]

    if not month_cols:
        raise ValueError("No valid month columns detected.")

    st.info(f"🗓 Detected month columns: {month_cols}")

    # Create a working copy of numeric data
    df_months = df[month_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Parse month columns to datetime for shifting
    month_dt = pd.to_datetime(month_cols, format="%B-%y", errors="coerce")

    # Prepare a mapping of column -> adjusted month
    adjusted_data = pd.DataFrame(0, index=df.index, columns=month_cols)

    for i, row in df.iterrows():
        supplier_country = str(row[country_col]).strip().lower()
        months_back = 3 if "sri lanka" in supplier_country else 4

        for j, col in enumerate(month_cols):
            qty = df_months.at[i, col]
            if qty == 0:
                continue

            # Compute adjusted date
            old_date = month_dt[j]
            new_date = old_date - relativedelta(months=months_back)
            new_month_label = new_date.strftime("%B-%y")

            # If adjusted month exists in columns, accumulate qty there
            if new_month_label in adjusted_data.columns:
                adjusted_data.at[i, new_month_label] += qty

    # Merge adjusted month data back
    df_result = df.copy()
    df_result[month_cols] = adjusted_data[month_cols]

    # Drop rows where all month values are 0
    if df_result[month_cols].sum(axis=1).eq(0).all():
        st.warning("⚠️ Result is empty after transformation. Check Supplier/Country columns and month headers.")
        return pd.DataFrame()

    return df_result


# Streamlit Page
def render():
    st.header("🧾 NDC — Lead Time Adjustment")

    uploaded = st.file_uploader("Upload NDC MCU File", type=["xlsx", "xls", "csv"], key="ndc_file")

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            result = transform_ndc(df)

            if result.empty:
                st.warning("⚠️ No valid data after transformation.")
                return

            st.subheader("✅ Adjusted Output")
            st.dataframe(result.head())

            # Download link
            out_bytes = excel_to_bytes(result, sheet_name="Leadtime_Adjusted")

            st.download_button(
                label="📥 Download Leadtime Adjusted File",
                data=out_bytes,
                file_name="NDC_Leadtime_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing NDC file: {e}")
