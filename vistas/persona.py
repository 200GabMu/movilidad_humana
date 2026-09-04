"""Página: buscar una persona por nombre y ver su ficha, su línea de tiempo de
atenciones, los servicios recibidos y sus registros. Solo con sesión iniciada
(la información es personal)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import almacen
from core.derivados import agregar_columnas_derivadas
from observatorio import personas as P
from observatorio.medidas import MedidaError
from ui import auth
from ui.componentes import boton_pagina, kpi, marcar_admin, portada, tabla_datos, tarjeta

AZUL, AMARILLO, GRIS = "#0B3D91", "#FFC300", "#5B6470"

marcar_admin()
if not auth.requiere("buscar"):
    st.stop()


@st.cache_data(show_spinner="Cargando consolidado…")
def cargar_datos(id_version: str):
    return agregar_columnas_derivadas(almacen.cargar(id_version, almacen.TIPO_LIMPIO))


@st.cache_data(show_spinner=False)
def indice(id_version: str):
    return P.indice_personas(cargar_datos(id_version))


def _grafico_periodos(p: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(x=p["periodo"], y=p["registros"], marker_color=AZUL,
                           text=p["registros"], textposition="outside",
                           hovertemplate="%{x}<br>%{y} registro(s)<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                      paper_bgcolor="white", font=dict(size=12), showlegend=False,
                      yaxis=dict(title="Registros", gridcolor="#EEF1F6", dtick=1, rangemode="tozero"),
                      xaxis=dict(title="", tickangle=-35, type="category"))
    return fig


def _grafico_servicios(s: pd.DataFrame, total_meses: int) -> go.Figure:
    s = s.sort_values("veces")
    fig = go.Figure(go.Bar(x=s["veces"], y=s["servicio"], orientation="h", marker_color=AZUL,
                           text=s["veces"], textposition="outside",
                           hovertemplate="%{y}<br>%{x} de " + str(total_meses) + " meses<extra></extra>"))
    fig.update_layout(height=max(160, 34 * len(s) + 60), margin=dict(l=10, r=30, t=10, b=10),
                      plot_bgcolor="white", paper_bgcolor="white", font=dict(size=12), showlegend=False,
                      xaxis=dict(title="Meses en que recibió el servicio", gridcolor="#EEF1F6", dtick=1,
                                 range=[0, max(total_meses, int(s["veces"].max())) + 0.8]),
                      yaxis=dict(title=""))
    return fig


# ── Portada ─────────────────────────────────────────────────────────────────
with portada("Administración · Movilidad Humana", "Buscar persona",
             "Escribe parte del nombre o del apellido. Verás la ficha de la persona, en qué meses fue "
             "atendida, qué servicios recibió y todos sus registros. Esta información es personal: "
             "solo la ven usuarios con sesión."):
    b1, b2, _ = st.columns([1.6, 1.4, 6])
    with b1:
        boton_pagina("vistas/unificar.py", "Panel administrador")
    with b2:
        boton_pagina("vistas/panel.py", "Ver panel", primario=False)

activa = almacen.version_activa()
if activa is None:
    st.info("Todavía no hay datos. Sube los reportes en **Panel administrador**.")
    st.stop()
try:
    df = cargar_datos(activa.id)
    idx = indice(activa.id)
except (almacen.AlmacenError, MedidaError) as exc:
    st.error(str(exc))
    st.stop()

# ── Búsqueda ────────────────────────────────────────────────────────────────
with tarjeta("🔍 Buscar", f"{len(idx):,} personas en la versión activa ({activa.id}). "
             "Se ignoran tildes y mayúsculas; puedes escribir nombre y apellido en cualquier orden."):
    texto = st.text_input("Nombre o apellido", placeholder="Ej.: María Pérez", key="mh_buscar_texto")
    resultados = P.buscar(idx, texto) if texto.strip() else idx.iloc[0:0]
    clave = None
    if texto.strip() and resultados.empty:
        st.warning("No hay coincidencias. Prueba con menos palabras o revisa la ortografía.")
    elif not resultados.empty:
        opciones = {P.etiqueta(f): f["clave"] for _, f in resultados.iterrows()}
        if len(resultados) >= 40:
            st.caption("Se muestran las primeras 40 coincidencias: escribe más letras para afinar.")
        sel = st.selectbox(f"{len(resultados)} coincidencia(s)", list(opciones), key="mh_buscar_sel")
        clave = opciones[sel]

if clave is None:
    st.stop()

# ── Datos de la persona ─────────────────────────────────────────────────────
todas = P.filas_de(df, clave)
años = P.años_de(todas)
c1, c2 = st.columns([1.2, 5])
with c1:
    año = st.selectbox("Año", ["Todos"] + años, key="mh_buscar_año")
d = P.filtrar_año(todas, None if año == "Todos" else año)
with c2:
    st.caption(f"Registros de {'todos los años' if año == 'Todos' else año}: "
               f"{len(d)} de {len(todas)} en total ({', '.join(años)}).")

r = P.resumen(d)
k = st.columns(4, gap="medium")
with k[0]:
    kpi("Registros", r["registros"], "una fila por mes reportado")
with k[1]:
    kpi("Meses atendida", r["meses"], f"en {r['años']} año(s)")
with k[2]:
    kpi("Primera atención", r["primera"], "")
with k[3]:
    kpi("Última atención", r["ultima"], "")

izq, der = st.columns([1.1, 1.4], gap="medium")
with izq:
    with tarjeta("Ficha", "Dato más reciente de cada campo (los vacíos no se muestran)."):
        filas = P.ficha(d)
        tabla_datos(filas[:20])
        if len(filas) > 20:
            with st.expander("Ver todos los datos"):
                tabla_datos(filas[20:])
with der:
    with tarjeta("Meses en que fue atendida", "Cada barra es un mes con registro en los reportes."):
        p = P.periodos(d)
        if p.empty:
            st.info("Sin registros para este filtro.")
        else:
            st.plotly_chart(_grafico_periodos(p), width="stretch", config={"displayModeBar": False})

    serv = P.servicios(d)
    otros = P.otros_kits(d)
    if serv or otros:
        for grupo, tabla in serv.items():
            with tarjeta(grupo, "Número de meses en que la casilla estaba en SI."):
                st.plotly_chart(_grafico_servicios(tabla, len(p)), width="stretch", config={"displayModeBar": False})
        if otros:
            with tarjeta("Otros kits entregados"):
                st.write(" · ".join(otros))
    else:
        with tarjeta("Servicios recibidos"):
            st.info("No hay casillas en SI para este filtro.")

with tarjeta("Registros completos", "Una fila por cada mes en que aparece en los reportes (todas las columnas)."):
    st.dataframe(d, width="stretch", hide_index=True, height=min(420, 60 + 36 * len(d)))
