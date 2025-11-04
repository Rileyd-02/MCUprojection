import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta

name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shift month quantities back 3 months (local) or 4 months (foreign).
    If shifted month doesn't exist, amount moves to earliest available month.
    """

    df = df.copy()
    df.columns = df.columns.str.strip()

    supplier_col = "Supplier"
    country_col = "Supplier Country"

    if supplier_col not in df.columns or country_col not in df.columns:
        raise ValueError("Missing 'Supplier' or 'Supplier Country' column.")

    # --- Detect month columns ---
    month_cols = [c for c in df.columns if "-" in c and any(m in c for m in [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
        "Aug", "Sep", "Oct", "Nov", "Dec"
    ])]

    if not month_cols:
        raise ValueError("No month columns detected.")

    st.info(f"🗓 Detected month columns: {month_cols}")

    # Parse month columns to datetime
    month_dt = pd.to_datetime(month_cols, format="%B-%y", errors="coerce")
    month_mapping = dict(zip(month_cols, month_dt))

    adjusted = pd.DataFrame(0, index=df.index, columns=month_cols)

    for i, row in df.iterrows():
        supplier_country = str(row[country_col]).strip().lower()
        months_back = 3 if "sri lanka" in supplier_country else 4

        for col in month_cols:
            qty = pd.to_numeric(row[col], errors="coerce")
            if pd.isna(qty) or qty == 0:
                continue

            old_date = month_mapping[col]
            new_date = old_date - relativedelta(months=months_back)
            new_label = new_date.strftime("%B-%y")

            # If shifted column exists, move qty there; otherwise use earliest column
            if new_label in adjusted.columns:
                adjusted.at[i, new_label] += qty
            else:
                adjusted.at[i, month_cols[0]] += qty

    # Merge adjusted values
    df_result = df.copy()
    df_result[month_cols] = adjusted[month_cols]

    # Clean up: drop rows with all zero months
    if df_result[month_cols].sum(axis=1).eq(0).all():
        st.warning("⚠️ All month columns zero after shifting — check date ranges.")
        return df_result

    return df_result


def render():
    st.header("📆 NDC — Lead Time Month Backshift")

    uploaded = st.file_uploader("Upload NDC MCU File", type=["xlsx", "xls", "csv"], key="ndc_file")

    if uploaded:
        try:
            df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            result = transform_ndc(df)

            st.subheader("✅ Adjusted Output")
            st.dataframe(result.head())

            out_bytes = excel_to_bytes(result, sheet_name="Adjusted")

            st.download_button(
                label="📥 Download Leadtime Adjusted NDC File",
                data=out_bytes,
                file_name="NDC_Leadtime_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
