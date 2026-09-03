# ============================================================
# brands/vs_bra.py
# ============================================================

import streamlit as st
import pandas as pd
from io import BytesIO


# ============================================================
# PAGE NAME
# ============================================================

name = "VS Bra - Bucket 01"


# ============================================================
# EXCEL OUTPUT
# ============================================================

def excel_to_bytes(df: pd.DataFrame, sheet_name="MCU"):

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name
        )

    buffer.seek(0)

    return buffer


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

def clean_columns(df):

    df = df.copy()

    cleaned_columns = []

    for column in df.columns:

        column = str(column)

        column = (
            column
            .replace("\xa0", " ")
            .replace("\u200b", "")
            .replace("–", "-")
            .replace("—", "-")
            .strip()
        )

        # Remove duplicate spaces
        column = " ".join(column.split())

        cleaned_columns.append(column)

    df.columns = cleaned_columns

    return df


# ============================================================
# CLEAN CELL VALUES
# ============================================================

def clean_cell_values(df):

    df = df.copy()

    for column in df.columns:

        # Only clean text/object columns
        if (
            df[column].dtype == "object"
            or pd.api.types.is_string_dtype(df[column])
        ):

            df[column] = (
                df[column]
                .fillna("")
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

            # Convert fake missing values to blank
            df[column] = df[column].replace(
                {
                    "nan": "",
                    "NaN": "",
                    "None": "",
                    "NaT": ""
                }
            )

    return df


# ============================================================
# PARSE DATE
# ============================================================

def parse_exmill_date(series):

    # First attempt
    parsed = pd.to_datetime(
        series,
        errors="coerce"
    )

    # Retry failed values using mixed format
    failed = parsed.isna()

    if failed.any():

        try:

            retry = pd.to_datetime(
                series[failed],
                errors="coerce",
                format="mixed"
            )

            parsed.loc[failed] = retry

        except Exception:
            pass

    return parsed


# ============================================================
# TRANSFORM VS BRA
# ============================================================

def transform_vs_bra(df):

    # ========================================================
    # 1. COPY
    # ========================================================

    df = df.copy()


    # ========================================================
    # 2. CLEAN COLUMN NAMES
    # ========================================================

    df = clean_columns(df)


    # ========================================================
    # 3. CLEAN CELL VALUES
    # ========================================================

    df = clean_cell_values(df)


    # ========================================================
    # 4. REQUIRED COLUMNS
    # ========================================================

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


    # ========================================================
    # 5. VALIDATE REQUIRED COLUMNS
    # ========================================================

    missing_columns = [
        column
        for column in REQUIRED
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "❌ Missing required column(s):\n\n"
            + "\n".join(
                f"- {column}"
                for column in missing_columns
            )
            + "\n\nDetected columns:\n"
            + ", ".join(
                str(column)
                for column in df.columns
            )
        )


    # ========================================================
    # 6. CHECK INPUT DATA
    # ========================================================

    if df.empty:

        raise ValueError(
            "❌ The uploaded Excel file contains no data."
        )


    # ========================================================
    # 7. SAVE ORIGINAL DATE VALUES
    # ========================================================

    original_dates = (
        df["REQ. Ex-mill Date"]
        .copy()
    )


    # ========================================================
    # 8. PARSE EX-MILL DATE
    # ========================================================

    df["REQ. Ex-mill Date"] = parse_exmill_date(
        df["REQ. Ex-mill Date"]
    )


    # ========================================================
    # 9. IDENTIFY INVALID DATES
    # ========================================================

    invalid_dates = (
        df["REQ. Ex-mill Date"]
        .isna()
    )


    # ========================================================
    # 10. SHOW INVALID DATES
    # ========================================================

    if invalid_dates.any():

        invalid_values = (
            original_dates[
                invalid_dates
            ]
            .astype(str)
            .tolist()
        )

        st.warning(
            f"⚠️ {int(invalid_dates.sum())} row(s) "
            "have an invalid REQ. Ex-mill Date."
        )

        with st.expander(
            "View invalid date values"
        ):

            st.write(
                invalid_values
            )


    # ========================================================
    # 11. REMOVE INVALID DATE ROWS
    # ========================================================

    df = df.loc[
        ~invalid_dates
    ].copy()


    # ========================================================
    # 12. CHECK DATA AFTER DATE FILTER
    # ========================================================

    if df.empty:

        raise ValueError(
            "❌ All rows were removed because "
            "REQ. Ex-mill Date could not be parsed."
        )


    # ========================================================
    # 13. CREATE MCU MONTH
    # ========================================================

    df["MCU Month"] = (
        df["REQ. Ex-mill Date"]
        .dt.strftime("%b-%y")
    )


    # ========================================================
    # 14. CLEAN MCU MONTH
    # ========================================================

    df["MCU Month"] = (
        df["MCU Month"]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    # ========================================================
    # 15. CHECK MCU MONTH
    # ========================================================

    if (
        df["MCU Month"]
        .eq("")
        .all()
    ):

        raise ValueError(
            "❌ No valid MCU Month could be generated "
            "from REQ. Ex-mill Date."
        )


    # ========================================================
    # 16. CLEAN REQUIREMENT (M)
    # ========================================================

    df["Requirement (M)"] = (
        df["Requirement (M)"]
        .fillna("")
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


    # ========================================================
    # 17. CONVERT REQUIREMENT TO NUMBER
    # ========================================================

    df["Requirement (M)"] = pd.to_numeric(
        df["Requirement (M)"],
        errors="coerce"
    ).fillna(0)


    # ========================================================
    # 18. IDENTITY COLUMNS
    # ========================================================

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


    # ========================================================
    # 19. CLEAN IDENTITY COLUMNS
    # ========================================================

    for column in identity_cols:

        # Fill blanks
        df[column] = df[column].fillna("")

        # Convert to string
        df[column] = (
            df[column]
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

        # Remove fake missing values
        df[column] = df[column].replace(
            {
                "nan": "",
                "NaN": "",
                "None": "",
                "NaT": ""
            }
        )


    # ========================================================
    # 20. DEBUG INFORMATION
    # ========================================================

    with st.expander(
        "🔍 Transformation Debug"
    ):

        st.write(
            "**Rows after cleaning:**",
            len(df)
        )

        st.write(
            "**MCU Months:**",
            df["MCU Month"]
            .unique()
            .tolist()
        )

        st.write(
            "**Requirement (M):**",
            df["Requirement (M)"]
            .tolist()
        )

        st.write(
            "**BS values:**",
            df["BS"]
            .unique()
            .tolist()
        )

        st.write(
            "**Data before transformation:**"
        )

        st.dataframe(
            df.head(50),
            use_container_width=True
        )


    # ========================================================
    # 21. GROUP DATA
    # ========================================================
    #
    # IMPORTANT:
    #
    # We intentionally use groupby + unstack instead of
    # pivot_table.
    #
    # This avoids the problem where pivot_table can remove
    # rows because an identity field is blank.
    #
    # dropna=False ensures blank identity values are retained.
    #
    # ========================================================

    grouped = (
        df
        .groupby(
            identity_cols + ["MCU Month"],
            dropna=False,
            as_index=False
        )["Requirement (M)"]
        .sum()
    )


    # ========================================================
    # 22. CHECK GROUPED DATA
    # ========================================================

    if grouped.empty:

        raise ValueError(
            "❌ No data remains after grouping."
        )


    # ========================================================
    # 23. CREATE MCU MONTH COLUMNS
    # ========================================================

    pivot_df = (
        grouped
        .set_index(
            identity_cols + ["MCU Month"]
        )["Requirement (M)"]
        .unstack(
            "MCU Month",
            fill_value=0
        )
        .reset_index()
    )


    # ========================================================
    # 24. REMOVE INDEX NAME
    # ========================================================

    pivot_df.columns.name = None


    # ========================================================
    # 25. IDENTIFY MONTH COLUMNS
    # ========================================================

    month_cols = [
        column
        for column in pivot_df.columns
        if column not in identity_cols
    ]


    # ========================================================
    # 26. CHECK MONTH COLUMNS
    # ========================================================

    if not month_cols:

        raise ValueError(
            "❌ No MCU month columns were created."
        )


    # ========================================================
    # 27. SORT MONTHS
    # ========================================================
    #
    # This version does NOT use month_pairs.sort().
    #
    # It converts the month names to dates and sorts them
    # safely.
    #
    # ========================================================

    month_dates = {}

    for month in month_cols:

        parsed_month = pd.to_datetime(
            str(month),
            format="%b-%y",
            errors="coerce"
        )

        if not pd.isna(parsed_month):

            month_dates[month] = parsed_month


    # ========================================================
    # 28. SORT VALID MONTHS
    # ========================================================

    ordered_months = [
        month
        for month, _ in sorted(
            month_dates.items(),
            key=lambda item: item[1]
        )
    ]


    # ========================================================
    # 29. HANDLE UNPARSED MONTHS
    # ========================================================

    unparsed_months = [
        month
        for month in month_cols
        if month not in month_dates
    ]

    ordered_months.extend(
        unparsed_months
    )


    # ========================================================
    # 30. FINAL COLUMN ORDER
    # ========================================================

    pivot_df = pivot_df[
        identity_cols + ordered_months
    ]


    # ========================================================
    # 31. FINAL CHECK
    # ========================================================

    if pivot_df.empty:

        raise ValueError(
            "❌ Pivot produced an empty output."
        )


    # ========================================================
    # 32. RETURN
    # ========================================================

    return pivot_df


# ============================================================
# STREAMLIT RENDER
# ============================================================

def render():

    st.header(
        "VS Bra — Buy Sheet → MCU Format"
    )


    # ========================================================
    # FILE UPLOADER
    # ========================================================

    file = st.file_uploader(
        "Upload VS Bra Buy Sheet",
        type=[
            "xlsx",
            "xls",
            "csv"
        ],
        key="vsbra_file"
    )


    # ========================================================
    # PROCESS FILE
    # ========================================================

    if file:

        try:

            # =================================================
            # READ FILE
            # =================================================

            if file.name.lower().endswith(".csv"):

                df = pd.read_csv(
                    file
                )

            else:

                df = pd.read_excel(
                    file
                )


            # =================================================
            # CHECK FILE
            # =================================================

            if df.empty:

                st.error(
                    "❌ The uploaded file is empty."
                )

                return


            # =================================================
            # INPUT PREVIEW
            # =================================================

            st.subheader(
                "📄 Input Preview"
            )

            st.dataframe(
                df.head(20),
                use_container_width=True
            )


            # =================================================
            # FILE INFORMATION
            # =================================================

            with st.expander(
                "📋 File Information"
            ):

                st.write(
                    "**File:**",
                    file.name
                )

                st.write(
                    "**Rows:**",
                    len(df)
                )

                st.write(
                    "**Columns:**",
                    len(df.columns)
                )

                st.write(
                    "**Detected columns:**"
                )

                st.write(
                    list(df.columns)
                )


            # =================================================
            # TRANSFORM
            # =================================================

            transformed = transform_vs_bra(
                df
            )


            # =================================================
            # OUTPUT
            # =================================================

            st.subheader(
                "✅ MCU Output"
            )

            st.dataframe(
                transformed,
                use_container_width=True
            )


            # =================================================
            # SUCCESS MESSAGE
            # =================================================

            st.success(
                f"✅ Successfully processed "
                f"{len(df)} input row(s) into "
                f"{len(transformed)} MCU row(s)."
            )


            # =================================================
            # CREATE EXCEL
            # =================================================

            output_file = excel_to_bytes(
                transformed,
                sheet_name="MCU"
            )


            # =================================================
            # DOWNLOAD
            # =================================================

            st.download_button(
                label="📥 Download MCU - VS Bra.xlsx",
                data=output_file,
                file_name="MCU_VS_Bra.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )


        # =====================================================
        # ERROR HANDLING
        # =====================================================

        except Exception as e:

            st.error(
                f"❌ Error processing VS Bra file: {e}"
            )

            with st.expander(
                "🔧 Technical Error Details"
            ):

                st.exception(e)
