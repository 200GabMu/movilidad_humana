"""Exportación a Excel (misma salida que la app original)."""

from __future__ import annotations

import io
import re

import pandas as pd

from .consolidacion import COLS_TRAZABILIDAD


_RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}( 00:00:00)?$")


def _fechas_reales(df: pd.DataFrame) -> pd.DataFrame:
    """En las columnas de fecha, los textos 'AAAA-MM-DD' se escriben como
    fechas de Excel; otros textos ('No aplica') se quedan como están."""
    df = df.copy()
    for col in df.columns:
        if "FECHA" in str(col).upper() and not pd.api.types.is_datetime64_any_dtype(df[col]) and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].map(
                lambda x: pd.Timestamp(x) if isinstance(x, str) and _RE_ISO.match(x) else x
            )
    return df


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "CONSOLIDADO") -> bytes:
    df = _fechas_reales(df)
    output = io.BytesIO()
    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        date_format="yyyy-mm-dd",
        datetime_format="yyyy-mm-dd",
    ) as writer:
        df.to_excel(writer, index=False, startrow=1, header=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]

        for col_idx, col_name in enumerate(df.columns):
            c_str = str(col_name)
            if c_str.startswith("Columna_") or c_str.startswith("Unnamed:"):
                header_val = ""
            elif c_str in COLS_TRAZABILIDAD:
                header_val = c_str
            else:
                header_val = re.sub(r"__\d+$", "", c_str)

            worksheet.write(0, col_idx, header_val)

            if not df.empty:
                col_data_len = df.iloc[:, col_idx].apply(lambda x: len(str(x)) if pd.notna(x) else 0).max()
            else:
                col_data_len = 0
            max_len = max(len(header_val), int(col_data_len))
            ancho = min(max_len + 2, 40)
            if pd.api.types.is_datetime64_any_dtype(df[col_name]):
                ancho = max(ancho, 12)
            worksheet.set_column(col_idx, col_idx, ancho)

    return output.getvalue()
