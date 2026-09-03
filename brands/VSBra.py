import streamlit as st
import pandas as pd
from io import BytesIO

name = "VS Bra - Bucket 01"

# HELPER - GENERATE EXCEL

def excel_to_bytes(df: pd.DataFrame, sheet_name="Sheet1"):
    """
    Convert a dataframe into an Excel file in memory.
    """

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

# CLEAN COLUMN NAMES
def clean_columns(df):
    """
    Clean Excel column names.

    Handles:
    - Non-breaking spaces
    - En dash
    - Em dash
    - Leading/trailing spaces
    - Multiple spaces
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

        # Convert multiple spaces to one
        cleaned = " ".join(cleaned.split())

        new_cols[c] = cleaned

    df.rename(
        columns=new_cols,
        inplace=True
    )

    return df
# CLEAN CELL VALUES
def clean_cell_values(df):
    """
    Clean text values inside the dataframe.

    This is important because Excel may contain invisible
    characters or non-breaking spaces inside cells.
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

            # Convert string representations of missing values
            # back to blank strings
            df[col] = df[col].replace(
                {
                    "nan": "",
                    "NaN": "",
                    "None": "",
                    "NaT": ""
                }
            )

    return df
# DATE PARSING

def parse_exmill_date(series):
    """
    Robustly parse REQ. Ex-mill Date.

    Supports:
    - Excel datetime values
    - Standard dates
    - MM/DD/YYYY
    - Mixed date formats
    """

    # First attempt
    parsed = pd.to_datetime(
        series,
        errors="coerce"
    )

    # Retry failed values using mixed format
    failed = (
        parsed.isna()
        & series.notna()
    )

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

# TRANSFORMATION LOGIC
def transform_vs_bra(df):

    df = df.copy()
    df = clean_columns(df)
    df = clean_cell_values(df)

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
            + "Columns detected in the uploaded file:\n"
            + ", ".join(
                map(str, df.columns)
            )
        )

    if df.empty:

        raise ValueError(
            "❌ The uploaded Excel file contains no data rows."
        )

    original_dates = (
        df["REQ. Ex-mill Date"]
        .copy()
    )

    df["REQ. Ex-mill Date"] = parse_exmill_date(
        df["REQ. Ex-mill Date"]
    )

    invalid_dates = (
        df["REQ. Ex-mill Date"]
        .isna()
    )
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

    df = df.loc[
        ~invalid_dates
    ].copy()

    if df.empty:

        raise ValueError(
            "❌ No valid rows remain after processing "
            "'REQ. Ex-mill Date'.\n\n"
            "Please check the date values in the uploaded "
            "Excel file."
        )

    df["MCU Month"] = (
        df["REQ. Ex-mill Date"]
        .dt.strftime("%b-%y")
    )


    if (
        df["MCU Month"]
        .isna()
        .all()
    ):

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
    # 17. Replace invalid quantities with 0
    # --------------------------------------------------------

    df["Requirement (M)"] = (
        df["Requirement (M)"]
        .fillna(0)
    )


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
    # 19. IMPORTANT FIX FOR BLANK VALUES
    # ========================================================
    #
    # Your second Excel has:
    #
    # BS
    # -
    # -
    # -
    #
    # Pandas pivot_table can drop rows where an index field
    # is NaN.
    #
    # Therefore we explicitly convert missing identity values
    # into blank strings.
    #
    # ========================================================

    for col in identity_cols:

        # Convert missing values to blank
        df[col] = df[col].fillna("")

        # Convert everything to string so that values such as
        # Dept Code, Style, etc. remain consistent
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(
                "\xa0",
                " ",
                regex=False
            )
            .str.strip()
        )

        # Clean literal missing values
        df[col] = df[col].replace(
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
            "**Rows before pivot:**",
            len(df)
        )

        st.write(
            "**MCU Month values:**",
            df["MCU Month"]
            .unique()
            .tolist()
        )

        st.write(
            "**Requirement (M) values:**",
            df["Requirement (M)"]
            .tolist()
        )

        st.write(
            "**Blank BS rows:**",
            int(
                (
                    df["BS"]
                    .astype(str)
                    .str.strip()
                    == ""
                ).sum()
            )
        )

        st.write(
            "**Data before pivot:**"
        )

        st.dataframe(
            df.head(20),
            use_container_width=True
        )


    # ========================================================
    # 21. PIVOT MCU MONTHS
    # ========================================================

    pivot_df = df.pivot_table(
        index=identity_cols,
        columns="MCU Month",
        values="Requirement (M)",
        aggfunc="sum",
        fill_value=0,

        # VERY IMPORTANT
        # Keep rows even when an identity field is blank
        dropna=False
    ).reset_index()


    # ========================================================
    # 22. Remove pivot column name
    # ========================================================

    pivot_df.columns.name = None


    # ========================================================
    # 23. Identify month columns
    # ========================================================

    month_cols = [
        c
        for c in pivot_df.columns
        if c not in identity_cols
    ]


    # ========================================================
    # 24. Sort MCU months chronologically
    # ========================================================

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

        # Keep only successfully parsed months
        month_pairs = [
            pair
            for pair in month_pairs
            if not pd.isna(pair[0])
        ]

        # Sort chronologically
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


    # ========================================================
    # 25. Final validation
    # ========================================================

    if pivot_df.empty:

        raise ValueError(
            "❌ Pivot produced an empty output.\n\n"
            "Please check the uploaded data."
        )


    # ========================================================
    # 26. Return transformed dataframe
    # ========================================================

    return pivot_df


# ============================================================
# STREAMLIT PAGE RENDERING
# ============================================================

def render():

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    st.header(
        "VS Bra — Buy Sheet → MCU Format"
    )


    # --------------------------------------------------------
    # File uploader
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
    # Process uploaded file
    # --------------------------------------------------------

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
            # INPUT VALIDATION
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
            # FILE DEBUG INFORMATION
            # =================================================

            with st.expander(
                "🔍 File Debug Information"
            ):

                st.write(
                    "**File name:**",
                    file.name
                )

                st.write(
                    "**Input rows:**",
                    len(df)
                )

                st.write(
                    "**Input columns:**",
                    len(df.columns)
                )

                st.write(
                    "**Detected columns:**"
                )

                st.write(
                    list(df.columns)
                )


                # ---------------------------------------------
                # Show date values
                # ---------------------------------------------

                if (
                    "REQ. Ex-mill Date"
                    in df.columns
                ):

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


                # ---------------------------------------------
                # Show Requirement values
                # ---------------------------------------------

                if (
                    "Requirement (M)"
                    in df.columns
                ):

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


                # ---------------------------------------------
                # Show BS values
                # ---------------------------------------------

                if "BS" in df.columns:

                    st.write(
                        "**BS values:**"
                    )

                    st.write(
                        df[
                            "BS"
                        ]
                        .head(20)
                        .tolist()
                    )


            # =================================================
            # TRANSFORM DATA
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
            # OUTPUT STATISTICS
            # =================================================

            st.success(
                f"✅ Successfully processed "
                f"{len(df)} input row(s) into "
                f"{len(transformed)} MCU row(s)."
            )


            # =================================================
            # GENERATE EXCEL
            # =================================================

            out = excel_to_bytes(
                transformed,
                sheet_name="MCU"
            )


            # =================================================
            # DOWNLOAD BUTTON
            # =================================================

            st.download_button(
                "📥 Download MCU - VS Bra.xlsx",
                data=out,
                file_name="MCU_VS_Bra.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )


        # =====================================================
        # ERROR HANDLING
        # =================================================

        except Exception as e:

            st.error(
                f"❌ Error processing VS Bra file: {e}"
            )

            with st.expander(
                "🔧 Technical Error Details"
            ):

                st.exception(e)
