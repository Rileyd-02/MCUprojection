import pandas as pd
from io import BytesIO

def excel_to_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1"):
    """Return bytes buffer of an Excel file for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output