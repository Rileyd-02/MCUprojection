# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO
from dateutil.relativedelta import relativedelta

# Display name in sidebar
name = "VSPink Apparel"

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
    """Fix hidden spaces and normalize column names"""
    cleaned = {}
    for c in df.columns:
        new_c = (
            str(c)
            .replace("\xa0", " ")
            .replace("–", "-")
            .replace("—", "-")
            .strip()
        )
        cleaned[c] = new_c
    df.rename(columns=cleaned, inplace=True)
    return df

def transform_vspink_apparel(file) -> pd.DataFrame:
    """Transform Buy Sheet → MCU Format"""
    df = pd.read_excel(file, header=0)

    # Remove first blank row if present
    if df.iloc[0].isna().all():
        df = df.iloc[1:].copy()

    # Clean column names
    df = clean_columns(df)

    # Detect required columns
    for col in ["Customer", "Supplier", "Supplier COO", "Program", "Article", "Qty (m)", "EX-mill"]:
        if col not in df.columns:
            raise ValueError(f"❌ Required column missing: {col}")

    # Parse EX-mill dates
    df["EX-mill"] = pd.to_datetime(df["EX-mill"], errors="coerce")
    df = df.dropna(subset=["EX-mill", "Article"])
    if df.empty:
        raise ValueError("❌ No valid rows found after EX-mill + Article filtering.")

    # Determine sourcing type
    df["Sourcing Type"] = df["Supplier COO"].apply(lambda x: "LOCAL" if str(x).strip().upper() == "SL" else "FOREIGN")

    # Back-calc MCU Month
    def compute_mcu_date(row):
        if row["Sourcing Type"] == "LOCAL":
            return row["EX-mill"] - relativedelta(months=3)
        else:
            return row["EX-mill"] - relativedelta(months=4)

    df["MCU Month"] = df.apply(compute_mcu_date, axis=1)
    df["MCU Month"] = df["MCU Month"].dt.strftime("%b-%y")  # e.g., Aug-25

    # Prepare final MCU output
    output_cols = ["Customer", "Supplier", "Supplier COO", "Program", "Article", "Qty (m)", "EX-mill", "MCU Month"]
    final_df = df[output_cols]

    # Pivot so that each MCU Month is a column with Qty
    pivot_df = final_df.pivot_table(
        index=["Customer", "Supplier", "Supplier COO", "Program", "Article"],
        columns="MCU Month",
        values="Qty (m)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Flatten columns
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
            if df_out.empty:
                st.warning("No valid rows found after transformation.")
                return

            st.subheader("📄 Preview Transformed MCU")
            st.dataframe(df_out.head())

            out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
            st.download_button(
                label="📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
