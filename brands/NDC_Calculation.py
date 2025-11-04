# brands/ndc.py
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import timedelta
import re

name = "NDC"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# ---- helpers ----
_MONTH_KEYWORDS = [
    "jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",
    "january","february","march","april","may","june","july","august","september","october","november","december"
]

def detect_month_columns(df: pd.DataFrame):
    """Return list of columns that look like month-year headers."""
    months = []
    for c in df.columns:
        low = str(c).lower()
        # pick columns that contain a month keyword and a year-like number
        if any(m in low for m in _MONTH_KEYWORDS) and re.search(r"\d{2,4}", low):
            months.append(c)
    return months

def parse_month_string(s: str):
    """
    Try several formats to parse month header strings into Timestamp (1st day of month).
    Accepts forms like: 'Nov-25', 'November-25', 'Nov-2025', 'November 2025', 'Nov 25', 'Nov25'.
    Returns pd.Timestamp or NaT.
    """
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    # normalize separators
    s = re.sub(r"[._/\\]", "-", s)
    s = re.sub(r"\s+", " ", s)
    formats = ["%b-%y","%B-%y","%b-%Y","%B-%Y","%b %y","%B %y","%b%y","%B%y","%Y-%b","%Y-%B"]
    for fmt in formats:
        try:
            return pd.to_datetime(s, format=fmt, errors="raise")
        except Exception:
            continue
    # as last resort let pandas infer
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return pd.NaT

# ---- main transform ----
def transform_ndc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.shape[0] == 0:
        return pd.DataFrame()

    # clean column names
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace("\n", " ").str.replace("\r", " ")

    st.write("Detected columns:", list(df.columns))

    # detect supplier columns
    supplier_col = next((c for c in df.columns if c.strip().lower() == "supplier"), None)
    supplier_country_col = next((c for c in df.columns if "supplier country" in c.strip().lower()), None)
    if not supplier_col or not supplier_country_col:
        raise ValueError("Missing 'Supplier' or 'Supplier Country' columns. Found: " + ", ".join(df.columns))

    # detect month columns
    month_cols = detect_month_columns(df)
    st.write("Detected month-like columns:", month_cols)
    if not month_cols:
        raise ValueError("No month columns detected. Month columns should contain month names and a year (e.g. 'Nov-25' or 'November-25').")

    # melt months into rows
    id_vars = [c for c in df.columns if c not in month_cols]
    melted = df.melt(id_vars=id_vars, value_vars=month_cols, var_name="OriginalMonth", value_name="Qty")

    # parse OriginalMonth into a dt (first day of month)
    melted["OriginalMonth_dt"] = melted["OriginalMonth"].apply(parse_month_string)
    st.write("Sample parsed months:", melted["OriginalMonth_dt"].dropna().unique()[:10])

    # drop rows where parsing failed
    melted = melted.dropna(subset=["OriginalMonth_dt"])
    if melted.empty:
        raise ValueError("After parsing month headers, no valid month values remained. Check the month column headers.")

    # ensure Qty numeric
    melted["Qty"] = (melted["Qty"].astype(str).str.replace(",", "", regex=False).str.strip())
    melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce").fillna(0)

    # determine adjusted date based on supplier country
    def adjust_dt(row):
        country = str(row.get(supplier_country_col, "")).strip().lower()
        # treat 'sri lanka' (or containing 'sri', 'lanka') as local
        if "sri lanka" in country or ("sri" in country and "lanka" in country) or country in ("sl","sri", "srilanka"):
            return row["OriginalMonth_dt"] - timedelta(days=93)
        else:
            return row["OriginalMonth_dt"] - timedelta(days=120)

    melted["Adjusted_dt"] = melted.apply(adjust_dt, axis=1)
    melted["AdjustedMonth"] = melted["Adjusted_dt"].dt.strftime("%b-%y")

    # Build meta columns: all original columns except original month columns
    meta_cols = id_vars

    # group by meta + adjusted month
    grouped = melted.groupby(meta_cols + ["AdjustedMonth"], as_index=False)["Qty"].sum()

    if grouped.empty:
        st.warning("Grouping resulted in empty dataframe — no quantities found after adjustments.")
        return pd.DataFrame()

    # pivot back to wide
    pivot_df = grouped.pivot_table(index=meta_cols, columns="AdjustedMonth", values="Qty", fill_value=0, aggfunc="sum").reset_index()

    # sort month columns chronologically
    month_cols_new = [c for c in pivot_df.columns if c not in meta_cols]
    if month_cols_new:
        parsed = [parse_month_string(c) for c in month_cols_new]
        # pair and sort
        paired = sorted(zip(parsed, month_cols_new), key=lambda x: (pd.NaT if pd.isna(x[0]) else x[0]))
        ordered_months = [m for _, m in paired]
        pivot_df = pivot_df[meta_cols + ordered_months]

    # flatten column names
    pivot_df.columns = [str(c) for c in pivot_df.columns]
    return pivot_df

# ---- Streamlit UI ----
def render():
    st.header("NDC — Lead-time Adjusted MCU")

    uploaded = st.file_uploader("Upload NDC MCU file (PLM-style)", type=["xlsx", "xls", "csv"], key="ndc_file")

    if not uploaded:
        st.info("Upload the MCU/PLM file containing month columns (e.g., 'November-25').")
        return

    try:
        if str(uploaded).lower().endswith(".csv") or getattr(uploaded, "type", "") == "text/csv":
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        st.subheader("Input preview")
        st.dataframe(df.head())

        out_df = transform_ndc(df)

        if out_df.empty:
            st.warning("Result is empty after transformation. Check month headers and Supplier/Supplier Country values.")
            return

        st.subheader("Lead-time adjusted output")
        st.dataframe(out_df.head())

        out_bytes = excel_to_bytes(out_df, sheet_name="MCU_Adjusted")
        st.download_button("📥 Download NDC MCU Adjusted.xlsx", data=out_bytes, file_name="NDC_MCU_Adjusted.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Error processing file: {e}")
