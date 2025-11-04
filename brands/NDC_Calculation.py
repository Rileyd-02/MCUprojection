# brands/ndc.py
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
    df = df.copy()
    df.columns = df.columns.str.strip()

    # detect month columns like "November-25", "December-25", etc.
    month_cols = [c for c in df.columns if "-" in c and any(m in c.lower() for m in [
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec"
    ])]

    if not month_cols:
        raise ValueError("No month columns detected (e.g. 'November-25', 'Dec-25').")

    # identify supplier and country columns
    supplier_col = next((c for c in df.columns if "supplier" in c.lower()), None)
    country_col = next((c for c in df.columns if "country" in c.lower()), None)

    if not supplier_col or not country_col:
        raise ValueError("Missing required columns: Supplier or Supplier Country")

    # melt the data so each row is one month’s quantity
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in month_cols],
        value_vars=month_cols,
        var_name="OriginalMonth",
        value_name="Qty"
    )

    # convert quantities
    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)

    # parse OriginalMonth safely
    melted["OriginalMonth_dt"] = pd.to_datetime(
        melted["OriginalMonth"], format="%B-%y", errors="coerce"
    )

    # if parsing fails, try full month names with year (e.g., "November-25")
    if melted["OriginalMonth_dt"].isna().all():
        melted["OriginalMonth_dt"] = pd.to_datetime(
            melted["OriginalMonth"].str.replace("-", " ", regex=False),
            format="%B %y",
            errors="coerce"
        )

    # fallback for datetimes already parsed (e.g. 2025-11-01)
    melted.loc[melted["OriginalMonth_dt"].isna(), "OriginalMonth_dt"] = pd.to_datetime(
        melted["OriginalMonth"], errors="coerce"
    )

    # adjust by supplier country
    def adjust_month(row):
        if pd.isna(row["OriginalMonth_dt"]):
            return None
        country = str(row[country_col]).strip().lower()
        if "sri" in country or "lanka" in country:
            return row["OriginalMonth_dt"] - relativedelta(months=3)
        else:
            return row["OriginalMonth_dt"] - relativedelta(months=4)

    melted["AdjustedMonth_dt"] = melted.apply(adjust_month, axis=1)
    melted["AdjustedMonth"] = melted["AdjustedMonth_dt"].dt.strftime("%B-%y")

    # group by metadata + adjusted month
    meta_cols = [c for c in df.columns if c not in month_cols]
    grouped = melted.groupby(meta_cols + ["AdjustedMonth"], as_index=False)["Qty"].sum()

    if grouped.empty:
        st.warning("⚠️ Grouping resulted in empty dataframe — no quantities found after adjustments.")
        return pd.DataFrame()

    # pivot back
    pivot = grouped.pivot_table(
        index=meta_cols,
        columns="AdjustedMonth",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # sort months chronologically
    month_order = pd.to_datetime(pivot.columns[~pivot.columns.isin(meta_cols)], format="%B-%y", errors="coerce")
    ordered_months = [m for _, m in sorted(zip(month_order, pivot.columns[~pivot.columns.isin(meta_cols)]))]
    pivot = pivot[meta_cols + ordered_months]

    return pivot

def render():
    st.header("NDC — Leadtime Adjusted MCU Converter")

    uploaded = st.file_uploader("Upload NDC MCU file", type=["xlsx", "xls", "csv"], key="ndc_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded) if uploaded.name.endswith((".xlsx", ".xls")) else pd.read_csv(uploaded)
            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_ndc(df)

            if transformed_df.empty:
                st.warning("⚠️ Result is empty after transformation. Check month headers and Supplier Country values.")
                return

            st.subheader("✅ Leadtime Adjusted Output")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="Leadtime Adjusted MCU")

            st.download_button(
                label="📥 Download Leadtime Adjusted MCU.xlsx",
                data=out_bytes,
                file_name="Leadtime_Adjusted_MCU.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing NDC file: {e}")
