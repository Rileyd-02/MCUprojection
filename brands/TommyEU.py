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

    # MCU month mapping (Tommy EU uses Nov–Mar)
    mcu["Nov"] = df.get("Nov", 0)
    mcu["Dec"] = df.get("Dec", 0)
    mcu["Jan"] = df.get("Jan", 0)
    mcu["Feb"] = df.get("Feb", 0)
    mcu["Mar"] = df.get("Mar", 0)

    # Fixed values
    mcu["Column24"] = ""
    mcu["Column25"] = ""
    mcu["Fabrics_1"] = "Fabrics"
    mcu["Sheet"] = "Sheet"
    mcu["false"] = "FALSE"

    return mcu


def process_tommy_eu(buy_sheet, plm_download_files, season="Spring 2025"):
    buy_df = pd.read_excel(buy_sheet)
    plm_upload = transform_buy_to_plm_upload(buy_df)

    mcu_frames = []
    for file in plm_download_files:
        df = pd.read_excel(file)
        mcu_frames.append(transform_plm_download_to_mcu(df, season))

    mcu_final = pd.concat(mcu_frames, ignore_index=True)
    return plm_upload, mcu_final


# -----------------------------------------------------------
# STREAMLIT UI FOR TOMMY EU BRAND
# -----------------------------------------------------------

def tommy_eu_ui():
    st.header("🇪🇺 Tommy EU – Buy Sheet → PLM Upload → MCU Format")

    st.markdown("""
    Use this tool to process **Tommy EU** raw files:
    - Buy Sheet ➜ PLM Upload file  
    - PLM Download(s) ➜ MCU format  
    """)

    # ---------------- BUY SHEET UPLOAD ----------------
    st.subheader("📘 Step 1 – Upload Buy Sheet")
    buy_sheet = st.file_uploader("Upload the buy sheet (Excel)", type=["xlsx"])

    # ---------------- PLM DOWNLOAD UPLOAD ----------------
    st.subheader("📗 Step 2 – Upload PLM Download File(s)")
    plm_downloads = st.file_uploader(
        "Upload one or multiple PLM Download files",
        type=["xlsx"],
        accept_multiple_files=True
    )

    season = st.text_input("Season", "Spring 2025")

    if st.button("Process Tommy EU Files"):
        if not buy_sheet:
            st.error("Please upload the Buy Sheet file.")
            return
        
        if not plm_downloads:
            st.error("Please upload at least one PLM Download file.")
            return

        try:
            plm_upload, mcu_final = process_tommy_eu(buy_sheet, plm_downloads, season)

            st.success("✔ Tommy EU files processed successfully!")

            # ---------------- DOWNLOAD PLM UPLOAD ----------------
            st.subheader("📥 Download PLM Upload File")

            plm_buffer = io.BytesIO()
            with pd.ExcelWriter(plm_buffer, engine="xlsxwriter") as writer:
                plm_upload.to_excel(writer, index=False, sheet_name="PLM Upload")

            st.download_button(
                "Download PLM Upload",
                plm_buffer.getvalue(),
                file_name="TommyEU_PLM_Upload.xlsx"
            )

            # ---------------- DOWNLOAD MCU FILE ----------------
            st.subheader("📥 Download MCU Format File")

            mcu_buffer = io.BytesIO()
            with pd.ExcelWriter(mcu_buffer, engine="xlsxwriter") as writer:
                mcu_final.to_excel(writer, index=False, sheet_name="MCU")

            st.download_button(
                "Download MCU File",
                mcu_buffer.getvalue(),
                file_name="TommyEU_MCU.xlsx"
            )

            # ---------------- PREVIEW TABLES ----------------
            st.subheader("📄 Preview – PLM Upload")
            st.dataframe(plm_upload.head())

            st.subheader("📄 Preview – MCU Output")
            st.dataframe(mcu_final.head())

        except Exception as e:
            st.error(f"❌ Error: {e}")


# -----------------------------------------------------------
# CALLABLE ENTRY FOR MAIN APP
# -----------------------------------------------------------

if __name__ == "__main__":
    tommy_eu_ui()
