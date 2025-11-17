# brands/pink_bra.py
import streamlit as st
import pandas as pd
from io import BytesIO

name = "Pink Bra"

# -------------------------
# Helpers
# -------------------------
def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "MCU"):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    out.seek(0)
    return out

def deep_clean_colname(c):
    if pd.isna(c):
        return ""
    s = str(c)
    # remove common hidden spaces and normalize
    s = s.replace("\u00A0", " ")  # NBSP
    s = s.replace("\u202F", "")   # narrow NBSP
    s = s.replace("\t", " ")
    s = s.replace("\n", " ")
    s = s.replace("–", "-").replace("—", "-")
    s = s.strip()
    return s

def normalize_map(columns):
    """
    Return mapping original_col -> normalized_key
    normalized_key is lowercase with non-alphanumeric removed except underscores
    """
    mapping = {}
    for c in columns:
        cleaned = deep_clean_colname(c)
        key = (
            cleaned.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
            .replace("/", "_")
        )
        # collapse consecutive underscores
        key = "_".join([p for p in key.split("_") if p != ""])
        mapping[c] = key
    return mapping

def find_best_col(normalized_map, keywords_any=None, keywords_all=None):
    """
    Find best original column name from normalized_map whose normalized value contains
    any of keywords_any or all of keywords_all. Returns original column or None.
    """
    # prefer keywords_all match (all present)
    if keywords_all:
        for orig, norm in normalized_map.items():
            if all(k in norm for k in keywords_all):
                return orig
    if keywords_any:
        for orig, norm in normalized_map.items():
            for k in keywords_any:
                if k in norm:
                    return orig
    return None

# -------------------------
# Transform logic
# -------------------------
def transform_pink_bra(file) -> pd.DataFrame:
    # Read file (allow csv/xlsx)
    if hasattr(file, "read") and getattr(file, "name", "").lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, header=0)

    # Clean column display names (keep originals)
    orig_cols = list(df.columns)
    col_map = normalize_map(orig_cols)  # orig -> normalized key

    # Attempt to detect the required columns
    # RM Ex Mill (user said column U RM Ex Mill). Look for patterns including 'rm','ex','mill'
    rm_ex_candidates_all = ["rm", "ex", "mill"]
    rm_ex_candidates_any = ["rmex", "rm_ex", "rmexmill", "rm_ex_mill", "exmill", "ex_mill", "rmex.mill", "rm_ex.mill"]
    rm_ex_col = find_best_col(col_map, keywords_any=rm_ex_candidates_any, keywords_all=rm_ex_candidates_all)
    # fallback: any column containing 'ex' and 'mill'
    if rm_ex_col is None:
        rm_ex_col = find_best_col(col_map, keywords_all=["ex", "mill"])
    # Qty detection (user explicitly said use Qty column (y))
    qty_col = find_best_col(col_map, keywords_any=["qty", "quantity", "requirement", "require"])
    # Article No
    article_col = find_best_col(col_map, keywords_any=["article", "article_no", "articleno", "article_no", "article_number"])
    # Supplier
    supplier_col = find_best_col(col_map, keywords_any=["supplier", "vendor"])
    # Measurement
    measurement_col = find_best_col(col_map, keywords_any=["measurement", "measure"])
    # Supplier Country
    supplier_country_col = find_best_col(col_map, keywords_any=["supplier_country", "suppliercoo", "country"])
    # Type of Cons1
    type_of_cons_col = find_best_col(col_map, keywords_any=["type_of_cons", "typeofcons", "type_of_cons1", "type_of_const", "type_of_cons1"])
    # Plant
    plant_col = find_best_col(col_map, keywords_any=["plant", "production_plant", "plant_name"])

    # Validate essential detections: rm_ex_col, qty_col, article_col, supplier_col
    missing = []
    if rm_ex_col is None:
        missing.append("RM Ex Mill (ex: 'RM Ex Mill', 'RM EX.MILL GC', etc.)")
    if qty_col is None:
        missing.append("Qty (use the 'Qty' column)")
    if article_col is None:
        missing.append("Article No (article number)")
    if supplier_col is None:
        missing.append("Supplier (supplier name)")

    if missing:
        raise ValueError("Could not detect required columns: " + "; ".join(missing) + f"\nDetected columns: {orig_cols}")

    # For clarity: map to canonical variable names
    rm_col = rm_ex_col
    qty_col = qty_col
    article_col = article_col
    supplier_col = supplier_col
    measurement_col = measurement_col
    supplier_country_col = supplier_country_col
    type_of_cons_col = type_of_cons_col
    plant_col = plant_col

    # Make sure cols exist in df (they are original names)
    # Convert RM Ex Mill to datetime robustly
    df[rm_col] = pd.to_datetime(df[rm_col], errors="coerce")

    # Ensure qty numeric cleaning
    df[qty_col] = df[qty_col].astype(str).str.replace(",", "").str.replace("\u00A0", "").str.strip()
    df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)

    # Drop rows without valid RM Ex Mill or zero qty -> skip zero rows
    df = df[df[rm_col].notna() & (df[qty_col] != 0)]
    if df.empty:
        raise ValueError("After parsing dates/qty there are no valid rows to process.")

    # Build MCU Month label
    df["_MCU_MonthDate"] = df[rm_col]
    df["_MCU_Month"] = df["_MCU_MonthDate"].dt.strftime("%b-%y")  # e.g., Nov-25

    # Identity columns (ensure present, create empty if missing)
    identity_cols = []
    def ensure_col(orig_name, fallback_key):
        if orig_name and orig_name in df.columns:
            identity_cols.append(orig_name)
        else:
            # create empty col with fallback display name
            df[fallback_key] = ""
            identity_cols.append(fallback_key)

    ensure_col(supplier_col, "Supplier")
    ensure_col(article_col, "Article No")
    ensure_col(measurement_col, "Measurement")
    ensure_col(supplier_country_col, "Supplier Country")
    ensure_col(type_of_cons_col, "Type of Cons1")
    ensure_col(plant_col, "Plant")

    # Group by identity + month and sum qty
    grouped = (
        df.groupby(identity_cols + ["_MCU_Month"], dropna=False, as_index=False)[qty_col]
        .sum()
        .rename(columns={qty_col: "Qty"})
    )

    # Pivot wide
    pivot = grouped.pivot_table(
        index=identity_cols,
        columns="_MCU_Month",
        values="Qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Flatten columns
    pivot.columns.name = None
    pivot.columns = [str(c) for c in pivot.columns]

    # Reorder month columns chronologically
    month_cols = [c for c in pivot.columns if c not in identity_cols]
    if month_cols:
        parsed = pd.to_datetime(month_cols, format="%b-%y", errors="coerce")
        # create list of (parsed_date, col) then sort
        col_order = [col for _, col in sorted(zip(parsed, month_cols), key=lambda x: (pd.NaT if pd.isna(x[0]) else x[0]))]
        # Put identity_cols first then ordered months
        final_cols = identity_cols + col_order
        pivot = pivot.loc[:, final_cols]

    # Rename identity columns to clean display names
    rename_display = {
        supplier_col: "Supplier",
        article_col: "Article No",
    }
    if measurement_col:
        rename_display[measurement_col] = "Measurement"
    if supplier_country_col:
        rename_display[supplier_country_col] = "Supplier Country"
    if type_of_cons_col:
        rename_display[type_of_cons_col] = "Type of Cons1"
    if plant_col:
        rename_display[plant_col] = "Plant"

    pivot = pivot.rename(columns=rename_display)

    return pivot

# -------------------------
# Streamlit Page
# -------------------------
def render():
    st.header("Pink Bra — Buy Sheet → MCU Format")
    st.markdown("Upload the Pink Bra buy sheet. The app will pivot the RM Ex Mill (date) into month columns and place Qty into the corresponding month column.")

    uploaded = st.file_uploader("Upload Pink Bra file (xlsx, xls, csv)", type=["xlsx", "xls", "csv"], key="pink_bra_file")

    if not uploaded:
        return

    try:
        df_out = transform_pink_bra(uploaded)
        st.subheader("Preview")
        st.dataframe(df_out.head())

        out_bytes = excel_to_bytes(df_out, sheet_name="MCU")
        st.download_button("📥 Download MCU - Pink Bra.xlsx", data=out_bytes, file_name="MCU_Pink_Bra.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"❌ Error: {e}")
