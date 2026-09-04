"""
Columnas derivadas (AÑO, MES, RANGO DE EDAD) y localización robusta de
columnas por nombre.

El Power BI original trabaja con las columnas MES y AÑO al final de la matriz
y con RANGO DE EDAD tal como viene en el formulario (NN · ADOLESCENTE ·
ADULTO · ADULTO MAYOR). Aquí se replican con las mismas etiquetas:
  * AÑO  -> año del nombre del archivo (entero)
  * MES  -> nombre del mes tomado del nombre de la hoja ('ENERO', 'FEBRERO'…)
  * RANGO DE EDAD -> se respeta la del formulario; solo si no existe se
    calcula desde EDAD - AÑOS / FECHA DE NACIMIENTO con esas 4 categorías.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

import pandas as pd

from .consolidacion import COL_ARCHIVO, COL_HOJA, buscar_col, extraer_año

COL_AÑO = "AÑO"
COL_MES = "MES"
COL_RANGO_EDAD = "RANGO DE EDAD"
SIN_DATO = "SIN DATO"

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]
_ALIAS_MES = {"SETIEMBRE": "SEPTIEMBRE"}

# Categorías del formulario (mismas etiquetas que usa el Power BI) y su orden.
RANGOS_EDAD = [
    (0, 11, "NN"),
    (12, 17, "ADOLESCENTE"),
    (18, 64, "ADULTO"),
    (65, 200, "ADULTO MAYOR"),
]
ORDEN_RANGOS = [r[2] for r in RANGOS_EDAD] + [SIN_DATO]

# Filtros del panel (mismo orden que la barra de segmentadores del Power BI).
FILTROS = [
    ("NACIONALIDAD", ("NACIONALIDAD",)),
    ("CIUDAD", ("CIUDAD",)),
    ("RANGO DE EDAD", (COL_RANGO_EDAD,)),
    ("SEXO", ("SEXO",)),
    ("SITUACIÓN MIGRATORIA", ("SITUACI", "MIGRATORIA")),
    ("AÑO", (COL_AÑO,)),
    ("MES", (COL_MES,)),
]


# ── Localización de columnas ────────────────────────────────────────────────

def _clave(texto: str) -> str:
    """Normaliza un encabezado: sin tildes, mayúsculas, un solo espacio."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t).strip().upper()


def resolver_columna(df: pd.DataFrame, nombre: str) -> str | None:
    """Devuelve la columna real que corresponde a `nombre` aunque difiera en
    tildes, mayúsculas o espacios dobles ('SITUACIÓN  MIGRATORIA')."""
    if nombre in df.columns:
        return nombre
    objetivo = _clave(nombre)
    for c in df.columns:
        if _clave(c) == objetivo:
            return c
    # el encabezado con sufijo de duplicado (__1 / .1)
    for c in df.columns:
        if _clave(re.sub(r"(__\d+|\.\d+)$", "", str(c))) == objetivo:
            return c
    # encabezado con ortografía corregida (ACOGIMINETO -> ACOGIMIENTO, etc.)
    from .plantilla import ALIAS_ENCABEZADO, CORRECCIONES_ENCABEZADO  # import tardío: evita ciclo
    for mapa in (CORRECCIONES_ENCABEZADO, ALIAS_ENCABEZADO):
        for original, alias in mapa.items():
            if _clave(original) == objetivo:
                for c in df.columns:
                    if _clave(c) == _clave(alias):
                        return c
    return None


def _col_para_filtro(df: pd.DataFrame, etiqueta: str, palabras: tuple[str, ...]) -> str | None:
    col = resolver_columna(df, etiqueta)
    if col is not None:
        return col
    return buscar_col(df.columns, *palabras)


def columnas_de_filtros(df: pd.DataFrame) -> dict[str, str | None]:
    """{etiqueta del filtro: nombre real de la columna (o None si no existe)}."""
    return {etiqueta: _col_para_filtro(df, etiqueta, palabras) for etiqueta, palabras in FILTROS}


# ── Derivadas ───────────────────────────────────────────────────────────────

def mes_desde_texto(texto: str) -> str | None:
    """'REPORTE MENSUAL SETIEMBRE 2024' -> 'SEPTIEMBRE'."""
    t = _clave(texto)
    for alias, real in _ALIAS_MES.items():
        t = t.replace(alias, real)
    for mes in MESES:
        if mes in t:
            return mes
    m = re.search(r"\b(0?[1-9]|1[0-2])\b", t)  # 'REPORTE MENSUAL 03'
    if m:
        return MESES[int(m.group(1)) - 1]
    return None


def orden_mes(valor: str) -> int:
    v = _clave(valor)
    return MESES.index(v) if v in MESES else 99


def rango_desde_edad(edad) -> str:
    """Acepta 27, '27', '27 AÑOS', '27,5'."""
    m = re.search(r"\d+(?:[.,]\d+)?", str(edad)) if edad is not None else None
    if not m:
        return SIN_DATO
    try:
        e = float(m.group(0).replace(",", "."))
    except ValueError:
        return SIN_DATO
    if pd.isna(e) or e < 0:
        return SIN_DATO
    for lo, hi, etiqueta in RANGOS_EDAD:
        if lo <= e <= hi:
            return etiqueta
    return SIN_DATO


def _edad_desde_fecha(fecha, hoy: date) -> float | None:
    f = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(f):
        return None
    return hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))


def agregar_columnas_derivadas(df: pd.DataFrame, hoy: date | None = None) -> pd.DataFrame:
    """Agrega AÑO, MES y RANGO DE EDAD sin pisar columnas que ya existan."""
    df = df.copy()
    hoy = hoy or date.today()

    if resolver_columna(df, COL_AÑO) is None:
        if COL_ARCHIVO in df.columns:
            df[COL_AÑO] = df[COL_ARCHIVO].map(lambda x: extraer_año(str(x)))
        else:
            df[COL_AÑO] = SIN_DATO

    if resolver_columna(df, COL_MES) is None:
        if COL_HOJA in df.columns:
            df[COL_MES] = df[COL_HOJA].map(lambda x: mes_desde_texto(x) or SIN_DATO)
        else:
            df[COL_MES] = SIN_DATO

    if resolver_columna(df, COL_RANGO_EDAD) is None:
        col_edad = buscar_col(df.columns, "EDAD", "AÑOS")
        col_fecha = buscar_col(df.columns, "FECHA", "NACIMIENTO")
        if col_edad is not None:
            rango = df[col_edad].map(rango_desde_edad)
            if col_fecha is not None:
                faltan = rango == SIN_DATO
                if faltan.any():
                    rango.loc[faltan] = df.loc[faltan, col_fecha].map(
                        lambda f: rango_desde_edad(_edad_desde_fecha(f, hoy))
                    )
            df[COL_RANGO_EDAD] = rango
        elif col_fecha is not None:
            df[COL_RANGO_EDAD] = df[col_fecha].map(lambda f: rango_desde_edad(_edad_desde_fecha(f, hoy)))
        else:
            df[COL_RANGO_EDAD] = SIN_DATO

    return df


# ── Filtros ─────────────────────────────────────────────────────────────────

def opciones(df: pd.DataFrame, col: str) -> list[str]:
    """Valores únicos de una columna, ordenados como en el Power BI."""
    vals = df[col].dropna().astype(str).str.strip()
    vals = vals[vals != ""].unique().tolist()
    if _clave(col) == COL_RANGO_EDAD:
        return sorted(vals, key=lambda v: ORDEN_RANGOS.index(v) if v in ORDEN_RANGOS else 99)
    if _clave(col) == COL_MES:
        return sorted(vals, key=orden_mes)
    return sorted(vals)


def aplicar_filtros(df: pd.DataFrame, seleccion: dict[str, str | None], cols: dict[str, str | None]) -> pd.DataFrame:
    """seleccion: {etiqueta: valor elegido o None/'Todas'}."""
    mask = pd.Series(True, index=df.index)
    for etiqueta, valor in seleccion.items():
        col = cols.get(etiqueta)
        if col is None or valor in (None, "", "Todas"):
            continue
        mask &= df[col].astype(str).str.strip() == valor
    return df[mask]
