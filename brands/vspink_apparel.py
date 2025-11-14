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


def find_column_loose(df, keywords):
    """
    Find a column using loose contains matching.
    Example: “EX Mill Date”, “Ex-mill”, “RM Exmill” will match keywords ["ex", "mill"]
    """
    cols = df.columns
    for col in cols:
        low = col.lower().replace(" ", "")
        if all(k in low for k in keywords):
            return col
    return None


def transform_vspink_apparel(df: pd.DataFrame) -> pd.DataFrame:

    # skip blank first row
    if df.iloc[0].isna().all():
        df = df.iloc[1:].copy()

    # normalize names
    df.columns = df.columns.str.strip().str.replace("\n", " ").str.replace("\r", " ")

    # 🔍 detect columns using loose matching
    article_col = find_column_loose(df, ["article"]) \
                  or find_column_loose(df, ["style"]) \
                  or find_column_loose(df, ["material"]) \
                  or find_column_loose(df, ["sku"])

    exmill_col = find_column_loose(df, ["ex", "mill"]) \
                 or find_column_loose(df, ["exmill"]) \
                 or find_column_loose(df, ["rm", "mill"]) \
                 or find_column_loose(df, ["rm", "ex"])

    qty_col = find_column_loose(df, ["qty"]) or find_column_loose(df, ["quantity"])

    if not article_col or not exmill_col or not qty_col:
        raise ValueError(
            f"❌ Could not detect required columns.\n"
            f"Detected columns: {df.columns.tolist()}"
        )

    # convert ex-mill to datetime
    df[exmill_col] = pd.to_datetime(df[exmill_col], errors="coerce")

    # drop rows with missing dates or missing article
    df = df.dropna(subset=[exmill_col, article_col])

    if df.empty:
        return pd.DataFrame()

    # create month field
    df["Month"] = df[exmill_col].dt.strftime("%b-%y")

    # convert qty
    df[qty_col] = (
        df[qty_col].astype(str)
        .str.replace(",", "")
        .str.extract("(\d+\.?\d*)", expand=False)
    )

    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # metadata
    meta_cols = [c for c in df.columns if c not in [qty_col, exmill_col, "Month"]]

    # group + pivot
    grouped = df.groupby(meta_cols + ["Month"], as_index=False)[qty_col].sum()

    pivot_df = grouped.pivot_table(
        index=meta_cols,
        columns="Month",
        values=qty_col,
        fill_value=0
    ).reset_index()

    # sort months
    month_cols = [c for c in pivot_df.columns if c not in meta_cols]
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
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded, header=1)
            else:
                df = pd.read_excel(uploaded, header=1)

            st.subheader("📄 Input Preview")
            st.dataframe(df.head())

            transformed = transform_vspink_apparel(df)

            if transformed.empty:
                st.warning("⚠️ No valid rows found after EX-mill + Article filtering.")
                return

            st.subheader("✅ Transformed Output")
            st.dataframe(transformed.head())

            out_bytes = excel_to_bytes(transformed, sheet_name="MCU")

            st.download_button(
                "📥 Download MCU - VSPink Apparel.xlsx",
                data=out_bytes,
                file_name="MCU_VSPink_Apparel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
