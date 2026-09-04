"""
Gráficos del panel con Plotly.

Reglas que se siguen a propósito:
  * Una serie -> un solo color (el azul institucional). El color no se usa
    para "decorar" categorías: eso confunde y no aporta información.
  * Barras horizontales ordenadas de mayor a menor para categorías largas.
  * Un solo eje; sin ejes dobles.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.derivados import ORDEN_RANGOS

COLOR_SERIE = "#2a78d6"
COLOR_TEXTO = "#52514e"
COLOR_GRID = "#e1e0d9"
PALETA_CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

_LAYOUT = dict(
    margin=dict(l=10, r=40, t=20, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLOR_TEXTO, size=12),
    xaxis=dict(gridcolor=COLOR_GRID, zeroline=False),
    yaxis=dict(gridcolor=COLOR_GRID, zeroline=False),
    showlegend=False,
)


def conteo(df: pd.DataFrame, col: str, top: int | None = 15) -> pd.DataFrame:
    """value_counts como tabla (Categoría, Registros), sin nulos."""
    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]
    vc = s.value_counts()
    if top is not None and len(vc) > top:
        otros = vc.iloc[top:].sum()
        vc = vc.iloc[:top]
        vc["OTROS (" + str(len(s.unique()) - top) + ")"] = otros
    return vc.rename_axis("Categoría").reset_index(name="Registros")


def barras_horizontales(df: pd.DataFrame, col: str, top: int | None = 15, alto: int = 320) -> go.Figure:
    datos = conteo(df, col, top).sort_values("Registros")
    fig = px.bar(datos, x="Registros", y="Categoría", orientation="h", text="Registros")
    fig.update_traces(
        marker_color=COLOR_SERIE, marker_line_width=0, textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} registros<extra></extra>",
    )
    fig.update_layout(**_LAYOUT, height=alto, xaxis_title=None, yaxis_title=None, bargap=0.3)
    _espacio_etiquetas(fig, datos["Registros"].max(), eje="x")
    return fig


def _espacio_etiquetas(fig: go.Figure, maximo, eje: str) -> None:
    """Deja un 18 % de aire para que el número fuera de la barra no se corte."""
    try:
        tope = float(maximo) * 1.18
    except (TypeError, ValueError):
        return
    if tope <= 0:
        return
    if eje == "x":
        fig.update_xaxes(range=[0, tope])
    else:
        fig.update_yaxes(range=[0, tope])


def barras_verticales(df: pd.DataFrame, col: str, orden: list[str] | None = None, alto: int = 320) -> go.Figure:
    datos = conteo(df, col, top=None)
    if orden:
        datos["_o"] = datos["Categoría"].map(lambda v: orden.index(v) if v in orden else 999)
        datos = datos.sort_values("_o")
    else:
        datos = datos.sort_values("Categoría")
    fig = px.bar(datos, x="Categoría", y="Registros", text="Registros")
    fig.update_traces(
        marker_color=COLOR_SERIE, marker_line_width=0, textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} registros<extra></extra>",
    )
    fig.update_layout(**_LAYOUT, height=alto, xaxis_title=None, yaxis_title=None, bargap=0.3)
    _espacio_etiquetas(fig, datos["Registros"].max(), eje="y")
    return fig


def rango_edad(df: pd.DataFrame, col: str, alto: int = 320) -> go.Figure:
    return barras_verticales(df, col, orden=ORDEN_RANGOS, alto=alto)


def serie_mensual(df: pd.DataFrame, col_año: str, col_mes: str, alto: int = 320) -> go.Figure:
    """Registros por mes; una línea por año (máx. 8, colores fijos por año)."""
    d = df[[col_año, col_mes]].dropna().astype(str)
    d = d[(d[col_año] != "SIN DATO") & (d[col_mes] != "SIN DATO")]
    tabla = d.groupby([col_año, col_mes]).size().reset_index(name="Registros").sort_values([col_año, col_mes])
    años = sorted(tabla[col_año].unique())[:8]
    fig = go.Figure()
    for i, a in enumerate(años):
        t = tabla[tabla[col_año] == a]
        fig.add_trace(go.Scatter(
            x=t[col_mes], y=t["Registros"], mode="lines+markers", name=str(a),
            line=dict(color=PALETA_CATEGORICA[i], width=2), marker=dict(size=8),
            hovertemplate=f"<b>{a}</b> · %{{x}}<br>%{{y:,}} registros<extra></extra>",
        ))
    layout = {**_LAYOUT, "showlegend": len(años) > 1}
    fig.update_layout(**layout, height=alto, xaxis_title=None, yaxis_title=None,
                      legend=dict(orientation="h", y=1.1, x=0))
    return fig


def conteo_si(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Para columnas tipo casilla (SI / X / 1): cuántas filas tienen marca en cada una."""
    filas = []
    for c in columnas:
        s = df[c].dropna().astype(str).str.strip().str.upper()
        n = int(s.isin(["SI", "SÍ", "X", "1", "TRUE", "VERDADERO"]).sum())
        filas.append((str(c), n))
    return pd.DataFrame(filas, columns=["Categoría", "Registros"])


def barras_conteo_si(df: pd.DataFrame, columnas: list[str], alto: int = 320) -> go.Figure:
    datos = conteo_si(df, columnas).sort_values("Registros")
    fig = px.bar(datos, x="Registros", y="Categoría", orientation="h", text="Registros")
    fig.update_traces(marker_color=COLOR_SERIE, marker_line_width=0, textposition="outside",
                      hovertemplate="<b>%{y}</b><br>%{x:,} entregas<extra></extra>")
    fig.update_layout(**_LAYOUT, height=alto, xaxis_title=None, yaxis_title=None, bargap=0.3)
    _espacio_etiquetas(fig, datos["Registros"].max(), eje="x")
    return fig
