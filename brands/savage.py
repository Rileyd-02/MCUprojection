import streamlit as st
import pandas as pd
from utils import excel_to_bytes

# ---------- Transformations ----------
def transform_style_units(uploaded_file):
    df = pd.read_excel(uploaded_file, header=2)
    df.columns = df.columns.str.replace(r'[\n"]+', ' ', regex=True).str.strip()

    required = ["DESIGN STYLE", "XFD", "GLOBAL UNITS"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for Savage Buy file: {missing}")

    df = df[required].copy()
    df["XFD_dt"] = pd.to_datetime(df["XFD"], errors="coerce", dayfirst=True)
    if df["XFD_dt"].isna().all() and pd.api.types.is_numeric_dtype(df["XFD"]):
        df["XFD_dt"] = pd.to_datetime(df["XFD"], errors="coerce", unit="D", origin="1899-12-30")

    month_map = {1:"JAN",2:"FEB",3:"MAR",4:"APR",5:"MAY",6:"JUNE",
                 7:"JULY",8:"AUG",9:"SEP",10:"OCT",11:"NOV",12:"DEC"}
    df["MONTH"] = df["XFD_dt"].dt.month.map(month_map)
    df = df[df["MONTH"].notna()]

    pivot_df = df.pivot_table(
        index="DESIGN STYLE",
        columns="MONTH",
        values="GLOBAL UNITS",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    month_order = ["JAN","FEB","MAR","APR","MAY","JUNE","JULY","AUG","SEP","OCT","NOV","DEC"]
    non_month_cols = [c for c in pivot_df.columns if c not in month_order]
    ordered_cols = non_month_cols + [m for m in month_order if m in pivot_df.columns]
    pivot_df = pivot_df[ordered_cols]
    return pivot_df


def transform_plm_to_mcu(uploaded_file):
    expected_sheet_names = [
        "Fabrics", "Strip Cut", "Laces", "Embriodery/Printing",
        "Elastics", "Tapes", "Trim/Component", "Label/ Transfer",
        "Foam Cup", "Packing Trim"
    ]
    base_cols = [
        "Sheet Names", "Season", "Style", "BOM", "Cycle", "Article",
        "Type of Const 1", "Supplier", "UOM", "Composition",
        "Measurement", "Supplier Country", "Avg YY"
    ]
    xls = pd.ExcelFile(uploaded_file)
    collected = []

    for sheet in expected_sheet_names:
        if sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df.columns = df.columns.str.strip()
            mask_keep = ~df.columns.str.strip().str.lower().str.startswith("sum")
            df = df.loc[:, mask_keep]
            df.insert(0, "Sheet Names", sheet)
            for col in base_cols:
                if col not in df.columns:
                    df[col] = ""
            dynamic_cols = [c for c in df.columns if c not in base_cols]
            keep_cols = base_cols + dynamic_cols
            df = df.loc[:, keep_cols]
            collected.append(df)

    if not collected:
        return pd.DataFrame(columns=base_cols)

    combined = pd.concat(collected, ignore_index=True)
    dynamic_cols = [c for c in combined.columns if c not in base_cols]
    final_cols = base_cols + dynamic_cols
    combined = combined.loc[:, final_cols]
    return combined

# ---------- Streamlit UI ----------
name = "Savage - Bucket 02"

def render():
    st.header("Savage — Buy File → PLM Upload")
    buy_file = st.file_uploader("Upload Buy file (Savage)", type=["xlsx","xls"], key="savage_buy")
    if buy_file:
        try:
            df_out = transform_style_units(buy_file)
            st.subheader("Preview — PLM Upload")
            st.dataframe(df_out.head())
            out_bytes = excel_to_bytes(df_out)
            st.download_button("📥 Download PLM Upload", out_bytes, file_name="plm_upload_savage.xlsx")
        except Exception as e:
            st.error(f"Error processing buy file: {e}")

    st.markdown("---")
    st.header("Savage — PLM Download → MCU")
    plm_file = st.file_uploader("Upload PLM Download file (Savage)", type=["xlsx","xls"], key="savage_plm")
    if plm_file:
        try:
            mcu = transform_plm_to_mcu(plm_file)
            st.subheader("Preview — MCU Combined")
            st.dataframe(mcu.head())
            out_bytes = excel_to_bytes(mcu)
            st.download_button("📥 Download MCU", out_bytes, file_name="MCU_savage.xlsx")
        except Exception as e:
            st.error(f"Error processing PLM download file: {e}")
