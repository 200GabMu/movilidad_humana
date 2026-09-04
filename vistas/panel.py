"""Página pública: réplica del reporte Power BI "Observatorio".

Estructura (igual que el .pbix):
  INICIO  →  6 secciones  →  cada sección tiene un menú lateral con sus páginas.
  En todas las páginas: encabezado azul + barra de segmentadores arriba.
"""

import streamlit as st

from core import almacen
from core.exportar import to_excel_bytes
from core.derivados import COL_AÑO, COL_MES, MESES, agregar_columnas_derivadas, aplicar_filtros, orden_mes, resolver_columna
from observatorio import medidas, navegacion, visuales
from observatorio.spec import PAGINAS, Fila, Visual
from ui import auth
from ui.barra_filtros import barra_filtros


@st.cache_data(show_spinner=False)
def excel_activo(id_version: str) -> bytes:
    return to_excel_bytes(almacen.cargar(id_version, almacen.TIPO_LIMPIO))


def kpis_inicio(df) -> list[tuple[str, str, str]]:
    if df is None:
        return [("Personas atendidas", "—", "Aún no hay datos"), ("Registros", "—", ""),
                ("Nacionalidades", "—", ""), ("Meses reportados", "—", "")]
    try:
        personas = medidas.formato_entero(medidas.total_personas(df))
    except medidas.MedidaError:
        personas = "—"
    nac = resolver_columna(df, "NACIONALIDAD")
    ca, cm = resolver_columna(df, COL_AÑO), resolver_columna(df, COL_MES)
    meses = df[[ca, cm]].drop_duplicates().shape[0] if ca and cm else 0
    return [
        ("Personas atendidas", personas, "distintas por nombre, apellido y fecha de nacimiento"),
        ("Registros", medidas.formato_entero(len(df)), "atenciones en los reportes mensuales"),
        ("Nacionalidades", str(df[nac].nunique()) if nac else "—", "países de origen"),
        ("Meses reportados", str(meses), rango_de_datos(df)),
    ]


@st.cache_data(show_spinner="Cargando consolidado…")
def cargar_datos(id_version: str):
    df = almacen.cargar(id_version, almacen.TIPO_LIMPIO)
    return agregar_columnas_derivadas(df)


def rango_de_datos(df) -> str:
    """'Marzo 2023 – Junio 2026' a partir de AÑO y MES reales del consolidado."""
    ca, cm = resolver_columna(df, COL_AÑO), resolver_columna(df, COL_MES)
    if ca is None or cm is None:
        return ""
    d = df[[ca, cm]].dropna().astype(str)
    d = d[d[cm].map(orden_mes) < 99]
    if d.empty:
        return ""
    d["_k"] = d[ca].str.strip() + d[cm].map(lambda m: f"{orden_mes(m):02d}")
    ini = d.loc[d["_k"].idxmin()]
    fin = d.loc[d["_k"].idxmax()]

    def f(r):
        return f"{MESES[orden_mes(r[cm])].capitalize()} {r[ca].strip()}"

    return f"{f(ini)} – {f(fin)}"


def dibujar_celda(ctx, celda) -> None:
    if celda is None:
        return
    if isinstance(celda, Visual):
        visuales.dibujar(ctx, celda)
    elif isinstance(celda, list):
        for v in celda:
            dibujar_celda(ctx, v)
    elif isinstance(celda, Fila):
        dibujar_fila(ctx, celda)


def dibujar_fila(ctx, fila: Fila) -> None:
    cols = st.columns(fila.anchos, gap="small")
    for col, celda in zip(cols, fila.celdas):
        with col:
            dibujar_celda(ctx, celda)


# ── Datos ───────────────────────────────────────────────────────────────────
activa = almacen.version_activa()
df = None
if activa is not None:
    try:
        df = cargar_datos(activa.id)
    except almacen.AlmacenError as exc:
        st.error(str(exc))

pagina = navegacion.pagina_actual()
hay_sesion = auth.usuario_actual() is not None

# El botón ☰ del encabezado (y la lupa "Inicio" del menú) vuelven a la portada
if st.query_params.get("ir") == "inicio":
    navegacion.ir_a(navegacion.INICIO)
    st.query_params.clear()
    pagina = navegacion.INICIO

# ── INICIO (portada pública, réplica del Power BI) ──────────────────────────
if df is None or pagina == navegacion.INICIO or pagina not in PAGINAS:
    excel = excel_activo(activa.id) if (df is not None and hay_sesion) else None
    navegacion.inicio(rango_de_datos(df) if df is not None else "", kpis_inicio(df), excel,
                      nombre_excel=f"REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL_{activa.id if activa else ''}.xlsx",
                      hay_sesion=hay_sesion)
    if df is None:
        st.info("Todavía no hay datos publicados. El administrador debe subir los reportes en **Panel administrador**.")
    else:
        st.caption(f"Versión de datos: {activa.id} · {activa.fecha_legible} · {len(df):,} registros")
    st.stop()

# ── Páginas de sección: filtros arriba, menú a la izquierda, visuales ───────
df_f, seleccion, cols = barra_filtros(df)
sin_sexo = {k: (v if k != "SEXO" else "Todas") for k, v in seleccion.items()}
df_sin_sexo = aplicar_filtros(df, sin_sexo, cols)
ctx = medidas.Contexto(df=df_f, df_sin_sexo=df_sin_sexo)

col_menu, col_contenido = st.columns([1.35, 9], gap="small")
with col_menu:
    st.markdown('<span class="pbi-marca-menu"></span>', unsafe_allow_html=True)
    navegacion.menu_lateral(pagina, buscar=auth.puede("buscar"))

with col_contenido:
    spec = PAGINAS[pagina]
    st.markdown(f'<div class="pbi-pagina-titulo">{spec.nombre}</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.warning("No hay registros con esa combinación de filtros.")
    else:
        for fila in spec.filas:
            dibujar_fila(ctx, fila)
    st.caption(f"Versión de datos: {activa.id} · {activa.fecha_legible}")
