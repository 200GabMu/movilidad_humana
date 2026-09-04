"""Bloques visuales del área administrativa: portada oscura, tarjetas, KPIs."""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


def enlace(pagina: str, etiqueta: str, icono: str | None = None) -> None:
    """st.page_link tolerante: fuera de st.navigation (pruebas) no rompe."""
    try:
        st.page_link(pagina, label=etiqueta, icon=icono)
    except Exception:  # StreamlitAPIException cuando la página no está registrada
        st.caption(etiqueta)


def boton_pagina(pagina: str, etiqueta: str, primario: bool = True, key: str | None = None) -> None:
    """Botón que navega a otra página (naranja en la franja oscura)."""
    if st.button(etiqueta, type="primary" if primario else "secondary", key=key):
        try:
            st.switch_page(pagina)
        except Exception:  # fuera de st.navigation (pruebas)
            st.caption(etiqueta)


def marcar_admin() -> None:
    """Marca la página como administrativa (botones primarios naranja)."""
    st.markdown('<span class="mh-admin"></span>', unsafe_allow_html=True)


@contextmanager
def portada(etiqueta: str, titulo: str, texto: str):
    """Franja azul oscuro con etiqueta pequeña, título grande y texto.
    Lo que se dibuje dentro del `with` (botones) queda sobre el fondo oscuro."""
    with st.container():
        st.markdown(
            f'<span class="mh-hero"></span>'
            f'<div class="mh-hero-label">{etiqueta}</div>'
            f'<div class="mh-hero-titulo">{titulo}</div>'
            f'<div class="mh-hero-texto">{texto}</div>',
            unsafe_allow_html=True,
        )
        yield


@contextmanager
def tarjeta(titulo: str, texto: str | None = None):
    with st.container():
        st.markdown(
            f'<span class="mh-tarjeta"></span><div class="mh-tarjeta-titulo">{titulo}</div>'
            + (f'<div class="mh-tarjeta-texto">{texto}</div>' if texto else ""),
            unsafe_allow_html=True,
        )
        yield


def tabla_datos(filas: list[tuple[str, str]]) -> None:
    cuerpo = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in filas)
    st.markdown(f'<table class="mh-datos">{cuerpo}</table>', unsafe_allow_html=True)


def kpi(etiqueta: str, valor: str, sub: str = "") -> None:
    with st.container():
        st.markdown(
            f'<span class="mh-tarjeta"></span><div class="mh-kpi-label">{etiqueta}</div>'
            f'<div class="mh-kpi-valor">{valor}</div><div class="mh-kpi-sub">{sub}</div>',
            unsafe_allow_html=True,
        )
