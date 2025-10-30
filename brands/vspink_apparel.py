# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Display name in sidebar
name = "VSPink Apparel"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform VSPink Apparel Buy Sheet → MCU Format.
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

    def find_column(key_words):
        for k in key_words:
            if k in col_lower:
                return col_lower[k]
        for col in df.columns:
            low = col.lower()
            for kw in key_words:
                if kw in low:
                    return col
        return None

    article_col = find_column(["article"])
    exmill_col = find_column(["ex-mill", "ex mill", "exmill"])
    qty_col = find_column(["qty", "qty (m)"])

    if article_col is None or exmill_col is None or qty_col is None:
        raise ValueError("Could not detect required columns. Ensure file has 'Article', 'EX-mill' and 'Qty (m)' columns.")

    # Parse EX-mill -> datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # Drop rows without a valid ex-mill date or without an article
    df = df.dropna(subset=[exmill_col, article_col])

    if df.empty:
        return pd.DataFrame()

    # Month label
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Ensure Qty is numeric
    df[qty_col] = df[qty_col].astype(str).str.replace(",", "", regex=False).str.strip()
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Metadata columns (keep all except Qty, EX-mill, Month)
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]
    index_cols = meta_cols if meta_cols else [article_col]

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
    ).reset_index()

    # Sort month columns chronologically
    month_cols = [c for c in pivot_df.columns if c not in index_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        order = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[index_cols + order]

    pivot_df.columns = [str(c) for c in pivot_df.columns]
    return pivot_df

# Streamlit UI
def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")

    uploaded = st.file_uploader(
        "Upload VSPink Apparel Buy Sheet (skip first blank row)", 
        type=["xlsx", "xls", "csv"], key="vspink_apparel_file"
    )

    if uploaded:
        try:
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded, header=1)  # skip first row
            else:
                df = pd.read_excel(uploaded, header=1)  # header in row 2

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

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
