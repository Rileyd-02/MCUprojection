# brands/vs_bra.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "VS Bra - Bucket 01"

# ----------------------------
# Helper to generate Excel
# ----------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name="Sheet1"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer

# ----------------------------
# Column cleaning
# ----------------------------
def clean_columns(df):
    new_cols = {}
    for c in df.columns:
        new_cols[c] = (
            str(c)
            .replace("\xa0", " ")
            .replace("–", "-")
            .replace("—", "-")
            .strip()
        )
    df.rename(columns=new_cols, inplace=True)
    return df

def detect_column(df, keywords):
    """Detect column by keywords (case-insensitive, partial match)."""
    for c in df.columns:
        col_lower = str(c).lower()
        for kw in keywords:
            if kw.lower() in col_lower:
                return c
    return None

# ----------------------------
# Transformation logic
# ----------------------------
def transform_vs_bra(file) -> pd.DataFrame:
    # Load file (CSV or Excel)
    if hasattr(file, "read") and getattr(file, "name", "").lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, header=0)
        # If all columns are Unnamed, skip first row
        if df.columns.str.contains("Unnamed").all():
            df = pd.read_excel(file, header=1)

    df = clean_columns(df)

    # Detect essential columns
    vendor_col = detect_column(df, ["vendor", "supplier name"])
    category_col = detect_column(df, ["category"])
    dept_col = detect_column(df, ["dept code"])
    fs_col = detect_column(df, ["fs"])
    program_col = detect_column(df, ["program"])
    style_col = detect_column(df, ["style"])
    bs_col = detect_column(df, ["bs"])
    coo_col = detect_column(df, ["coo", "coo code"])
    supplier_col = detect_column(df, ["supplier"])
    article_col = detect_column(df, ["article"])
    measurement_col = detect_column(df, ["measurement"])
    exmill_col = detect_column(df, ["req. ex-mill", "req ex mill", "ex-mill", "ex mill"])
    qty_col = detect_column(df, ["requirement", "qty", "qty (m)"])

    # Validate required columns
    missing = []
    for col_name, col_value in [
        ("Vendor", vendor_col),
        ("Category", category_col),
        ("Dept Code", dept_col),
        ("FS", fs_col),
        ("Program", program_col),
        ("Style", style_col),
        ("BS", bs_col),
        ("COO", coo_col),
        ("Supplier Name", supplier_col),
        ("Article No.", article_col),
        ("Measurement", measurement_col),
        ("REQ. Ex-mill Date", exmill_col),
        ("Requirement (M)", qty_col),
    ]:
        if col_value is None:
            missing.append(col_name)
    if missing:
        raise ValueError(f"❌ Missing required column(s): {', '.join(missing)}. Detected columns: {list(df.columns)}")

    # Parse date
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")
    df = df.dropna(subset=[exmill_col, article_col])
    if df.empty:
        raise ValueError("No valid rows after parsing EX-mill dates or Article values.")

    # Clean quantity
    df[qty_col] = (
        df[qty_col].astype(str)
        .str.replace(",", "")
        .str.strip()
    )
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
    df = df[df[qty_col] != 0]

    # Build Month label
    df["MCU Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Identity columns
    identity_cols = [
        vendor_col, category_col, dept_col, fs_col, program_col,
        style_col, bs_col, coo_col, supplier_col, article_col, measurement_col
    ]

    # Pivot
    pivot_df = df.pivot_table(
        index=identity_cols,
        columns="MCU Month",
        values=qty_col,
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    pivot_df.columns.name = None

    # Sort month columns
    month_cols = [c for c in pivot_df.columns if c not in identity_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        ordered = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[identity_cols + ordered]

    return pivot_df

# ----------------------------
# Streamlit Page Rendering
# ----------------------------
def render():
    st.header("VS Bra — Buy Sheet → MCU Format")
    st.markdown(
        "Upload the VS Bra buy sheet. The app will pivot the REQ. Ex-mill Date into month columns and place Qty into the corresponding month column."
    )

    uploaded = st.file_uploader(
        "Upload VS Bra file (xlsx, xls, csv)",
        type=["xlsx", "xls", "csv"],
        key="vsbra_file"
    )

    if not uploaded:
        return

    try:
        df_out = transform_vs_bra(uploaded)
        st.subheader("Preview")
        st.dataframe(df_out.head())

        out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
        st.download_button(
            "📥 Download MCU - VS Bra.xlsx",
            data=out_bytes,
            file_name="MCU_VS_Bra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Error processing VS Bra file: {e}")
