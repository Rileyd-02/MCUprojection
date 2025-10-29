import streamlit as st
import pandas as pd
from io import BytesIO

# Display name in sidebar
name = "VSPink Brief"

# ---------------------------
# Helper: Convert DataFrame to Excel Bytes
# ---------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


# ---------------------------
# Transformation Logic
# ---------------------------
def transform_vspink_brief(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform VSPink Brief Buy Sheet → MCU Format.
    EX-mill date is converted into month name (e.g., "Oct-25"),
    and Qty (m) is assigned to that month column.
    """
    df.columns = df.columns.str.strip()

    # Ensure required columns exist
    required_cols = ["Article", "EX-mill", "Qty (m)"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: '{col}'")

    # Convert EX-mill to datetime
    df["EX-mill"] = pd.to_datetime(df["EX-mill"], errors="coerce")
    df = df.dropna(subset=["EX-mill"])  # drop rows with invalid dates

    # Create month label (e.g. Oct-25)
    df["Month"] = df["EX-mill"].dt.strftime("%b-%y")

    # Keep relevant columns
    base_cols = [c for c in df.columns if c not in ["Qty (m)", "EX-mill"]]
    pivot_df = (
        df.pivot_table(
            index=base_cols,
            columns="Month",
            values="Qty (m)",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    # Flatten MultiIndex columns
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df


# ---------------------------
# Streamlit UI
# ---------------------------
def render():
    st.header("VSPink Brief — Buy Sheet → MCU Format")

    uploaded = st.file_uploader("Upload VSPink Brief Buy Sheet", type=["xlsx", "xls"], key="vspink_brief_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_vspink_brief(df)

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU")

            st.download_button(
                label="📥 Download MCU - VSPink Brief.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Brief.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Brief file: {e}")
