# brands/vspink_apparel.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "VSPink Apparel"

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output

def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:
    # Skip first blank row if present
    if df.iloc[0].isna().all():
        df = df.iloc[1:].copy()
    # Normalize column names
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")

    # Detect columns
    col_map = {c.lower().replace(" ", ""): c for c in df.columns}
    def find_column(possible_names):
        for name in possible_names:
            key = name.lower().replace(" ", "")
            if key in col_map:
                return col_map[key]
        return None

    article_col = find_column(["Article"])
    exmill_col = find_column(["EX-mill", "exmill", "ex mill"])
    qty_col = find_column(["qty", "qty(m)", "qty (m)"])

    if not article_col or not exmill_col or not qty_col:
        raise ValueError(f"Could not detect required columns. Found: {df.columns.tolist()}")

    # Convert EX-mill to datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")
    df = df.dropna(subset=[exmill_col, article_col])

    if df.empty:
        return pd.DataFrame()

    # Month column
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # Clean Qty
    df[qty_col] = df[qty_col].astype(str).str.replace(",", "").str.strip()
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Metadata
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]

    grouped = df.groupby(meta_cols + ["Month"], as_index=False)[qty_col].sum()
    pivot_df = grouped.pivot_table(index=meta_cols, columns="Month", values=qty_col, fill_value=0).reset_index()

    # Sort month columns
    month_cols = [c for c in pivot_df.columns if c not in meta_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        order = [m for _, m in sorted(zip(parsed, month_cols))]
        pivot_df = pivot_df[meta_cols + order]

    pivot_df.columns = [str(c) for c in pivot_df.columns]
    return pivot_df

def render():
    st.header("VSPink Apparel — Buy Sheet → MCU Format")
    uploaded = st.file_uploader("Upload VSPink Apparel Buy Sheet", type=["xlsx", "xls", "csv"], key="vspink_apparel_file")
    if uploaded:
        try:
            # read with second row as header
            if str(uploaded).lower().endswith(".csv") or uploaded.type == "text/csv":
                df = pd.read_csv(uploaded, header=1)
            else:
                df = pd.read_excel(uploaded, header=1)
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
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Error processing VSPink Apparel file: {e}")

