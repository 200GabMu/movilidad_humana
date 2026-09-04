"""
Punto de entrada.   Ejecutar con:   streamlit run app.py

Roles (core/usuarios.py):
  * Usuario final (sin cuenta)   → 📊 Panel (página de inicio, pública).
  * operador (usuario + clave)   → 📤 Unificar (solo agregar) · 🗂️ Historial (consulta).
  * administrador                → todo lo anterior + reemplazar, activar/eliminar
                                   versiones y 👥 Usuarios.
    Cada página administrativa comprueba el permiso al abrirse.

El encabezado azul se pinta aquí, ANTES de ejecutar la página, por eso
aparece arriba en todos los módulos.
"""

import streamlit as st

from ui import nube_ui
from ui.estilos import aplicar_estilos, encabezado

st.set_page_config(
    page_title="Movilidad Humana · Mensajeros de la Paz",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

aplicar_estilos()
nube_ui.arranque()   # si el disco está vacío (reinicio en la nube) trae data/ desde GitHub

panel = st.Page("vistas/panel.py", title="Panel", icon="📊", default=True)
acceso = st.Page("vistas/acceso.py", title="Acceso", icon="🔐")

# Las páginas administrativas se registran SIEMPRE (cada una comprueba el
# permiso con auth.requiere). Así una URL como /unificar sin sesión muestra el
# candado en vez del aviso "Page not found" de Streamlit.
admin = [
    st.Page("vistas/unificar.py", title="Panel administrador", icon="📤"),
    st.Page("vistas/historial.py", title="Historial y copias de seguridad", icon="🗂️"),
    st.Page("vistas/usuarios.py", title="Usuarios", icon="👥"),
    st.Page("vistas/persona.py", title="Buscar persona", icon="🔍"),
    acceso,
]
secciones = {"Público": [panel], "Administración": admin}

# La navegación se hace con los botones de cada página (la barra lateral de
# Streamlit queda oculta por CSS, como en el Power BI).
pagina = st.navigation(secciones, position="hidden")
# El encabezado azul (réplica del Power BI) solo va en las páginas internas del
# Observatorio; la portada, el acceso y la administración usan la franja oscura.
if pagina is panel and st.session_state.get("pbi_pagina", "INICIO") != "INICIO":
    encabezado()
pagina.run()
