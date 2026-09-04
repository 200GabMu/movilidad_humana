"""Página: acceso (usuario + contraseña), tarjeta centrada."""

import streamlit as st

from ui import auth
from ui.componentes import enlace, marcar_admin

marcar_admin()

# Ya hay sesión (p. ej. volvió a "Acceso" con el navegador): directo al panel
if auth.usuario_actual() is not None:
    try:
        st.switch_page(auth.PAGINA_ADMIN)
    except Exception:      # fuera de st.navigation (pruebas) se muestra la tarjeta
        pass

_, centro, _ = st.columns([1, 1.25, 1])
with centro:
    with st.container():
        st.markdown(
            '<span class="mh-login"></span>'
            '<div class="mh-login-titulo">Panel administrador</div>'
            '<div class="mh-login-texto">Ingresa con tu cuenta para subir reportes y administrar los datos del Observatorio.</div>',
            unsafe_allow_html=True,
        )
        auth.formulario_login()
        enlace("vistas/panel.py", "← Volver al panel")
