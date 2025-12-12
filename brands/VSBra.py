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

# ----------------------------
# Transformation logic
# ----------------------------
def transform_vs_bra(df):
    df = clean_columns(df)

    REQUIRED = [
        "Vendor", "Category", "Dept Code", "FS", "Program", "Style",
        "BS", "COO", "Supplier Name", "Article No.", "Measurement",
        "REQ. Ex-mill Date", "Requirement (M)"
    ]

    for col in REQUIRED:
        if col not in df.columns:
            raise ValueError(f"❌ Missing required column: {col}")

    # Parse date
    df["REQ. Ex-mill Date"] = pd.to_datetime(df["REQ. Ex-mill Date"], errors="coerce")
    df = df.dropna(subset=["REQ. Ex-mill Date"])
    df["MCU Month"] = df["REQ. Ex-mill Date"].dt.strftime("%b-%y")

    # Clean quantity
    df["Requirement (M)"] = (
        df["Requirement (M)"]
        .astype(str)
        .str.replace(",", "")
        .str.strip()
    )
    df["Requirement (M)"] = pd.to_numeric(df["Requirement (M)"], errors="coerce").fillna(0)

    # Core columns for identity
    identity_cols = [
        "Vendor", "Category", "Dept Code", "FS", "Program", "Style",
        "BS", "COO", "Supplier Name", "Article No.", "Measurement"
    ]

    # Pivot MCU months
    pivot_df = df.pivot_table(
        index=identity_cols,
        columns="MCU Month",
        values="Requirement (M)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    pivot_df.columns.name = None  # remove pivot header

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

    file = st.file_uploader("Upload VS Bra Buy Sheet", type=["xlsx", "xls", "csv"], key="vsbra_file")

    if file:
        try:
            if file.name.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed = transform_vs_bra(df)

            st.subheader("✅ MCU Output")
            st.dataframe(transformed.head())

            out = excel_to_bytes(transformed, sheet_name="MCU")
            st.download_button(
                "📥 Download MCU - VS Bra.xlsx",
                data=out,
                file_name="MCU_VS_Bra.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VS Bra file: {e}")
