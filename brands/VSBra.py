# brands/vs_bra.py

import streamlit as st
import pandas as pd
from io import BytesIO


name = "VS Bra - Bucket 01"


# ============================================================
# Helper: Generate Excel file
# ============================================================

def excel_to_bytes(df: pd.DataFrame, sheet_name="Sheet1"):
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name
        )

    buffer.seek(0)

    return buffer


# ============================================================
# Column Cleaning
# ============================================================

def clean_columns(df):
    """
    Cleans column names by:
    - Converting to string
    - Removing non-breaking spaces
    - Replacing en/em dashes
    - Removing leading/trailing spaces
    - Converting multiple spaces to a single space
    """

    df = df.copy()

    new_cols = {}

    for c in df.columns:

        cleaned = (
            str(c)
            .replace("\xa0", " ")
            .replace("–", "-")
            .replace("—", "-")
            .strip()
        )

        # Convert multiple spaces into one
        cleaned = " ".join(cleaned.split())

        new_cols[c] = cleaned

    df.rename(
        columns=new_cols,
        inplace=True
    )

    return df


# ============================================================
# Cell Value Cleaning
# ============================================================

def clean_cell_values(df):
    """
    Cleans text values throughout the dataframe.

    This is important because Excel files can contain
    invisible/non-breaking spaces inside the actual cells,
    not just in the column headers.
    """

    df = df.copy()

    for col in df.columns:

        if df[col].dtype == "object":

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(
                    "\xa0",
                    " ",
                    regex=False
                )
                .str.replace(
                    "\u200b",
                    "",
                    regex=False
                )
                .str.strip()
            )

            # Convert literal "nan" strings back to blank
            df[col] = df[col].replace(
                {
                    "nan": "",
                    "NaN": "",
                    "None": ""
                }
            )

    return df


# ============================================================
# Date Cleaning
# ============================================================

def parse_exmill_date(series):
    """
    Robustly parses REQ. Ex-mill Date.

    Handles:
    - Excel datetime values
    - Normal date strings
    - MM/DD/YYYY
    - DD/MM/YYYY where possible
    - Blank values
    """

    # First attempt
    parsed = pd.to_datetime(
        series,
        errors="coerce"
    )

    # If some values failed, try a second pass
    failed = parsed.isna() & series.notna()

    if failed.any():

        parsed_retry = pd.to_datetime(
            series[failed],
            errors="coerce",
            format="mixed"
        )

        parsed.loc[failed] = parsed_retry

    return parsed


# ============================================================
# Transformation Logic
# ============================================================

def transform_vs_bra(df):

    # --------------------------------------------------------
    # 1. Make a copy
    # --------------------------------------------------------

    df = df.copy()


    # --------------------------------------------------------
    # 2. Clean column names
    # --------------------------------------------------------

    df = clean_columns(df)


    # --------------------------------------------------------
    # 3. Clean cell values
    # --------------------------------------------------------

    df = clean_cell_values(df)


    # --------------------------------------------------------
    # 4. Required columns
    # --------------------------------------------------------

    REQUIRED = [
        "Vendor",
        "Category",
        "Dept Code",
        "FS",
        "Program",
        "Style",
        "BS",
        "COO",
        "Supplier Name",
        "Article No.",
        "Measurement",
        "REQ. Ex-mill Date",
        "Requirement (M)"
    ]


    # --------------------------------------------------------
    # 5. Validate required columns
    # --------------------------------------------------------

    missing = [
        col
        for col in REQUIRED
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "❌ Missing required column(s): "
            + ", ".join(missing)
            + "\n\n"
            + "Available columns are:\n"
            + ", ".join(map(str, df.columns))
        )


    # --------------------------------------------------------
    # 6. Check input data
    # --------------------------------------------------------

    if df.empty:

        raise ValueError(
            "❌ The uploaded Excel file contains no data rows."
        )


    # --------------------------------------------------------
    # 7. Store original date values for debugging
    # --------------------------------------------------------

    original_dates = (
        df["REQ. Ex-mill Date"]
        .copy()
    )


    # --------------------------------------------------------
    # 8. Parse REQ. Ex-mill Date
    # --------------------------------------------------------

    df["REQ. Ex-mill Date"] = parse_exmill_date(
        df["REQ. Ex-mill Date"]
    )


    # --------------------------------------------------------
    # 9. Identify invalid dates
    # --------------------------------------------------------

    invalid_dates = (
        df["REQ. Ex-mill Date"]
        .isna()
    )


    # --------------------------------------------------------
    # 10. Display invalid dates
    # --------------------------------------------------------

    if invalid_dates.any():

        invalid_count = int(
            invalid_dates.sum()
        )

        invalid_values = (
            original_dates[invalid_dates]
            .astype(str)
            .tolist()
        )

        st.warning(
            f"⚠️ {invalid_count} row(s) have an invalid "
            f"'REQ. Ex-mill Date' and will be excluded."
        )

        with st.expander(
            "View invalid date values"
        ):

            st.write(
                invalid_values
            )


    # --------------------------------------------------------
    # 11. Remove rows with invalid dates
    # --------------------------------------------------------

    df = df.loc[
        ~invalid_dates
    ].copy()


    # --------------------------------------------------------
    # 12. Check if data remains
    # --------------------------------------------------------

    if df.empty:

        raise ValueError(
            "❌ No valid rows remain after processing "
            "'REQ. Ex-mill Date'.\n\n"
            "The uploaded file contains rows, but none of "
            "the REQ. Ex-mill Date values could be interpreted "
            "as valid dates."
        )


    # --------------------------------------------------------
    # 13. Create MCU Month
    # --------------------------------------------------------

    df["MCU Month"] = (
        df["REQ. Ex-mill Date"]
        .dt.strftime("%b-%y")
    )


    # --------------------------------------------------------
    # 14. Validate MCU Month
    # --------------------------------------------------------

    if df["MCU Month"].isna().all():

        raise ValueError(
            "❌ Unable to create MCU Month from "
            "'REQ. Ex-mill Date'."
        )


    # --------------------------------------------------------
    # 15. Clean Requirement (M)
    # --------------------------------------------------------

    df["Requirement (M)"] = (
        df["Requirement (M)"]
        .astype(str)
        .str.replace(
            "\xa0",
            "",
            regex=False
        )
        .str.replace(
            ",",
            "",
            regex=False
        )
        .str.strip()
    )


    # --------------------------------------------------------
    # 16. Convert Requirement (M) to numeric
    # --------------------------------------------------------

    df["Requirement (M)"] = pd.to_numeric(
        df["Requirement (M)"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # 17. Replace invalid quantities with zero
    # --------------------------------------------------------

    df["Requirement (M)"] = (
        df["Requirement (M)"]
        .fillna(0)
    )


    # --------------------------------------------------------
    # 18. Core identity columns
    # --------------------------------------------------------

    identity_cols = [
        "Vendor",
        "Category",
        "Dept Code",
        "FS",
        "Program",
        "Style",
        "BS",
        "COO",
        "Supplier Name",
        "Article No.",
        "Measurement"
    ]


    # --------------------------------------------------------
    # 19. Check data before pivot
    # --------------------------------------------------------

    if df.empty:

        raise ValueError(
            "❌ No data available before pivot."
        )


    # --------------------------------------------------------
    # 20. Pivot MCU months
    # --------------------------------------------------------

    pivot_df = df.pivot_table(
        index=identity_cols,
        columns="MCU Month",
        values="Requirement (M)",
        aggfunc="sum",
        fill_value=0
    ).reset_index()


    # --------------------------------------------------------
    # 21. Remove pivot column name
    # --------------------------------------------------------

    pivot_df.columns.name = None


    # --------------------------------------------------------
    # 22. Identify month columns
    # --------------------------------------------------------

    month_cols = [
        c
        for c in pivot_df.columns
        if c not in identity_cols
    ]


    # --------------------------------------------------------
    # 23. Sort month columns chronologically
    # --------------------------------------------------------

    if month_cols:

        parsed_months = pd.to_datetime(
            month_cols,
            format="%b-%y",
            errors="coerce"
        )

        month_pairs = list(
            zip(
                parsed_months,
                month_cols
            )
        )

        month_pairs = [
            pair
            for pair in month_pairs
            if not pd.isna(pair[0])
        ]

        month_pairs.sort(
            key=lambda x: x[0]
        )

        ordered_months = [
            month
            for _, month in month_pairs
        ]

        pivot_df = pivot_df[
            identity_cols + ordered_months
        ]


    # --------------------------------------------------------
    # 24. Final output validation
    # --------------------------------------------------------

    if pivot_df.empty:

        raise ValueError(
            "❌ Pivot produced an empty output.\n\n"
            "Please check the uploaded data."
        )


    # --------------------------------------------------------
    # 25. Return transformed dataframe
    # --------------------------------------------------------

    return pivot_df


# ============================================================
# Streamlit Page Rendering
# ============================================================

def render():

    st.header(
        "VS Bra — Buy Sheet → MCU Format"
    )


    # --------------------------------------------------------
    # File Upload
    # --------------------------------------------------------

    file = st.file_uploader(
        "Upload VS Bra Buy Sheet",
        type=[
            "xlsx",
            "xls",
            "csv"
        ],
        key="vsbra_file"
    )


    # --------------------------------------------------------
    # Process file
    # --------------------------------------------------------

    if file:

        try:

            # ------------------------------------------------
            # Read input file
            # ------------------------------------------------

            if file.name.lower().endswith(".csv"):

                df = pd.read_csv(
                    file
                )

            else:

                df = pd.read_excel(
                    file
                )


            # ------------------------------------------------
            # Input validation
            # ------------------------------------------------

            if df.empty:

                st.error(
                    "❌ The uploaded file is empty."
                )

                return


            # ------------------------------------------------
            # Input Preview
            # ------------------------------------------------

            st.subheader(
                "📄 Input Preview"
            )

            st.dataframe(
                df.head(20),
                use_container_width=True
            )


            # ------------------------------------------------
            # Debug Information
            # ------------------------------------------------

            with st.expander(
                "🔍 File Debug Information"
            ):

                st.write(
                    "**File name:**",
                    file.name
                )

                st.write(
                    "**Number of rows:**",
                    len(df)
                )

                st.write(
                    "**Number of columns:**",
                    len(df.columns)
                )

                st.write(
                    "**Columns detected:**"
                )

                st.write(
                    list(df.columns)
                )


                # Show raw Ex-mill dates
                if "REQ. Ex-mill Date" in df.columns:

                    st.write(
                        "**REQ. Ex-mill Date values:**"
                    )

                    st.write(
                        df[
                            "REQ. Ex-mill Date"
                        ]
                        .head(20)
                        .tolist()
                    )


                # Show Requirement values
                if "Requirement (M)" in df.columns:

                    st.write(
                        "**Requirement (M) values:**"
                    )

                    st.write(
                        df[
                            "Requirement (M)"
                        ]
                        .head(20)
                        .tolist()
                    )


            # ------------------------------------------------
            # Transform
            # ------------------------------------------------

            transformed = transform_vs_bra(
                df
            )


            # ------------------------------------------------
            # Output
            # ------------------------------------------------

            st.subheader(
                "✅ MCU Output"
            )

            st.dataframe(
                transformed,
                use_container_width=True
            )


            # ------------------------------------------------
            # Output statistics
            # ------------------------------------------------

            st.success(
                f"✅ Successfully processed "
                f"{len(df)} input row(s) into "
                f"{len(transformed)} MCU row(s)."
            )


            # ------------------------------------------------
            # Excel Output
            # ------------------------------------------------

            out = excel_to_bytes(
                transformed,
                sheet_name="MCU"
            )


            # ------------------------------------------------
            # Download
            # ------------------------------------------------

            st.download_button(
                "📥 Download MCU - VS Bra.xlsx",
                data=out,
                file_name="MCU_VS_Bra.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )


        # ----------------------------------------------------
        # Error Handling
        # ----------------------------------------------------

        except Exception as e:

            st.error(
                f"❌ Error processing VS Bra file: {e}"
            )

            # Additional technical details
            with st.expander(
                "🔧 Technical Error Details"
            ):

                st.exception(e)
