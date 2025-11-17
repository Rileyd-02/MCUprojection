import streamlit as st
import pandas as pd
import io

# -----------------------------------------------------------
# TOMMY EU — TRANSFORMATION FUNCTIONS
# -----------------------------------------------------------

def transform_buy_to_plm_upload(df):
    month_cols = [c for c in df.columns if c in
                  ["Jul","Aug","Sep","Oct","Nov","Dec",
                   "Jan","Feb","Mar","Apr","May","Jun"]]

    df["Style number"] = df["Generic Article"].astype(str).str[:11]

    final_cols = ["Style number"] + month_cols
    out = df[final_cols].copy()
    out[month_cols] = out[month_cols].fillna(0)

    return out


def transform_plm_download_to_mcu(df, season="Spring 2025"):
    mcu = pd.DataFrame()
    mcu["Fabrics"] = "Fabrics"
    mcu["Season"] = season
    mcu["Style"] = df["Style"]
    mcu["BOM"] = df["BOM"]
    mcu["Cycle"] = df["Cycle"]
    mcu["Article"] = df["Article"]
    mcu["Type of Const 1"] = df["Type of Const 1"]
    mcu["Supplier"] = df["Supplier"]
    mcu["UOM"] = df["UOM"]
    mcu["Composition"] = df["Composition"]
    mcu["Measurement"] = df["Measurement"]
    mcu["Supplier Country"] = df["Supplier Country"]
    mcu["Avg YY"] = df["Avg YY"]

    # MCU month mapping
    for m in ["Nov", "Dec", "Jan", "Feb", "Mar"]:
        mcu[m] = df.get(f"Sum of {m}", df.get(m, 0))

    mcu["Column24"] = ""
    mcu["Column25"] = ""
    mcu["Fabrics_1"] = "Fabrics"
    mcu["Sheet"] = "Sheet"
    mcu["false"] = "FALSE"

    return mcu


def process_tommy_eu(buy_sheet_file, plm_download_files, season="Spring 2025"):
    buy_df = pd.read_excel(buy_sheet_file)
    plm_upload = transform_buy_to_plm_upload(buy_df)

    mcu_frames = []
    for file in plm_download_files:
        df = pd.read_excel(file)
        mcu_frames.append(transform_plm_download_to_mcu(df, season))

    mcu_final = pd.concat(mcu_frames, ignore_index=True)
    return plm_upload, mcu_final


# -----------------------------------------------------------
# UI
# -----------------------------------------------------------

def render():
    st.header("🇪🇺 Tommy EU – Buy Sheet → PLM Upload → MCU Format")

    st.markdown("""
    Use this tool to process **Tommy EU** files:
    - Buy Sheet ➜ PLM Upload  
    - PLM Download(s) ➜ MCU Format  
    """)

    buy_sheet = st.file_uploader("Upload the Buy Sheet", type=["xlsx"], key="tommy_buy_sheet")
    plm_downloads = st.file_uploader(
        "Upload PLM Download file(s)",
        type=["xlsx"],
        accept_multiple_files=True,
        key="tommy_plm_download"
    )

    season = st.text_input("Season", value="Spring 2025", key="tommy_season")

    if st.button("Process Tommy EU Files"):
        if not buy_sheet:
            st.error("Please upload a Buy Sheet.")
            return
        
        if not plm_downloads:
            st.error("Please upload at least one PLM Download file.")
            return

        try:
            plm_upload, mcu_final = process_tommy_eu(buy_sheet, plm_downloads, season)

            st.success("✔ Processing completed!")

            # PLM upload download
            buffer1 = io.BytesIO()
            with pd.ExcelWriter(buffer1, engine="xlsxwriter") as writer:
                plm_upload.to_excel(writer, index=False, sheet_name="PLM Upload")

            st.download_button(
                "⬇ Download PLM Upload",
                buffer1.getvalue(),
                file_name="TommyEU_PLM_Upload.xlsx"
            )

            # MCU download
            buffer2 = io.BytesIO()
            with pd.ExcelWriter(buffer2, engine="xlsxwriter") as writer:
                mcu_final.to_excel(writer, index=False, sheet_name="MCU")

            st.download_button(
                "⬇ Download MCU Format",
                buffer2.getvalue(),
                file_name="TommyEU_MCU.xlsx"
            )

            st.subheader("PLM Upload Preview")
            st.dataframe(plm_upload.head())

            st.subheader("MCU Preview")
            st.dataframe(mcu_final.head())

        except Exception as e:
            st.error(f"❌ Error: {e}")
