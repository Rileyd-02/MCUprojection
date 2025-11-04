import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import timedelta

name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name="Sheet1"):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
    out.seek(0)
    return out

def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.map(str).str.strip()

    # --- Detect Supplier columns ---
    supplier_col = next((c for c in df.columns if "supplier" in c.lower()), None)
    country_col  = next((c for c in df.columns if "country" in c.lower()), None)
    if not supplier_col or not country_col:
        raise ValueError("Missing Supplier or Country column")

    # --- Detect month columns (datetime or parseable) ---
    non_months = [
        supplier_col, country_col, "Brand", "Division", "Global Collection",
        "Global Style", "MFG Count", "MAS Prod Category", "Country", "Region",
        "Reciept Type", "Speed Model", "U Product Line", "Description",
        "Season", "Style", "BOM", "Cycle", "Article", "UOM",
        "Composition", "Type of Const 1", "Avg YY"
    ]
    month_cols = [c for c in df.columns if c not in non_months]
    # Try converting to datetime if they’re strings
    month_dt = []
    for c in month_cols:
        try:
            month_dt.append(pd.to_datetime(c))
        except Exception:
            month_dt.append(None)
    valid = [c for c, d in zip(month_cols, month_dt) if d is not None]
    if not valid:
        raise ValueError("No valid month columns detected")

    # --- Melt month data ---
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in valid],
        value_vars=valid,
        var_name="OriginalMonth",
        value_name="Qty"
    )

    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)
    melted["OriginalMonth_dt"] = pd.to_datetime(melted["OriginalMonth"], errors="coerce")

    # --- Apply lead-time adjustment ---
    def adjust_date(row):
        if pd.isna(row["OriginalMonth_dt"]):
            return pd.NaT
        country = str(row[country_col]).strip().lower()
        delta = timedelta(days=93 if "sri" in country else 120)
        return row["OriginalMonth_dt"] - delta

    melted["AdjustedDate"] = melted.apply(adjust_date, axis=1)
    melted["AdjustedMonth"] = (
        melted["AdjustedDate"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # --- Group quantities into new month buckets ---
    grouped = (
        melted.groupby(
            [c for c in df.columns if c not in valid] + ["AdjustedMonth"],
            dropna=False, as_index=False
        )["Qty"].sum()
    )
    if grouped.empty:
        raise ValueError("No rows after adjustment (check Qty values).")

    pivoted = grouped.pivot_table(
        index=[c for c in df.columns if c not in valid],
        columns="AdjustedMonth",
        values="Qty",
        fill_value=0,
        aggfunc="sum"
    ).reset_index()

    # Sort months chronologically
    month_order = sorted([c for c in pivoted.columns if isinstance(c, pd.Timestamp)])
    pivoted = pivoted[[c for c in pivoted.columns if c not in month_order] + month_order]

    # Clean column headers
    pivoted.columns = [c.strftime("%b-%y") if isinstance(c, pd.Timestamp) else str(c) for c in pivoted.columns]
    return pivoted

def render():
    st.header("NDC — Lead Time Adjustment Tool")

    uploaded = st.file_uploader("Upload NDC MCU File", type=["xlsx", "xls"], key="ndc_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed = transform_ndc(df)
            st.subheader("✅ Lead Time Adjusted Output")
            st.dataframe(transformed.head())

            out = excel_to_bytes(transformed, "Leadtime_Adjusted")
            st.download_button(
                "📥 Download Adjusted MCU File",
                data=out,
                file_name="NDC_Leadtime_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
