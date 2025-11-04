import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io

st.title("NDC Transformation")

st.write("""
Upload the MCU-format file, and this tool will adjust RM EX-MILL months 
based on supplier lead time:
- 🇱🇰 Local suppliers (Sri Lanka): **-3 months**
- 🌍 Foreign suppliers: **-4 months**
""")

uploaded_file = st.file_uploader("Upload MCU Format Excel", type=["xlsx"])

if uploaded_file:
    try:
        # Read the file
        df = pd.read_excel(uploaded_file)

        st.success("✅ File uploaded successfully!")
        st.write("### Preview of uploaded data:")
        st.dataframe(df.head())

        # --- Required Columns ---
        required_columns = ["Supplier", "Supplier Country", "Article"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
            st.stop()

        # --- Detect month columns ---
        month_cols = [col for col in df.columns if "-" in str(col)]
        if not month_cols:
            st.error("No month columns found (e.g., 'November-25', 'December-25').")
            st.stop()

        # Convert month column names into datetime objects for easier shifting
        month_mapping = {}
        for col in month_cols:
            try:
                month_mapping[col] = datetime.strptime(col, "%B-%y")
            except:
                pass

        # --- Function to shift months ---
        def shift_month(current_month, supplier_country):
            date_obj = datetime.strptime(current_month, "%B-%y")
            if "sri lanka" in str(supplier_country).lower():
                new_date = date_obj - relativedelta(months=3)
            else:
                new_date = date_obj - relativedelta(months=4)
            return new_date.strftime("%B-%y")

        # Create adjusted columns
        adjusted_df = df.copy()
        for idx, row in df.iterrows():
            supplier_country = row["Supplier Country"]
            for month in month_cols:
                value = row[month]
                if pd.notna(value) and value != 0:
                    new_month = shift_month(month, supplier_country)
                    if new_month not in adjusted_df.columns:
                        adjusted_df[new_month] = 0
                    adjusted_df.at[idx, new_month] += value
                    adjusted_df.at[idx, month] = 0  # zero out the old value

        # --- Cleanup ---
        adjusted_df = adjusted_df[df.columns.tolist() + list(set(adjusted_df.columns) - set(df.columns))]
        st.success("✅ Lead times adjusted successfully!")

        # Show preview
        st.dataframe(adjusted_df.head())

        # --- Download ---
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
        st.error(f"❌ Error: {str(e)}")
