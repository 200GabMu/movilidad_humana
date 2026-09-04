"""
Barra de filtros del panel (misma estructura que el reporte Power BI):

  [🧹]  NACIONALIDAD | CIUDAD | RANGO DE EDAD | SEXO | SITUACIÓN MIGRATORIA | AÑO | MES

Cada filtro es un desplegable con la opción "Todas". Devuelve el diccionario
{etiqueta: valor} y el DataFrame ya filtrado.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.derivados import FILTROS, aplicar_filtros, columnas_de_filtros, opciones

TODAS = "Todas"
_PREFIJO_KEY = "mh_filtro_"


def _key(etiqueta: str) -> str:
    return _PREFIJO_KEY + etiqueta.replace(" ", "_")


def limpiar_filtros() -> None:
    for etiqueta, _ in FILTROS:
        st.session_state[_key(etiqueta)] = TODAS


def barra_filtros(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], dict[str, str | None]]:
    cols_reales = columnas_de_filtros(df)
    seleccion: dict[str, str] = {}

    caja = st.container(border=True)
    caja.markdown('<span class="mh-marca-filtros"></span>', unsafe_allow_html=True)  # ancla para el CSS
    columnas = caja.columns([0.45] + [1] * len(FILTROS), vertical_alignment="bottom")

    with columnas[0]:
        # Va ANTES de los selectbox para que al pulsarlo se reinicien en este mismo ciclo
        if st.button("🧹", help="Limpiar todos los filtros", width="stretch"):
            limpiar_filtros()

    for i, (etiqueta, _) in enumerate(FILTROS, start=1):
        col_real = cols_reales.get(etiqueta)
        with columnas[i]:
            if col_real is None:
                st.selectbox(etiqueta, [TODAS], key=_key(etiqueta), disabled=True,
                             help="No existe esta columna en el consolidado")
                seleccion[etiqueta] = TODAS
                continue
            ops = [TODAS] + opciones(df, col_real)
            k = _key(etiqueta)
            if st.session_state.get(k) not in ops:   # valor viejo que ya no existe en esta versión
                st.session_state[k] = TODAS
            seleccion[etiqueta] = st.selectbox(etiqueta, ops, key=k)

    df_filtrado = aplicar_filtros(df, seleccion, cols_reales)
    activos = {k: v for k, v in seleccion.items() if v != TODAS}
    if activos:
        st.caption("Filtros activos: " + " · ".join(f"**{k}** = {v}" for k, v in activos.items()))
    return df_filtrado, seleccion, cols_reales
