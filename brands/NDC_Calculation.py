import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import timedelta

# Display name in sidebar
name = "NDC Calculation"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def detect_month_columns(df: pd.DataFrame):
    """Detect columns that look like Month-Year (e.g. 'Nov-25', 'December-25')."""
    months = []
    for c in df.columns:
        if any(m in c.lower() for m in [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ]):
            months.append(c)
    return months

def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    # Clean column names
    df = df.copy()
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")

    # Detect Supplier columns
    supplier_col = next((c for c in df.columns if "supplier" == c.lower().strip()), None)
    supplier_country_col = next((c for c in df.columns if "supplier country" in c.lower()), None)

    if not supplier_col or not supplier_country_col:
        raise ValueError("Could not find 'Supplier' or 'Supplier Country' columns.")

    # Detect month columns dynamically
    month_cols = detect_month_columns(df)
    if not month_cols:
        raise ValueError("No month columns found (e.g., 'Nov-25', 'Dec-25').")

    # Melt month columns into rows
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in month_cols],
        value_vars=month_cols,
        var_name="OriginalMonth",
        value_name="Qty"
    )

    # Convert OriginalMonth → datetime
    melted["OriginalMonth_dt"] = pd.to_datetime(
        melted["OriginalMonth"].str.strip(), format="%b-%y", errors="coerce"
    )
    melted = melted.dropna(subset=["OriginalMonth_dt"])

    # Adjust EX-mill dates
    def adjust_date(row):
        country = str(row[supplier_country_col]).strip().lower()
        if "sri lanka" in country or "sl" in country:
            return row["OriginalMonth_dt"] - timedelta(days=93)
        else:
            return row["OriginalMonth_dt"] - timedelta(days=120)

    melted["AdjustedMonth_dt"] = melted.apply(adjust_date, axis=1)
    melted["AdjustedMonth"] = melted["AdjustedMonth_dt"].dt.strftime("%b-%y")

    # Group by adjusted month
    meta_cols = [c for c in df.columns if c not in month_cols]
    grouped = melted.groupby(meta_cols + ["AdjustedMonth"], as_index=False)["Qty"].sum()

    # Pivot back to MCU format
    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="AdjustedMonth",
        values="Qty",
        fill_value=0,
        aggfunc="sum"
    ).reset_index()

    # Sort month columns chronologically
    month_cols_new = [c for c in pivot_df.columns if c not in meta_cols]
    parsed = pd.to_datetime(month_cols_new, format="%b-%y", errors="coerce")
    sorted_cols = [m for _, m in sorted(zip(parsed, month_cols_new))]
    pivot_df = pivot_df[meta_cols + sorted_cols]

    pivot_df.columns = [str(c) for c in pivot_df.columns]
    return pivot_df


def render():
    st.header("NDC — Lead Time Adjusted MCU Transformer")

    uploaded = st.file_uploader("Upload MCU File", type=["xlsx", "xls", "csv"], key="ndc_file")

    if uploaded:
        try:
            if uploaded.name.endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_ndc(df)

            st.subheader("✅ Transformed Output (Lead-Time Adjusted)")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU_Adjusted")
            st.download_button(
                label="📥 Download NDC adjusted MCU.xlsx",
                data=out_bytes,
                file_name="NDC_MCU_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing NDC file: {e}")
