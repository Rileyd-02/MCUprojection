# brands/la_senza.py
import streamlit as st
import pandas as pd
from utils import excel_to_bytes

name = "La Senza - Bucket 02"

# -----------------------------
# 1. BUY SHEET -> PLM UPLOAD
# -----------------------------
def buy_sheet_to_plm_upload(file) -> pd.DataFrame:
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()

    # Identify month columns dynamically (e.g., OCT, NOV, etc.)
    month_cols = [c for c in df.columns if c.strip().isalpha() and len(c.strip()) == 3]

    if not month_cols:
        raise ValueError("No month columns detected in Buy Sheet.")

    # Required columns
    if "Product Number" not in df.columns:
        raise ValueError("'Product Number' column missing in Buy Sheet.")

    # Build final PLM upload format
    plm = pd.DataFrame()
    plm["Style Number"] = df["Product Number"].astype(str)

    for m in month_cols:
        plm[m] = df[m]

    return plm

# -----------------------------
# 2. PLM DOWNLOAD -> MCU FORMAT (same logic as SOMA)
# -----------------------------
def plm_to_mcu(file) -> pd.DataFrame:
    all_sheets = pd.read_excel(file, sheet_name=None)
    mcu_list = []
    all_months_set = set()

    # First pass: find all month columns
    for sheet_name, df in all_sheets.items():
        df = df.copy()
        df.columns = df.columns.str.strip()
        month_cols = [c for c in df.columns if '-' in c and not c.lower().startswith('sum')]
        all_months_set.update(month_cols)

    # Sort months chronologically
    parsed = pd.to_datetime(list(all_months_set), format="%b-%y", errors="coerce")
    sorted_months = [c for _, c in sorted(zip(parsed, all_months_set)) if not pd.isna(_)]

    # Metadata expected in PLM
    meta_cols = [
        'Season','Style','BOM','Cycle','Article','Type of Const 1','Supplier',
        'UOM','Composition','Measurement','Supplier Country','Avg YY'
    ]

    # Second pass: build MCU
    for sheet_name, df in all_sheets.items():
        df = df.copy()
        df.columns = df.columns.str.strip()

        keep_meta = [c for c in meta_cols if c in df.columns]
        month_cols = [c for c in df.columns if '-' in c and not c.lower().startswith('sum')]

        out = df[keep_meta + month_cols]

        # Add missing month columns
        for m in sorted_months:
            if m not in out.columns:
                out[m] = 0

        # Reorder
        out = out[keep_meta + sorted_months]

        # Add Sheet Name
        out.insert(0, "Sheet Names", "Fabrics")

        mcu_list.append(out)

    final_mcu = pd.concat(mcu_list, ignore_index=True)
    return final_mcu

# -----------------------------
# STREAMLIT UI
# -----------------------------
def render():
    st.header("La Senza — Buy Sheet → PLM Upload & PLM Download → MCU")

    ## ---- BUY SHEET ----
    st.subheader("1️⃣ Buy Sheet → PLM Upload")
    buy_file = st.file_uploader("Upload La Senza Buy Sheet", type=["xlsx","xls"], key="ls_buy")

    if buy_file:
        try:
            df_buy = buy_sheet_to_plm_upload(buy_file)
            st.write("Preview — PLM Upload Format")
            st.dataframe(df_buy.head())
            st.download_button(
                "📥 Download PLM Upload",
                excel_to_bytes(df_buy),
                file_name="LaSenza_PLM_Upload.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing Buy Sheet: {e}")

    ## ---- PLM DOWNLOAD ----
    st.subheader("2️⃣ PLM Download → MCU")
    plm_file = st.file_uploader("Upload La Senza PLM Download", type=["xlsx","xls"], key="ls_plm")

    if plm_file:
        try:
            df_mcu = plm_to_mcu(plm_file)
            st.write("Preview — MCU Format")
            st.dataframe(df_mcu.head())
            st.download_button(
                "📥 Download MCU Format",
                excel_to_bytes(df_mcu),
                file_name="LaSenza_MCU.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:

            st.error(f"❌ Error processing PLM Download file: {e}")
