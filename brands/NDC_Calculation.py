import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import timedelta

# Display name on sidebar
name = "NDC"

# -------------------------------
# Helper: Write Excel output
# -------------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Leadtime Adjusted"):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    out.seek(0)
    return out


# -------------------------------
# Transformation Logic
# -------------------------------
def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adjust ex-mill months by lead time based on Supplier Country.
    Local (Sri Lanka) = minus 3 months (≈93 days)
    Foreign = minus 4 months (≈120 days)
    """

    df = df.copy()
    df.columns = df.columns.str.strip().str.replace("\n", " ")

    # --- Hardcode key column names (for reliability) ---
    supplier_col = "Supplier"
    country_col = "Supplier Country"

    # Ensure these columns exist
    if supplier_col not in df.columns or country_col not in df.columns:
        raise ValueError("Missing required columns 'Supplier' or 'Supplier Country'.")

    # --- Detect month columns dynamically ---
    month_cols = []
    for c in df.columns:
        c_str = str(c).strip()
        # Detect names like "November-25"
        if any(m in c_str.lower() for m in [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ]):
            month_cols.append(c)
        else:
            # Detect datetime-like names like "2025-11-01 00:00:00"
            try:
                pd.to_datetime(c_str)
                month_cols.append(c)
            except Exception:
                continue

    if not month_cols:
        st.error("❌ No valid month columns found. Check headers — must look like 'November-25' or '2025-11-01'.")
        return pd.DataFrame()

    st.info(f"🗓 Detected month columns: {month_cols}")

    # --- Melt to long format ---
    id_columns = [c for c in df.columns if c not in month_cols]
    melted = df.melt(id_vars=id_columns, value_vars=month_cols,
                     var_name="Month", value_name="Qty")

    # Drop rows with no quantity
    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)
    melted = melted[melted["Qty"] > 0]

    if melted.empty:
        st.warning("⚠️ No valid quantity data found after melting. Please check the file content.")
        return pd.DataFrame()

    # --- Normalize month column to datetime ---
    def parse_month(m):
        try:
            return pd.to_datetime(m, errors="coerce")
        except Exception:
            return pd.to_datetime("1900-01-01")

    melted["MonthDate"] = melted["Month"].apply(parse_month)

    # --- Apply lead time offset ---
    def adjust_date(row):
        country = str(row[country_col]).strip().lower()
        if "sri lanka" in country or "stretchline" in str(row[supplier_col]).lower():
            return row["MonthDate"] - timedelta(days=93)
        else:
            return row["MonthDate"] - timedelta(days=120)

    melted["AdjustedDate"] = melted.apply(adjust_date, axis=1)
    melted["AdjustedMonth"] = melted["AdjustedDate"].dt.strftime("%B-%y")

    # --- Group adjusted results ---
    grouped = (
        melted.groupby(id_columns + ["AdjustedMonth"], dropna=False, as_index=False)["Qty"]
        .sum()
    )

    if grouped.empty:
        st.warning("⚠️ Grouping resulted in empty dataframe — no quantities found after adjustments.")
        return pd.DataFrame()

    # --- Pivot back to wide format ---
    pivot_df = grouped.pivot_table(
        index=id_columns,
        columns="AdjustedMonth",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # --- Ensure all expected month columns exist (avoid empty results) ---
    adjusted_months = sorted(list(set(melted["AdjustedMonth"].dropna())))
    for m in adjusted_months:
        if m not in pivot_df.columns:
            pivot_df[m] = 0

    # Sort month columns by chronological order
    month_order = sorted(
        [m for m in pivot_df.columns if m not in id_columns],
        key=lambda x: pd.to_datetime(x, format="%B-%y", errors="coerce")
    )
    pivot_df = pivot_df[id_columns + month_order]

    return pivot_df


# -------------------------------
# Streamlit Page
# -------------------------------
def render():
    st.header("NDC — Lead Time Adjustment")

    uploaded = st.file_uploader(
        "📤 Upload MCU Format File",
        type=["xlsx", "xls"],
        key="ndc_file"
    )

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            result_df = transform_ndc(df)

            if result_df.empty:
                st.warning("⚠️ Result is empty after transformation. Check Supplier/Country columns and month headers.")
                return

            st.subheader("✅ Lead Time Adjusted Output")
            st.dataframe(result_df.head())

            out_bytes = excel_to_bytes(result_df)
            st.download_button(
                label="📥 Download Adjusted MCU File",
                data=out_bytes,
                file_name="NDC_Leadtime_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(f"❌ Error processing NDC file: {e}")
