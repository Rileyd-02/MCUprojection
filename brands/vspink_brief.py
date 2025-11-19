# brands/vspink_brief.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Display name in sidebar
name = "VSPink Brief - Bucket 03"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def transform_vspink_brief(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform VSPink Brief Buy Sheet → MCU Format.
    - Converts EX-mill to datetime and to Month label (e.g. "Oct-25")
    - Ensures Qty (m) is numeric
    - Pivots so each Month becomes a column with Qty sums
    - Preserves other metadata columns (Customer, Supplier, Article, etc.)
    """

    # normalize column names
    df = df.copy()
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")

    # Detect key columns flexibly (case-insensitive)
    col_lower = {c.lower(): c for c in df.columns}
    # required keys - try exact names then fall back to contains
    def find_column(key_words):
        for k in key_words:
            if k in col_lower:
                return col_lower[k]
        # fallback: find first column containing any word
        for col in df.columns:
            low = col.lower()
            for kw in key_words:
                if kw in low:
                    return col
        return None

    article_col = find_column(["article"])
    exmill_col = find_column(["ex-mill", "ex mill", "exmill"])
    qty_col = find_column(["qty", "qty (m)", "qty (m)", "qty (m)".lower()])

    if article_col is None or exmill_col is None or qty_col is None:
        raise ValueError("Could not detect required columns. Ensure file has 'Article', 'EX-mill' and 'Qty (m)' columns.")

    # Parse EX-mill -> datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # Drop rows without a valid ex-mill date or without an article
    df = df.dropna(subset=[exmill_col, article_col])

    if df.empty:
        # Nothing to transform
        return pd.DataFrame()

    # Create Month label (e.g., Oct-25). Use consistent format.
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Ensure Qty is numeric (remove commas / whitespace)
    df[qty_col] = df[qty_col].astype(str).str.replace(",", "", regex=False).str.strip()
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Decide metadata columns to preserve in the pivot index:
    # keep all cols except Qty and EX-mill and Month (we'll pivot Month)
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]

    # Pivot: meta_cols as index, Month as columns, Qty as values
    # If meta_cols is empty (unlikely), pivot only by article_col
    if len(meta_cols) == 0:
        index_cols = [article_col]
    else:
        index_cols = meta_cols

    grouped = (
        df.groupby(index_cols + ["Month"], dropna=False, as_index=False)[qty_col]
          .sum()
    )

    pivot_df = grouped.pivot_table(
        index=index_cols,
        columns="Month",
        values=qty_col,
        aggfunc="sum",
        fill_value=0
    )

    # Reset index so metadata are columns again
    pivot_df = pivot_df.reset_index()

    # Make sure month columns are sorted chronologically
    month_cols = [c for c in pivot_df.columns if c not in index_cols]
    if month_cols:
        # parse month columns back to dates for sorting
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        order = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[index_cols + order]

    # Flatten column names to simple strings (in case)
    pivot_df.columns = [str(c) for c in pivot_df.columns]

    return pivot_df

# Streamlit UI
def render():
    st.header("VSPink Brief — Buy Sheet → MCU Format")

    uploaded = st.file_uploader("Upload VSPink Brief Buy Sheet", type=["xlsx", "xls", "csv"], key="vspink_brief_file")

    if uploaded:
        try:
            # allow CSV as well for quick testing
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed_df = transform_vspink_brief(df)

            if transformed_df.empty:
                st.warning("No valid rows after parsing EX-mill dates or Article values.")
                return

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

