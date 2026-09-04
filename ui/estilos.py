"""Encabezado azul estilo Power BI + estilos globales de la app."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

AZUL = "#1F3F8F"        # azul del encabezado (tomado del reporte Power BI)
AZUL_OSCURO = "#152C66"
BLANCO = "#FFFFFF"
GRIS_FONDO = "#F4F6FA"

RUTA_LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
NOMBRE_ORGANIZACION = "FUNDACIÓN MENSAJEROS DE LA PAZ"
SUBTITULO = "Servicio de Movilidad Humana"

_CSS = f"""
<style>
  /* sin barra lateral ni barra de herramientas de Streamlit */
  section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
  div[data-testid="stToolbar"], div[data-testid="stDecoration"] {{ display: none !important; }}
  .block-container {{ padding-top: 2.6rem; padding-bottom: 2rem; max-width: 1400px; }}
  .pbi-nota {{
    font-size: 0.78rem; color: #5B6470; line-height: 1.35; margin-top: -0.2rem;
    padding: 0.35rem 0.5rem; border-top: 1px dashed #D5DAE3;
  }}
  .pbi-nota b {{ color: {AZUL}; font-weight: 700; }}
  /* el script invisible que cierra el aviso "Page not found" no ocupa espacio */
  div[data-testid="stElementContainer"]:has(> iframe[data-testid="stIFrame"][height="0"]),
  div[data-testid="stElementContainer"]:has(> iframe.mh-oculto) {{ display: none !important; }}

  .mh-header {{
    background: {AZUL};
    color: {BLANCO};
    border-radius: 10px;
    padding: 10px 18px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,.18);
  }}
  .mh-header img {{ height: 52px; width: auto; }}
  .mh-header .mh-logo-fallback {{
    width: 52px; height: 52px; border-radius: 50%;
    background: {BLANCO}; color: {AZUL};
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 20px;
  }}
  .mh-header .mh-titulo {{
    flex: 1; text-align: center;
    font-size: 26px; font-weight: 800; letter-spacing: .5px;
    text-transform: uppercase;
  }}
  .mh-header .mh-sub {{ font-size: 12px; font-weight: 400; opacity: .85; text-transform: none; }}
  .mh-header .mh-menu {{
    width: 52px; height: 40px; border-radius: 8px;
    background: {BLANCO}; color: {AZUL};
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; text-decoration: none;
  }}
  .mh-header .mh-menu:hover {{ background: #FFC300; color: {AZUL}; }}

  /* barra de filtros: tarjeta clara con borde azul, como en Power BI */
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.mh-marca-filtros) {{
    background: {GRIS_FONDO};
    border: 2px solid {AZUL} !important;
    border-radius: 10px;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.mh-marca-filtros) label p {{
    font-weight: 700 !important; font-size: 13px !important;
  }}

  .mh-seccion {{
    background: {AZUL}; color: {BLANCO};
    font-weight: 700; text-align: center;
    padding: 6px; border-radius: 8px 8px 0 0;
    text-transform: uppercase; font-size: 14px;
    margin-top: 6px;
  }}
  div[data-testid="stMetric"] {{
    background: {GRIS_FONDO}; border-left: 5px solid {AZUL};
    padding: 8px 12px; border-radius: 8px;
  }}

  /* ── Réplica Power BI ─────────────────────────────────────────── */
  .pbi-titulo {{
    font-family: "Segoe UI Semibold", "Segoe UI", Arial, sans-serif;
    font-size: 13px; font-weight: 700; color: #0B1F3A;
    text-transform: uppercase; padding: 2px 4px 0 4px;
  }}
  .pbi-card {{ text-align: center; padding: 6px 4px; min-height: 96px; }}
  .pbi-card-titulo {{ font-size: 12px; font-weight: 700; color: #0B1F3A; text-transform: uppercase; }}
  .pbi-card-valor {{ font-family: "Segoe UI Semibold", "Segoe UI", Arial, sans-serif; font-weight: 600; color: #0B3D91; line-height: 1.15;
                     white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .pbi-card-etiqueta {{ font-size: 11px; color: #4A4A68; }}
  .pbi-pagina-titulo {{ font-size: 15px; font-weight: 800; color: {AZUL}; text-transform: uppercase; margin: 2px 0 6px 2px; }}

  /* menú lateral azul (columna que contiene .pbi-marca-menu) */
  div[data-testid="stColumn"]:has(.pbi-marca-menu) {{
    background: {AZUL}; border-radius: 10px; padding: 8px 6px 12px 6px;
    align-self: flex-start;   /* solo tan alto como sus botones: sin franja azul vacía debajo */
  }}
  div[data-testid="stColumn"]:has(.pbi-marca-menu) button {{
    padding: 3px 4px !important; min-height: 34px; height: auto !important;
  }}
  div[data-testid="stColumn"]:has(.pbi-marca-menu) button p,
  div[data-testid="stColumn"]:has(.pbi-marca-menu) button div {{
    font-size: 11px !important; line-height: 1.15 !important;
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
  }}
  div[data-testid="stColumn"]:has(.pbi-marca-menu) button[kind="secondary"] {{
    background: {AZUL}; color: {BLANCO}; border-color: rgba(255,255,255,.45);
  }}
  div[data-testid="stColumn"]:has(.pbi-marca-menu) button[kind="primary"] {{
    background: #FFC300; color: #0B1F3A; border-color: #FFC300; font-weight: 700;
  }}
  .pbi-menu-titulo {{ color: {BLANCO}; font-weight: 700; text-align: center; font-size: 13px; margin-bottom: 4px; }}
  .pbi-menu-icono {{ text-align: center; margin-top: 8px; }}

  /* portada (INICIO del Power BI) */
  .pbi-inicio {{ text-align: center; padding: 26px 0 10px 0; }}
  .pbi-inicio-logos {{ display: flex; justify-content: center; gap: 140px; align-items: center; margin-bottom: 10px; }}
  .pbi-inicio-titulo {{ font-family: Verdana, sans-serif; font-weight: 900; font-size: 64px; color: #12239e; letter-spacing: 1px; line-height: 1.1; }}
  .pbi-inicio-barra {{ display: inline-block; width: 6px; height: 56px; background: #BFC3CC; margin-left: 28px; vertical-align: middle; }}
  .pbi-inicio-caja {{ display: inline-block; border: 1px solid #E3E6EC; border-radius: 6px; padding: 8px 40px; background: #FFFFFF; }}
  .pbi-inicio-sub {{ font-family: Corbel, "Segoe UI", sans-serif; font-weight: 700; font-size: 24px; color: #12239e; margin-top: 14px; }}
  .pbi-inicio-rango {{ font-family: Cambria, Georgia, serif; font-weight: 700; font-size: 24px; color: #ffc300; margin: 6px 0 22px 0; display: block; width: fit-content; margin-left: auto; margin-right: auto; }}
  .pbi-seccion-icono {{ background: #FFFFFF; border: 1px solid #E3E6EC; border-radius: 6px; padding: 6px; text-align: center; }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) {{
    border: 1px solid #E3E6EC; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,.08); padding: 10px 12px; background: #FFFFFF;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) button {{
    background: transparent; border: none; color: #5A5A5A; font-weight: 700; font-size: 20px; line-height: 1.2;
    white-space: normal; text-align: center; padding: 6px 4px;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) button {{ height: auto !important; min-height: 64px; }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) button p,
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) button div {{
    font-size: 20px !important; font-weight: 700 !important; color: #5A5A5A;
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important; line-height: 1.2 !important;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .pbi-marca-seccion) button:hover p {{ color: #12239e; }}
  .pbi-boton-icono {{ text-align: center; margin-top: 10px; }}

  /* ── Área administrativa (estilo portada oscura + tarjetas) ─────────── */
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) {{
    background: #16283F; color: #FFFFFF; border-radius: 14px;
    padding: 30px 34px 26px 34px; margin: 4px 0 18px 0;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) p,
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a {{ color: #FFFFFF; }}
  .mh-hero-label {{ font-size: 12px; letter-spacing: 3px; text-transform: uppercase; color: #C8D2E0; margin-bottom: 6px; }}
  .mh-hero-titulo {{ font-size: 40px; font-weight: 800; line-height: 1.1; margin-bottom: 12px; color: #FFFFFF; }}
  .mh-hero-texto {{ font-size: 17px; color: #E3E9F2; max-width: 760px; margin-bottom: 14px; }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) button,
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a[data-testid="stPageLink-NavLink"],
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a[kind] {{
    background: transparent; color: #FFFFFF; border: 1.5px solid rgba(255,255,255,.6); border-radius: 8px;
    font-weight: 600; padding: 8px 18px;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) button[kind="primary"] {{
    background: #D9822B; border-color: #D9822B; color: #FFFFFF;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a[data-testid="stPageLink-NavLink"] {{
    background: transparent; border: 1.5px solid rgba(255,255,255,.7); white-space: nowrap;
  }}
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a[data-testid="stPageLink-NavLink"] span,
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-hero) a[data-testid="stPageLink-NavLink"] p {{
    color: #FFFFFF !important; font-weight: 700;
  }}

  .mh-hero-logos {{ display: flex; gap: 22px; align-items: center; margin: 4px 0 12px 0; }}
  .mh-hero-logos img {{ background: #FFFFFF; border-radius: 8px; padding: 4px 8px; }}
  .mh-secciones-titulo {{ font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: #5B6675; margin: 22px 0 4px 2px; }}

  /* tarjetas blancas */
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-tarjeta) {{
    background: #FFFFFF; border: 1px solid #E5E9F0; border-radius: 14px; padding: 22px 24px;
    box-shadow: 0 1px 3px rgba(20,40,70,.06);
  }}
  .mh-tarjeta-titulo {{ font-size: 20px; font-weight: 800; color: #16283F; margin-bottom: 10px; }}
  .mh-tarjeta-texto {{ font-size: 14px; color: #5B6675; line-height: 1.5; }}
  .mh-datos {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
  .mh-datos td {{ padding: 9px 0; border-bottom: 1px solid #E5E9F0; color: #16283F; }}
  .mh-datos td:last-child {{ text-align: right; font-weight: 700; }}
  .mh-kpi-label {{ font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #5B6675; }}
  .mh-kpi-valor {{ font-size: 36px; font-weight: 800; color: #16283F; line-height: 1.1; }}
  .mh-kpi-sub {{ font-size: 14px; color: #5B6675; }}

  /* botones primarios naranja en el área administrativa */
  div[data-testid="stAppViewContainer"]:has(.mh-admin) button[kind="primary"],
  div[data-testid="stAppViewContainer"]:has(.mh-admin) button[kind="primaryFormSubmit"] {{
    background: #D9822B; border-color: #D9822B; color: #FFFFFF; font-weight: 700;
  }}

  /* acceso: tarjeta centrada */
  div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:first-child .mh-login) {{
    background: #FFFFFF; border: 1px solid #E5E9F0; border-radius: 14px; padding: 28px 30px;
    box-shadow: 0 2px 8px rgba(20,40,70,.08); margin-top: 30px;
  }}
  .mh-login-titulo {{ font-size: 34px; font-weight: 800; color: #16283F; margin-bottom: 8px; }}
  .mh-login-texto {{ font-size: 16px; color: #5B6675; margin-bottom: 8px; }}
</style>
"""




def _logo_html() -> str:
    if RUTA_LOGO.exists():
        try:
            b64 = base64.b64encode(RUTA_LOGO.read_bytes()).decode()
            return f'<img src="data:image/png;base64,{b64}" alt="logo">'
        except OSError:
            pass
    return '<div class="mh-logo-fallback">MP</div>'


# Streamlit Cloud abre la app con una ruta interna (…/~/+/) que no es una
# página nuestra y muestra el aviso "Page not found". Este pequeño script,
# invisible, cierra ese aviso en cuanto aparece (solo ese: mira el título).
_CERRAR_AVISO_JS = """
<script>
(function () {
  const doc = window.parent && window.parent.document;
  if (!doc) return;
  try { window.frameElement.classList.add('mh-oculto'); } catch (e) {}
  function cerrar() {
    doc.querySelectorAll('[data-testid="stDialog"]').forEach(function (d) {
      const titulo = d.querySelector('h2');
      if (titulo && /page not found/i.test(titulo.textContent)) {
        const btn = d.querySelector('button[aria-label="Close"]');
        if (btn) btn.click();
      }
    });
  }
  cerrar();
  new MutationObserver(cerrar).observe(doc.body, { childList: true, subtree: true });
})();
</script>
"""


def aplicar_estilos() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    try:
        components.html(_CERRAR_AVISO_JS, height=0)
    except Exception:  # fuera del navegador (pruebas) no hace falta
        pass


def encabezado(titulo: str = NOMBRE_ORGANIZACION, subtitulo: str = SUBTITULO) -> None:
    """Barra azul superior: logo · nombre de la organización · icono de menú."""
    st.markdown(
        f"""
        <div class="mh-header">
          {_logo_html()}
          <div class="mh-titulo">{titulo}<div class="mh-sub">{subtitulo}</div></div>
          <a class="mh-menu" href="?ir=inicio" target="_self" title="Menú de secciones">☰</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def titulo_seccion(texto: str) -> None:
    st.markdown(f'<div class="mh-seccion">{texto}</div>', unsafe_allow_html=True)


def mostrar_mensajes(mensajes, contenedor=None) -> None:
    """Pinta la lista de Mensaje(nivel, texto) del núcleo con el widget adecuado."""
    c = contenedor or st
    for m in mensajes:
        fn = {"info": c.info, "success": c.success, "warning": c.warning, "error": c.error}.get(m.nivel, c.write)
        fn(m.texto)
