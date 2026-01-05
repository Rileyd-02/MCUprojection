# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "VSPink Apparell - Bucket 03"

# ----------------------------
# Helpers
# ----------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name="MCU"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def clean_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.replace("–", "-", regex=False)
        .str.replace("—", "-", regex=False)
        .str.strip()
    )
    return df


# ----------------------------
# Transformation
# ----------------------------
def transform_vspink_apparel(file) -> pd.DataFrame:
    """
    EX-mill month only
    NO back calculation
    """

    # ✅ Header is THIRD row (index=2)
    df = pd.read_excel(file, header=2)

    df = clean_columns(df)

    required_cols = [
        "Customer",
        "Supplier",
        "Supplier COO",
        "Program",
        "Article",
        "Qty (m)",
        "EX-mill",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"❌ Missing required column(s): {missing}\nDetected: {list(df.columns)}"
        )

    # ----------------------------
    # STRICT EX-MILL PARSING
    # ----------------------------
    df["EX-mill"] = pd.to_datetime(
        df["EX-mill"],
        errors="coerce",
        dayfirst=False   # IMPORTANT: keeps Feb as Feb
    )

    df["Qty (m)"] = (
        df["Qty (m)"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["Qty (m)"] = pd.to_numeric(df["Qty (m)"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["EX-mill", "Qty (m)", "Article"])
    df = df[df["Qty (m)"] != 0]

    if df.empty:
        raise ValueError("❌ No valid rows after EX-mill parsing.")

    # ----------------------------
    # 🔒 MCU Month = EX-mill month ONLY
    # ----------------------------
    df["MCU Month"] = df["EX-mill"].dt.strftime("%b-%y")

    # ----------------------------
    # Pivot
    # ----------------------------
    pivot_df = df.pivot_table(
        index=["Customer", "Supplier", "Supplier COO", "Program", "Article"],
        columns="MCU Month",
        values="Qty (m)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    pivot_df.columns.name = None

    # Sort months chronologically
    month_cols = [c for c in pivot_df.columns if c not in pivot_df.columns[:5]]
    if month_cols:
        ordered = sorted(
            month_cols,
            key=lambda x: pd.to_datetime(x, format="%b-%y")
        )
        pivot_df = pivot_df[
            list(pivot_df.columns[:5]) + ordered
        ]

    return pivot_df


# ----------------------------
# Streamlit UI
# ----------------------------
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU (EX-mill based)")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            df_out = transform_vspink_apparel(uploaded)

            st.subheader("📄 MCU Preview")
            st.dataframe(df_out.head())

            out = excel_to_bytes(df_out)
            st.download_button(
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

