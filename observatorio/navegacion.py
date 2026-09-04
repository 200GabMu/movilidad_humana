"""
Navegación del panel: INICIO (6 botones de sección) y menú lateral de cada
sección, igual que el reporte Power BI. El estado vive en session_state.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from observatorio.spec import PAGINAS, SECCIONES, seccion_de

KEY_PAGINA = "pbi_pagina"
INICIO = "INICIO"
DIR_ICONOS = Path(__file__).resolve().parent.parent / "assets" / "iconos"
DIR_ASSETS = DIR_ICONOS.parent


def pagina_actual() -> str:
    return st.session_state.get(KEY_PAGINA, INICIO)


def ir_a(pagina: str) -> None:
    st.session_state[KEY_PAGINA] = pagina


def _icono_b64(nombre: str) -> str | None:
    ruta = DIR_ICONOS / f"{nombre}.png"
    if not ruta.exists():
        return None
    return base64.b64encode(ruta.read_bytes()).decode()


def _img(nombre: str, alto: int = 40, blanco: bool = False) -> str:
    b64 = _icono_b64(nombre)
    if not b64:
        return ""
    filtro = "filter:invert(1);" if blanco else ""
    return f'<img src="data:image/png;base64,{b64}" style="height:{alto}px;{filtro}">'


def _logo_html(nombre: str, alto: int) -> str:
    ruta = DIR_ASSETS / nombre
    if not ruta.exists():
        return ""
    b64 = base64.b64encode(ruta.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" style="height:{alto}px;">'


def inicio(rango_datos: str, kpis: list[tuple[str, str, str]], excel: bytes | None = None,
           nombre_excel: str = "consolidado.xlsx", hay_sesion: bool = False) -> None:
    """Portada pública: arriba la franja oscura (título, texto, botones y
    tarjetas con cifras); debajo, la página INICIO del Power BI (logos,
    OBSERVATORIO, datos disponibles y las 6 secciones)."""
    from ui.componentes import enlace, kpi, portada  # import tardío: evita ciclo

    # ── 1) Franja oscura + cifras ──
    with portada(
        f"Observatorio · Movilidad Humana · {rango_datos or 'sin datos'}",
        "Observatorio de Movilidad Humana",
        "Consulta el perfil de la población atendida, su situación migratoria, vulnerabilidades, "
        "asistencia humanitaria, intervenciones técnicas e integración comunitaria, a partir de los "
        "reportes mensuales del Servicio de Movilidad Humana.",
    ):
        # La descarga solo existe con sesión iniciada (el consolidado tiene datos
        # personales). Al público solo se le muestra el acceso al panel.
        if hay_sesion:
            b1, b2, b3, _ = st.columns([1.5, 2.2, 1.9, 4])
            with b1:
                if excel is not None:
                    st.download_button("Descargar Excel", data=excel, file_name=nombre_excel, type="primary",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.button("Descargar Excel", type="primary", disabled=True, help="Todavía no hay datos.")
            with b2:
                enlace("vistas/unificar.py", "Panel administrador", "🔐")
            with b3:
                enlace("vistas/persona.py", "Buscar persona", "🔍")
        else:
            b1, _ = st.columns([2.2, 7])
            with b1:
                enlace("vistas/acceso.py", "Panel administrador", "🔐")

    cols = st.columns(len(kpis), gap="medium")
    for col, (etiqueta, valor, sub) in zip(cols, kpis):
        with col:
            kpi(etiqueta, valor, sub)

    # ── 2) INICIO del Power BI ──
    st.markdown(
        f"""
        <div class="pbi-inicio">
          <div class="pbi-inicio-logos">{_logo_html("logo.png", 150)}{_logo_html("logo_tec_azuay.png", 110)}</div>
          <div class="pbi-inicio-titulo">OBSERVATORIO<span class="pbi-inicio-barra"></span></div>
          <div class="pbi-inicio-caja pbi-inicio-sub">Datos disponibles</div>
          <div class="pbi-inicio-caja pbi-inicio-rango">{rango_datos or "Sin datos publicados"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    filas = [SECCIONES[:3], SECCIONES[3:]]
    for fila in filas:
        cols = st.columns(3, gap="large")
        for col, (nombre, icono, _) in zip(cols, fila):
            with col:
                with st.container():
                    st.markdown('<span class="pbi-marca-seccion"></span>', unsafe_allow_html=True)
                    c_ic, c_tx = st.columns([1, 2.4], vertical_alignment="center")
                    c_ic.markdown(f'<div class="pbi-seccion-icono">{_img(icono, 64)}</div>', unsafe_allow_html=True)
                    if c_tx.button(nombre, key=f"sec_{icono}", width="stretch"):
                        ir_a(nombre)
                        st.rerun()


def menu_lateral(pagina: str, buscar: bool = False) -> None:
    """Columna izquierda azul: páginas de la sección + volver al inicio."""
    sec = seccion_de(pagina)
    if sec is None:
        return
    nombre_sec, _, paginas = sec
    st.markdown('<div class="pbi-menu-titulo">Menú</div>', unsafe_allow_html=True)
    for p in paginas:
        icono = PAGINAS[p].icono
        st.markdown(f'<div class="pbi-menu-icono">{_img(icono, 34, blanco=True)}</div>', unsafe_allow_html=True)
        activo = p == pagina
        if st.button(p, key=f"nav_{p}", width="stretch", type="primary" if activo else "secondary"):
            ir_a(p)
            st.rerun()
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="pbi-menu-icono">{_img("salir", 28, blanco=True)}</div>', unsafe_allow_html=True)
    if st.button("Inicio", key="nav_inicio", width="stretch"):
        ir_a(INICIO)
        st.rerun()
    if buscar:   # solo con sesión: la ficha tiene datos personales
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("🔍 Buscar persona", key="nav_buscar", width="stretch"):
            try:
                st.switch_page("vistas/persona.py")
            except Exception:  # fuera de st.navigation (pruebas)
                pass
