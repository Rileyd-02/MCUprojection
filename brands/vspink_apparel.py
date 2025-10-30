# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Display name in sidebar
name = "VSPink Apparel"

# -----------------------------
# Helper: export Excel
# -----------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

# -----------------------------
# Transformation: Buy Sheet → MCU
# -----------------------------
def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform VSPink Apparel Buy Sheet → MCU Format.
    - Converts EX-mill to Month (e.g., Nov-25)
    - Ensures Qty is numeric
    - Pivots Month columns
    - Preserves other metadata
    """

    # Skip blank first row if present
    if df.iloc[0].isna().all():
        df = df.iloc[1:].copy()

    # Normalize column names
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")

    # Detect columns
    def find_column(key_words):
        for kw in key_words:
            for col in df.columns:
                if kw.lower() in col.lower():
                    return col
        return None

    article_col = find_column(["article"])
    exmill_col = find_column(["ex-mill", "ex mill", "exmill"])
    qty_col = find_column(["qty", "qty (m)"])

    if not article_col or not exmill_col or not qty_col:
        raise ValueError("Could not detect required columns: Article, EX-mill, Qty.")

    # Parse EX-mill → datetime (if not already)
    if not pd.api.types.is_datetime64_any_dtype(df[exmill_col]):
        df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # Drop rows without valid EX-mill or Article
    df = df.dropna(subset=[exmill_col, article_col])

    if df.empty:
        return pd.DataFrame()

    # Create Month label
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Clean Qty and convert to numeric
    df[qty_col] = (
        df[qty_col].astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Keep metadata columns (everything except Qty, EX-mill, Month)
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]

    # Group by metadata + Month
    grouped = df.groupby(meta_cols + ["Month"], as_index=False)[qty_col].sum()

    # Pivot Month → columns
    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="Month",
        values=qty_col,
        fill_value=0
    ).reset_index()

    # Sort month columns chronologically
    month_cols = [c for c in pivot_df.columns if c not in meta_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        order = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[meta_cols + order]

    # Flatten column names
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

# -----------------------------
# Streamlit UI
# -----------------------------
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet",
        type=["xlsx", "xls", "csv"],
        key="vspink_apparel_file"
    )

    if uploaded:
        try:
            # Read file
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded, header=1)  # skip first blank row
            else:
                df = pd.read_excel(uploaded, header=1)  # skip first blank row

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            # Transform
            transformed_df = transform_vspink_apparel(df)

            if transformed_df.empty:
                st.warning("No valid rows after parsing EX-mill dates or Article values.")
                return

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed_df.head())

            out_bytes = excel_to_bytes(transformed_df, sheet_name="MCU")

            st.download_button(
                label="📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")
