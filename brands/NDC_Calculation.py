import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import io

st.title("📦 NDC Lead Time Adjuster (Simplified)")

st.write("""
Upload the MCU-format Excel file.  
This tool will shift the RM EX-MILL months **back by:**
- 🇱🇰 **3 months** for *Sri Lanka* suppliers (local)
- 🌍 **4 months** for others (foreign)
""")

uploaded_file = st.file_uploader("Upload MCU Format Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ File uploaded successfully!")

        # --- Detect required columns ---
        if "Supplier" not in df.columns or "Supplier Country" not in df.columns:
            st.error("❌ Missing 'Supplier' or 'Supplier Country' columns.")
            st.stop()

        # --- Detect month columns ---
        month_cols = [col for col in df.columns if "-" in str(col)]
        if not month_cols:
            st.error("❌ No month columns found. Expected format: November-25, December-25, etc.")
            st.stop()

        st.info(f"🗓 Detected month columns: {month_cols}")

        # --- Function to shift month name ---
        def shift_month_name(month_name, supplier_country):
            try:
                date_obj = datetime.strptime(month_name, "%B-%y")
                shift = 3 if "sri lanka" in str(supplier_country).lower() else 4
                new_date = date_obj - relativedelta(months=shift)
                return new_date.strftime("%B-%y")
            except:
                return month_name  # fallback if parsing fails

        # --- Create adjusted DataFrame ---
        adjusted_df = df.copy()

        # Add new shifted columns dynamically
        for idx, row in df.iterrows():
            supplier_country = row["Supplier Country"]
            for month in month_cols:
                value = row[month]
                if pd.notna(value) and value != 0:
                    new_month = shift_month_name(month, supplier_country)
                    if new_month not in adjusted_df.columns:
                        adjusted_df[new_month] = 0
                    adjusted_df.at[idx, new_month] += value
                    adjusted_df.at[idx, month] = 0

        # Reorder columns: original + any new shifted ones
        all_cols = df.columns.tolist()
        new_cols = [c for c in adjusted_df.columns if c not in all_cols]
        adjusted_df = adjusted_df[all_cols + new_cols]

        # --- Sanity check ---
        if adjusted_df[month_cols + new_cols].sum(numeric_only=True).sum() == 0:
            st.warning("⚠️ Result is empty — no values were shifted. Please verify month headers and numeric values.")
        else:
            st.success("✅ Lead times adjusted successfully!")
            st.dataframe(adjusted_df.head())

            # --- Download output ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                adjusted_df.to_excel(writer, index=False)
            output.seek(0)

            st.download_button(
                label="📥 Download Adjusted NDC File",
                data=output,
                file_name="NDC_Leadtime_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
