import streamlit as st
import pandas as pd
import io
from dateutil.relativedelta import relativedelta

# ==========================================================
# 🔧 Helper: shift a month string (e.g. "November-25") by X months
# ==========================================================
def shift_month_str(month_str: str, offset: int) -> str:
    try:
        month_str = month_str.strip().replace(" ", "").replace("–", "-").replace("_", "-")
        month, year = month_str.split("-")
        year = int("20" + year) if len(year) == 2 else int(year)
        dt_date = pd.to_datetime(f"01-{month}-{year}", format="%d-%B-%Y", errors="coerce")

        if pd.isna(dt_date):
            dt_date = pd.to_datetime(f"01-{month[:3]}-{year}", format="%d-%b-%Y", errors="coerce")

        if pd.isna(dt_date):
            return None

        new_date = dt_date - relativedelta(months=offset)
        return new_date.strftime("%B-%y")
    except Exception:
        return None


# ==========================================================
# ⚙️ Core Transformation Logic
# ==========================================================
def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    # --- Detect Supplier and Country Columns ---
    supplier_col = next((c for c in df.columns if "supplier" in c.lower() and "country" not in c.lower()), None)
    country_col = next((c for c in df.columns if "country" in c.lower()), None)

    if not supplier_col or not country_col:
        st.error("❌ Could not detect 'Supplier' or 'Supplier Country' columns. Check your headers.")
        return pd.DataFrame()

    # --- Detect Month Columns ---
    month_cols = [
        c.strip() for c in df.columns
        if "-" in c and any(m in c.lower() for m in [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ])
    ]

    if not month_cols:
        st.error("❌ No valid month columns found. Expected headers like 'November-25', 'December-25', etc.")
        return pd.DataFrame()

    # --- Melt Data ---
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in month_cols],
        value_vars=month_cols,
        var_name="OriginalMonth",
        value_name="Qty"
    )

    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)
    melted = melted[melted["Qty"] > 0]

    if melted.empty:
        st.warning("⚠️ No valid quantities found.")
        return pd.DataFrame()

    # --- Apply Leadtime Logic ---
    def get_adjusted_month(row):
        country = str(row[country_col]).strip().lower()
        original = str(row["OriginalMonth"]).strip()
        if not original:
            return None
        # Local = 3 months (Sri Lanka)
        # Foreign = 4 months
        offset = 3 if ("sri" in country or "lanka" in country) else 4
        return shift_month_str(original, offset)

    melted["AdjustedMonth"] = melted.apply(get_adjusted_month, axis=1)
    melted = melted.dropna(subset=["AdjustedMonth"])

    if melted.empty:
        st.warning("⚠️ No rows found after month adjustment.")
        return pd.DataFrame()

    # --- Group by adjusted month ---
    id_columns = [c for c in df.columns if c not in month_cols]
    grouped = (
        melted.groupby(id_columns + ["AdjustedMonth"], as_index=False)["Qty"]
        .sum()
    )

    if grouped.empty:
        st.warning("⚠️ Grouping resulted in empty dataframe — check supplier/country values.")
        return pd.DataFrame()

    # --- Pivot back to wide format ---
    pivot_df = grouped.pivot_table(
        index=id_columns,
        columns="AdjustedMonth",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    if pivot_df.empty:
        st.warning("⚠️ Result is empty after transformation. Check headers or data.")
        return pd.DataFrame()

    return pivot_df


# ==========================================================
# 🧩 Streamlit Page UI
# ==========================================================
def app():
    st.title("📦 NDC Leadtime Adjustment Tool")
    st.markdown("""
    This tool adjusts MCU data by subtracting lead time from **Ex-Mill months**:
    - **Local Suppliers (Sri Lanka)** → 3 months earlier  
    - **Foreign Suppliers** → 4 months earlier
    ---
    """)

    uploaded_file = st.file_uploader("📁 Upload NDC MCU Excel File", type=["xls", "xlsx"])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("✅ File uploaded successfully.")
            st.dataframe(df.head())

            result_df = transform_ndc(df)

            if not result_df.empty:
                st.success("✅ Transformation complete.")
                st.dataframe(result_df.head())

                # Download button
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="Leadtime_Adjusted")
                output.seek(0)

                st.download_button(
                    label="💾 Download Adjusted File",
                    data=output,
                    file_name="NDC_Leadtime_Adjusted.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("⚠️ No data produced after transformation.")

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
