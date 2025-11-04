import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta
from datetime import datetime

name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Leadtime_Adjusted"):
    """Convert dataframe to downloadable Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def shift_month_str(month_str: str, offset: int) -> str:
    """
    Shift month string (like 'November-25') backward by offset months (3 or 4)
    and return a new formatted string (e.g. 'August-25').
    """
    try:
        dt = datetime.strptime(month_str, "%B-%y")  # e.g. November-25
        new_dt = dt - relativedelta(months=offset)
        return new_dt.strftime("%B-%y")
    except Exception:
        return None


def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adjust MCU months backward by 3 (local) or 4 (foreign) months based on supplier country.
    """
    df = df.copy()
    df.columns = df.columns.str.strip()  # remove trailing spaces

    # Detect supplier and country columns dynamically
    supplier_col = next((c for c in df.columns if "supplier" in c.lower() and "country" not in c.lower()), None)
    country_col = next((c for c in df.columns if "country" in c.lower()), None)

    if not supplier_col or not country_col:
        raise ValueError("Could not detect 'Supplier' or 'Supplier Country' columns. Check column headers.")

    # Detect month columns (with e.g., November-25, December-25, etc.)
    month_cols = [
        c for c in df.columns
        if "-" in c and any(m in c.lower() for m in [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ])
    ]

    if not month_cols:
        raise ValueError("No month columns found (e.g., 'November-25', 'December-25').")

    # Melt to long format
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in month_cols],
        value_vars=month_cols,
        var_name="OriginalMonth",
        value_name="Qty"
    )

    # Drop rows without quantities
    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)
    melted = melted[melted["Qty"] > 0]

    # Determine adjusted month for each row
    def get_adjusted_month(row):
        country = str(row[country_col]).lower()
        original = str(row["OriginalMonth"]).strip()
        if not original:
            return None
        offset = 3 if ("sri" in country or "lanka" in country) else 4
        return shift_month_str(original, offset)

    melted["AdjustedMonth"] = melted.apply(get_adjusted_month, axis=1)
    melted = melted.dropna(subset=["AdjustedMonth"])

    if melted.empty:
        st.warning("⚠️ No valid quantities found after lead time adjustment.")
        return pd.DataFrame()

    # Aggregate totals
    grouped = (
        melted.groupby([c for c in df.columns if c not in month_cols] + ["AdjustedMonth"], as_index=False)["Qty"]
        .sum()
    )

    # Pivot back to wide format
    pivot_df = grouped.pivot_table(
        index=[c for c in df.columns if c not in month_cols],
        columns="AdjustedMonth",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Reorder columns — non-month columns first, then all month columns chronologically
    month_strs = sorted(
        list(pivot_df.columns.difference(df.columns, sort=False)),
        key=lambda x: datetime.strptime(x, "%B-%y")
    )

    final_df = pivot_df[[c for c in df.columns if c not in month_cols] + month_strs]

    return final_df


def render():
    st.header("NDC — Leadtime Adjustment Tool")

    uploaded = st.file_uploader("Upload NDC MCU File", type=["xlsx", "xls"], key="ndc_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            result = transform_ndc(df)

            if result.empty:
                st.warning("⚠️ Result is empty after transformation. Check Supplier/Country columns and month headers.")
                return

            st.subheader("✅ Leadtime Adjusted Output")
            st.dataframe(result.head())

            # Allow download
            out_bytes = excel_to_bytes(result)
            st.download_button(
                label="📥 Download Leadtime Adjusted MCU File",
                data=out_bytes,
                file_name="Leadtime_Adjusted_NDC.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing NDC file: {e}")
