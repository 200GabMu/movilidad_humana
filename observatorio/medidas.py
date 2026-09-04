"""
Medidas del modelo Power BI, traducidas de DAX a pandas.

  TOTAL DE PERSONAS =
      COUNTROWS(DISTINCT(SELECTCOLUMNS(CONSOLIDADO, NOMBRES, APELLIDOS, FECHA DE NACIMIENTO)))
      -> personas distintas por (Nombres, Apellidos, Fecha de nacimiento)

  % Tarjeta Hombres = DIVIDE(CALCULATE([TOTAL], SEXO = "Hombre"),
                             CALCULATE([TOTAL], ALL(SEXO)), 0)
      -> el denominador ignora SOLO el filtro de SEXO (los demás filtros siguen)

  % Tarjeta Mujeres = igual con "Mujer"

Además, algunos visuales usan agregaciones directas de columna:
  Min(columna)          -> mínimo alfabético (así está en el reporte original)
  CountNonNull(columna) -> recuento de valores no vacíos
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.derivados import _clave, resolver_columna

COL_NOMBRES = "NOMBRES"
COL_APELLIDOS = "APELLIDOS"
COL_FECHA_NAC = "FECHA DE NACIMIENTO"
COL_SEXO = "SEXO"


class MedidaError(Exception):
    pass


@dataclass
class Contexto:
    """Lo que necesita una medida para evaluarse:
      df        -> filas tras aplicar TODOS los filtros de la barra
      df_sin_sexo -> filas tras aplicar todos los filtros MENOS el de SEXO
                     (para ALL(SEXO) en % Hombres / % Mujeres)"""
    df: pd.DataFrame
    df_sin_sexo: pd.DataFrame


def _cols_identidad(df: pd.DataFrame) -> list[str]:
    cols = [resolver_columna(df, c) for c in (COL_NOMBRES, COL_APELLIDOS, COL_FECHA_NAC)]
    faltan = [n for n, c in zip((COL_NOMBRES, COL_APELLIDOS, COL_FECHA_NAC), cols) if c is None]
    if faltan:
        raise MedidaError(f"Faltan columnas para TOTAL DE PERSONAS: {faltan}")
    return cols  # type: ignore[return-value]


def total_personas(df: pd.DataFrame) -> int:
    """DISTINCT sobre (Nombres, Apellidos, Fecha de nacimiento). Una combinación
    con todo vacío cuenta como una persona, igual que en DAX."""
    if df.empty:
        return 0
    return int(df[_cols_identidad(df)].drop_duplicates().shape[0])


def total_por_categoria(df: pd.DataFrame, col: str, serie: str | None = None, sin_blanco: bool = False) -> pd.DataFrame:
    """TOTAL DE PERSONAS agrupado por una categoría (y opcionalmente una serie).
    Los vacíos se muestran como '(En blanco)', como hace Power BI, salvo que
    sin_blanco=True (se omiten)."""
    ident = _cols_identidad(df)
    claves = [col] + ([serie] if serie else [])
    d = df[ident + claves].copy()
    if sin_blanco:
        d = d[d[col].notna() & (d[col].astype(str).str.strip() != "")]
    for k in claves:
        d[k] = d[k].where(d[k].notna(), "(En blanco)").astype(str).str.strip()
    d = d.drop_duplicates(subset=ident + claves)
    out = d.groupby(claves, sort=False).size().reset_index(name="valor")
    return out


def _filtrar_sexo(df: pd.DataFrame, valor: str) -> pd.DataFrame:
    col = resolver_columna(df, COL_SEXO)
    if col is None:
        raise MedidaError("No existe la columna SEXO")
    # DAX compara texto sin distinguir mayúsculas: "Hombre" == "HOMBRE"
    return df[df[col].astype(str).str.strip().str.upper() == valor.upper()]


def pct_sexo(ctx: Contexto, valor: str) -> float:
    numerador = total_personas(_filtrar_sexo(ctx.df, valor))
    denominador = total_personas(ctx.df_sin_sexo)
    return numerador / denominador if denominador else 0.0


def pct_hombres(ctx: Contexto) -> float:
    return pct_sexo(ctx, "Hombre")


def pct_mujeres(ctx: Contexto) -> float:
    return pct_sexo(ctx, "Mujer")


def minimo(df: pd.DataFrame, col: str) -> str:
    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]
    return str(s.min()) if not s.empty else ""


def count_non_null(df: pd.DataFrame, col: str) -> int:
    s = df[col]
    return int((s.notna() & (s.astype(str).str.strip() != "")).sum())


def aplicar_filtros_visual(df: pd.DataFrame, filtros: dict[str, list[str]] | None) -> pd.DataFrame:
    """Filtros propios de un visual (los del panel 'Filtros' de Power BI):
    {columna: [valores permitidos]} -> comparación de texto sin mayúsculas."""
    if not filtros:
        return df
    mask = pd.Series(True, index=df.index)
    for nombre, valores in filtros.items():
        col = resolver_columna(df, nombre)
        if col is None:
            raise MedidaError(f"El visual filtra por una columna que no existe: {nombre}")
        # sin tildes ni mayúsculas: 'VOCACION' == 'VOCACIÓN' (la ortografía se corrige en la limpieza)
        permitidos = {_clave(v) for v in valores}
        mask &= df[col].map(lambda x: _clave(x) if isinstance(x, str) else "").isin(permitidos)
    return df[mask]


def formato_entero(n) -> str:
    """Como las tarjetas del Power BI: sin separador de miles (2776)."""
    return f"{int(n)}"


def formato_pct(x: float) -> str:
    """Como las tarjetas del Power BI: sin decimales (43%)."""
    return f"{round(x * 100):d}%"
