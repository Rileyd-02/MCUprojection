import streamlit as st
import pandas as pd
from io import BytesIO

# Brand identifier (shows up in sidebar)
name = "CKUM"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    """Convert DataFrame to downloadable Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def transform_ckum_plm_to_mcu(df: pd.DataFrame) -> pd.DataFrame:
    """Transform CKUM PLM Upload → MCU format using the same logic as CKUW."""
    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop sum or metadata columns
    mask_keep = ~df.columns.str.lower().str.startswith("sum")
    df = df.loc[:, mask_keep]

    # (Optional) Add other CKUM-specific transformations if needed later
    return df


def render():
    """Render Streamlit UI for CKUM conversion."""
    st.header("CKUM — PLM Upload → MCU Format")

    uploaded = st.file_uploader("Upload CKUM PLM Upload file", type=["xlsx", "xls"], key="ckum_file")

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            df_out = transform_ckum_plm_to_mcu(df)

            st.subheader("Preview — MCU Format")
            st.dataframe(df_out.head())

            out_bytes = excel_to_bytes(df_out, sheet_name="MCU")

            st.download_button(
                label="📥 Download MCU - CKUM.xlsx",
                data=out_bytes,
                file_name="MCU_CKUM.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing CKUM file: {e}")
