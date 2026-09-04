"""
Dibuja cada tipo de visual del reporte con Plotly / HTML, usando el tema
"Mensajeros de la Paz - Azul y Amarillo" del .pbix (colores de datos, tipografía).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.derivados import ORDEN_RANGOS, orden_mes, resolver_columna
from observatorio import medidas
from observatorio.spec import Visual

# Tema del .pbix
COLORES = ["#0B3D91", "#FFC300", "#1E5EFF", "#F2A900", "#00306E", "#FFE066", "#4A78C4", "#B8860B",
           "#173F6B", "#8C6D00", "#4AC5BB", "#5F6B6D", "#FB8281", "#F4D25A", "#7F898A", "#A4DDEE"]
COLOR_TEXTO = "#0B1F3A"
COLOR_ETIQUETA = "#4A4A68"
COLOR_TITULO = "#0B1F3A"
COLOR_CALLOUT = "#0B3D91"
COLOR_BORDE = "#E5E7F0"
FUENTE = "Segoe UI, Segoe UI Semibold, Arial, sans-serif"


class VisualError(Exception):
    pass


# ── Datos para un visual ────────────────────────────────────────────────────

def _df_visual(ctx: medidas.Contexto, v: Visual) -> pd.DataFrame:
    return medidas.aplicar_filtros_visual(ctx.df, v.filtros)


def _valor_medida(ctx: medidas.Contexto, v: Visual):
    df = _df_visual(ctx, v)
    if v.medida == "personas":
        return medidas.total_personas(df)
    if v.medida == "pct_hombres":
        return medidas.pct_hombres(medidas.Contexto(df, medidas.aplicar_filtros_visual(ctx.df_sin_sexo, v.filtros)))
    if v.medida == "pct_mujeres":
        return medidas.pct_mujeres(medidas.Contexto(df, medidas.aplicar_filtros_visual(ctx.df_sin_sexo, v.filtros)))
    if v.medida.startswith("min:"):
        col = resolver_columna(df, v.medida[4:])
        if col is None:
            raise VisualError(f"No existe la columna {v.medida[4:]}")
        return medidas.minimo(df, col)
    if v.medida.startswith("count:"):
        col = resolver_columna(df, v.medida[6:])
        if col is None:
            raise VisualError(f"No existe la columna {v.medida[6:]}")
        return medidas.count_non_null(df, col)
    raise VisualError(f"Medida desconocida: {v.medida}")


def _tabla_categoria(ctx: medidas.Contexto, v: Visual) -> tuple[pd.DataFrame, str, str | None]:
    """Tabla (categoría[, serie], valor) ordenada como el visual original
    (valor descendente; salvo RANGO DE EDAD y MES que llevan orden natural)."""
    df = _df_visual(ctx, v)
    cat = resolver_columna(df, v.cat)
    if cat is None:
        raise VisualError(f"No existe la columna {v.cat}")
    serie = resolver_columna(df, v.serie) if v.serie else None
    if v.serie and serie is None:
        raise VisualError(f"No existe la columna {v.serie}")

    if v.medida == "personas":
        t = medidas.total_por_categoria(df, cat, serie, sin_blanco=v.sin_blanco)
    elif v.medida.startswith("count:"):
        col = resolver_columna(df, v.medida[6:])
        d = df[[cat] + ([serie] if serie else [])].copy()
        d["_v"] = df[col].notna() & (df[col].astype(str).str.strip() != "")
        for k in [cat] + ([serie] if serie else []):
            d[k] = d[k].where(d[k].notna(), "(En blanco)").astype(str).str.strip()
        t = d.groupby([cat] + ([serie] if serie else []))["_v"].sum().reset_index(name="valor")
    else:
        raise VisualError(f"Medida no soportada en gráficos: {v.medida}")

    tot = t.groupby(cat)["valor"].sum()
    if v.cat.upper() == "RANGO DE EDAD":
        orden = sorted(tot.index, key=lambda x: ORDEN_RANGOS.index(x) if x in ORDEN_RANGOS else 99)
    elif v.cat.upper() == "MES":
        orden = sorted(tot.index, key=orden_mes)
    else:
        orden = tot.sort_values(ascending=False).index.tolist()
    if v.top:
        orden = orden[: v.top]
        t = t[t[cat].isin(orden)]
    t[cat] = pd.Categorical(t[cat], categories=orden, ordered=True)
    t = t.sort_values(cat)
    return t, cat, serie


# ── Componentes visuales ────────────────────────────────────────────────────

def _titulo(v: Visual) -> None:
    if v.titulo:
        st.markdown(f'<div class="pbi-titulo">{v.titulo}</div>', unsafe_allow_html=True)


def tarjeta(ctx: medidas.Contexto, v: Visual) -> None:
    valor = _valor_medida(ctx, v)
    if isinstance(valor, float):
        texto = medidas.formato_pct(valor)
    elif isinstance(valor, int):
        texto = medidas.formato_entero(valor)
    else:
        texto = str(valor) if valor else "(En blanco)"
    if isinstance(valor, str):
        tam = "22px"          # texto (p. ej. IRREGULAR)
    elif v.grande:
        tam = "40px"
    else:
        tam = "28px"
    titulo = f'<div class="pbi-card-titulo">{v.titulo}</div>' if v.titulo else ""
    st.markdown(
        f'<div class="pbi-card">{titulo}<div class="pbi-card-valor" style="font-size:{tam}">{texto}</div>'
        f'<div class="pbi-card-etiqueta">{v.etiqueta or ""}</div></div>',
        unsafe_allow_html=True,
    )


def _layout(v: Visual, alto_defecto: int, leyenda: bool) -> dict:
    lay = dict(
        height=v.alto or alto_defecto,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=FUENTE, color=COLOR_ETIQUETA, size=11),
        showlegend=leyenda,
    )
    pos = v.leyenda or "bottom"
    if pos == "bottom":
        lay["legend"] = dict(orientation="h", yanchor="top", y=-0.14, xanchor="center", x=0.5)
        if leyenda:
            lay["margin"] = dict(l=8, r=8, t=8, b=36)
    elif pos == "top":
        lay["legend"] = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    elif pos == "left":
        lay["legend"] = dict(orientation="v", x=0, xanchor="left", y=0.5)
        lay["margin"] = dict(l=150, r=8, t=8, b=8)
        lay["legend"]["x"] = -0.28
    else:
        lay["legend"] = dict(orientation="v", x=1.02, y=0.5)
    return lay


def _mostrar(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def circular(ctx: medidas.Contexto, v: Visual) -> None:
    t, cat, _ = _tabla_categoria(ctx, v)
    _titulo(v)
    fig = go.Figure(go.Pie(
        labels=t[cat].astype(str), values=t["valor"], sort=False,
        hole=0.55 if v.tipo == "donut" else 0,
        marker=dict(colors=COLORES[: len(t)], line=dict(color="white", width=1)),
        textinfo="label+percent" if v.etiquetas_datos else "none",
        textposition="outside", textfont=dict(size=10),
        hovertemplate="<b>%{label}</b><br>%{value:,} personas · %{percent}<extra></extra>",
    ))
    fig.update_layout(**_layout(v, 300, v.leyenda is not None))
    _mostrar(fig)


def barras(ctx: medidas.Contexto, v: Visual) -> None:
    t, cat, serie = _tabla_categoria(ctx, v)
    _titulo(v)
    horizontal = v.tipo.startswith("barh")
    porcentaje = v.tipo.endswith("_pct")
    agrupado = v.tipo.endswith("_clust")
    cats = t[cat].cat.categories.tolist()

    fig = go.Figure()
    if serie:
        pivot = t.pivot_table(index=cat, columns=serie, values="valor", aggfunc="sum", fill_value=0, observed=False)
        pivot = pivot.reindex(cats)
        orden_series = pivot.sum().sort_values(ascending=False).index.tolist()
        if porcentaje:
            pivot = pivot.div(pivot.sum(axis=1).replace(0, 1), axis=0) * 100
        for i, s in enumerate(orden_series):
            vals = pivot[s].tolist()
            txt = [f"{x:.0f}%" if porcentaje else medidas.formato_entero(x) for x in vals]
            fig.add_trace(go.Bar(
                name=str(s), marker_color=COLORES[i % len(COLORES)],
                x=vals if horizontal else cats, y=cats if horizontal else vals,
                orientation="h" if horizontal else "v",
                text=txt if v.etiquetas_datos else None, textposition="auto",
                hovertemplate=f"<b>%{{{'y' if horizontal else 'x'}}}</b> · {s}<br>%{{{'x' if horizontal else 'y'}:,.0f}}"
                              + ("%" if porcentaje else " personas") + "<extra></extra>",
            ))
        fig.update_layout(barmode="group" if agrupado else "stack")
        leyenda = True
    else:
        vals = t["valor"].tolist()
        fig.add_trace(go.Bar(
            x=vals if horizontal else cats, y=cats if horizontal else vals,
            orientation="h" if horizontal else "v",
            marker_color=COLORES[0],
            text=[medidas.formato_entero(x) for x in vals] if v.etiquetas_datos else None,
            textposition="outside", cliponaxis=False,
            hovertemplate=f"<b>%{{{'y' if horizontal else 'x'}}}</b><br>%{{{'x' if horizontal else 'y'}:,.0f}} personas<extra></extra>",
        ))
        leyenda = False

    lay = _layout(v, 320, leyenda)
    fig.update_layout(**lay, bargap=0.25)
    eje_cat = dict(title=dict(text=v.eje_x, font=dict(size=11)) if v.eje_x else None, tickfont=dict(size=10), automargin=True)
    eje_val = dict(title=dict(text=v.eje_y, font=dict(size=11)) if v.eje_y else None, gridcolor=COLOR_BORDE,
                   zeroline=False, tickfont=dict(size=10))
    if porcentaje:
        eje_val["ticksuffix"] = "%"
    if horizontal:
        fig.update_yaxes(autorange="reversed", **eje_cat)
        fig.update_xaxes(**eje_val)
    else:
        fig.update_xaxes(**eje_cat)
        fig.update_yaxes(**eje_val)
    _mostrar(fig)


def linea(ctx: medidas.Contexto, v: Visual) -> None:
    t, cat, _ = _tabla_categoria(ctx, v)
    _titulo(v)
    fig = go.Figure(go.Scatter(
        x=t[cat].astype(str), y=t["valor"], mode="lines+markers+text",
        line=dict(color=COLORES[0], width=2), marker=dict(size=9, color=COLORES[0]),
        text=[medidas.formato_entero(x) for x in t["valor"]], textposition="top center",
        hovertemplate="<b>%{x}</b><br>%{y:,} personas<extra></extra>",
    ))
    fig.update_layout(**_layout(v, 320, False))
    fig.update_yaxes(title=None, gridcolor=COLOR_BORDE, zeroline=False, rangemode="tozero")
    fig.update_xaxes(title=None)
    _mostrar(fig)


def embudo(ctx: medidas.Contexto, v: Visual) -> None:
    t, cat, _ = _tabla_categoria(ctx, v)
    _titulo(v)
    fig = go.Figure(go.Funnel(
        y=t[cat].astype(str), x=t["valor"], textinfo="value",
        marker=dict(color=COLORES[: len(t)]),
        hovertemplate="<b>%{y}</b><br>%{x:,} personas<extra></extra>",
    ))
    fig.update_layout(**_layout(v, 320, False))
    _mostrar(fig)


def matriz(ctx: medidas.Contexto, v: Visual) -> None:
    df = _df_visual(ctx, v)
    filas = resolver_columna(df, v.cat)
    cols = resolver_columna(df, v.columnas)
    if filas is None or cols is None:
        raise VisualError(f"No existen las columnas {v.cat} / {v.columnas}")
    if v.sin_blanco:
        df = df[df[filas].notna() & (df[filas].astype(str).str.strip() != "")]
    t = medidas.total_por_categoria(df, filas, cols)
    pivot = t.pivot_table(index=filas, columns=cols, values="valor", aggfunc="sum", fill_value=0)
    # Igual que la matriz de Power BI: filas y columnas en orden alfabético
    pivot = pivot.sort_index()
    pivot = pivot[sorted(pivot.columns, key=str)]
    # Los totales NO son la suma de las celdas: son la medida evaluada en ese
    # nivel (una persona que cambió de rango entre reportes cuenta una sola vez),
    # exactamente como calcula la matriz de Power BI.
    tot_filas = medidas.total_por_categoria(df, filas).set_index(filas)["valor"]
    tot_cols = medidas.total_por_categoria(df, cols).set_index(cols)["valor"]
    pivot["Total"] = tot_filas.reindex(pivot.index).fillna(0)
    pivot.loc["Total"] = [int(tot_cols.get(c, 0)) for c in pivot.columns[:-1]] + [medidas.total_personas(df)]
    pivot = pivot.astype(int)
    _titulo(v)
    st.dataframe(pivot, width="stretch", height=v.alto or 240)


RENDER = {
    "card": tarjeta,
    "pie": circular, "donut": circular,
    "barh": barras, "barv": barras, "barh_pct": barras, "barv_pct": barras,
    "barh_clust": barras, "barv_clust": barras,
    "line": linea, "funnel": embudo, "matriz": matriz,
}


# Notas al pie que explican las categorías de un campo (se muestran dentro de
# la misma tarjeta, debajo del gráfico, en todos los visuales que lo usen).
NOTAS_CAMPO = {
    "RANGO DE EDAD": (
        "<b>NN</b> 0 meses – 11 años &nbsp;·&nbsp; <b>ADOLESCENTE</b> 12 – 17 años &nbsp;·&nbsp; "
        "<b>ADULTO</b> 18 – 64 años &nbsp;·&nbsp; <b>ADULTO MAYOR</b> 65 años en adelante"
    ),
}


def _nota_campo(v: Visual) -> None:
    campos = {c for c in (v.cat, v.serie, v.columnas, v.etiqueta) if c}
    for campo, texto in NOTAS_CAMPO.items():
        if any(campo in str(c).upper() for c in campos):
            st.markdown(f'<div class="pbi-nota">{texto}</div>', unsafe_allow_html=True)


def dibujar(ctx: medidas.Contexto, v: Visual) -> None:
    fn = RENDER.get(v.tipo)
    if fn is None:
        st.error(f"Tipo de visual no soportado: {v.tipo}")
        return
    try:
        with st.container(border=True):
            fn(ctx, v)
            if v.tipo != "card":
                _nota_campo(v)
    except (VisualError, medidas.MedidaError) as exc:
        st.warning(f"**{v.titulo or v.etiqueta or v.tipo}**: {exc}")
