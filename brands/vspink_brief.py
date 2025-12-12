# brands/vspink_brief.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "VSPink Brief - Bucket 03"

# ----------------------------
# Helper utilities
# ----------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def clean_columns(df):
    """Clean hidden spaces and normalize column names"""
    cleaned = {}
    for c in df.columns:
        new_c = str(c).strip().replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
        cleaned[c] = new_c
    df.rename(columns=cleaned, inplace=True)
    return df

def detect_column(df, keywords):
    """Detect column by keywords (case-insensitive)."""
    for c in df.columns:
        low = str(c).lower()
        for kw in keywords:
            if kw.lower() in low:
                return c
    return None

# ----------------------------
# Transformation
# ----------------------------
def transform_vspink_brief(file) -> pd.DataFrame:
    """
    Transform VSPink Brief Buy Sheet → MCU Format:
    - EX-mill → Month label (e.g., Mar-26)
    - Pivot month columns with quantities
    - Preserve metadata columns
    """
    # Load file (CSV or Excel)
    if hasattr(file, "read") and getattr(file, "name", "").lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, header=0)
        # Skip first row if all Unnamed
        if df.columns.str.contains("Unnamed").all():
            df = pd.read_excel(file, header=1)

    df = clean_columns(df)

    # Detect essential columns
    article_col = detect_column(df, ["article"])
    exmill_col = detect_column(df, ["ex-mill", "ex mill", "exmill", "rm ex mill"])
    qty_col = detect_column(df, ["qty", "qty (m)", "requirement"])

    if not article_col or not exmill_col or not qty_col:
        raise ValueError(f"Could not detect required columns. Found: {list(df.columns)}")

    # Parse EX-mill -> datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")
    df = df.dropna(subset=[exmill_col, article_col])
    if df.empty:
        raise ValueError("No valid rows after parsing EX-mill dates or Article values.")

    # Ensure Qty numeric
    df[qty_col] = pd.to_numeric(df[qty_col].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)
    df = df[df[qty_col] != 0]

    # Build Month label
    df["_MCU_Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Identify metadata columns
    meta_cols = []
    for key in ["Customer", "Supplier", "Supplier COO", "Program", article_col, "Measurement", "Supplier Country", "Type of Cons1", "Plant"]:
        if key in df.columns:
            meta_cols.append(key)
        else:
            df[key] = ""  # create empty column if missing
            meta_cols.append(key)

    # Group & pivot
    grouped = df.groupby(meta_cols + ["_MCU_Month"], as_index=False)[qty_col].sum().rename(columns={qty_col: "Qty"})
    pivot = grouped.pivot_table(
        index=meta_cols,
        columns="_MCU_Month",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Flatten columns
    pivot.columns.name = None
    pivot.columns = [str(c) for c in pivot.columns]

    # Sort month columns chronologically
    month_cols = [c for c in pivot.columns if c not in meta_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        col_order = [col for _, col in sorted(zip(parsed, month_cols), key=lambda x: pd.Timestamp.min if pd.isna(x[0]) else x[0])]
        pivot = pivot[meta_cols + col_order]

    return pivot

# ----------------------------
# Streamlit UI
# ----------------------------
def render():
    st.header("VSPink Brief — Buy Sheet → MCU Format")
    st.markdown("Upload the VSPink Brief buy sheet. The app will pivot the EX-mill date into month columns and place Qty into the corresponding month column.")

    uploaded = st.file_uploader(
        "Upload VSPink Brief file (xlsx, xls, csv)",
        type=["xlsx", "xls", "csv"],
        key="vspink_brief_file"
    )

    if not uploaded:
        return

    try:
        df_out = transform_vspink_brief(uploaded)
        st.subheader("Preview")
        st.dataframe(df_out.head())

        out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
        st.download_button(
            "📥 Download MCU - VSPink Brief.xlsx",
            data=out_bytes,
            file_name="MCU_VSPink_Brief.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")
