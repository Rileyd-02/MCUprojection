# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Display name in sidebar
name = "VSPink Apparel - Bucket 03"

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
    cleaned = {}
    for c in df.columns:
        cleaned[c] = (
            str(c)
            .replace("\xa0", " ")
            .replace("–", "-")
            .replace("—", "-")
            .strip()
        )
    df.rename(columns=cleaned, inplace=True)
    return df

# ----------------------------
# Transformation
# ----------------------------
def transform_vspink_apparel(file) -> pd.DataFrame:
    """Transform VSPink Apparel Buy Sheet → MCU Format
       (NO back calculation — EX-mill month only)
    """

    # Header is on second row
    df = pd.read_excel(file, header=1)

    df = clean_columns(df)

    required_cols = [
        "Customer", "Supplier", "Supplier COO",
        "Program", "Article", "Qty (m)", "EX-mill"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(
                f"❌ Required column missing: {col}. Columns detected: {list(df.columns)}"
            )

    # Parse EX-mill date
    df["EX-mill"] = pd.to_datetime(df["EX-mill"], errors="coerce")
    df = df.dropna(subset=["EX-mill", "Article"])

    if df.empty:
        raise ValueError("❌ No valid rows found after EX-mill + Article filtering.")

    # 🔥 NO BACK CALCULATION
    # MCU Month = EX-mill month
    df["MCU Month"] = df["EX-mill"].dt.strftime("%b-%y")

    # Pivot
    pivot_df = df.pivot_table(
        index=["Customer", "Supplier", "Supplier COO", "Program", "Article"],
        columns="MCU Month",
        values="Qty (m)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    pivot_df.columns.name = None
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

# ----------------------------
# Streamlit Page
# ----------------------------
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            df_out = transform_vspink_apparel(uploaded)

            st.subheader("📄 Preview Transformed MCU")
            st.dataframe(df_out.head())

            out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
            st.download_button(
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
