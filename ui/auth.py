"""
Sesión y permisos.

  * Usuario final  → sin cuenta. Solo ve el Panel.
  * Cuentas (core/usuarios.py) → inician sesión con usuario + contraseña.
    Lo que puede hacer cada una depende de su rol (administrador / operador).

La primera vez, si no hay usuarios creados, se crea "admin" con la clave
ADMIN_PASSWORD de .streamlit/secrets.toml (o de la variable de entorno).
"""

from __future__ import annotations

import os
import time

import streamlit as st

from core import usuarios as us

_KEY = "mh_usuario"          # dict {nombre, rol}
_KEY_FALLOS = "mh_fallos"    # intentos fallidos en esta sesión
MAX_INTENTOS = 5
ESPERA_SEG = 30
PAGINA_ADMIN = "vistas/unificar.py"   # a dónde se va después de iniciar sesión


def clave_inicial() -> str | None:
    try:
        clave = st.secrets.get("ADMIN_PASSWORD")
    except (FileNotFoundError, AttributeError):
        clave = None
    if not clave:
        clave = os.environ.get("ADMIN_PASSWORD")
    return str(clave) if clave else None


def usuario_actual() -> us.Usuario | None:
    datos = st.session_state.get(_KEY)
    if not datos:
        return None
    u = us.obtener(datos["nombre"])
    if u is None or not u.activo:      # lo desactivaron/eliminaron mientras tenía sesión
        cerrar_sesion()
        return None
    return u


def es_admin() -> bool:
    u = usuario_actual()
    return u is not None and u.rol == "administrador"


def puede(permiso: str) -> bool:
    u = usuario_actual()
    return u is not None and u.puede(permiso)


def cerrar_sesion() -> None:
    st.session_state.pop(_KEY, None)


def requiere(permiso: str) -> bool:
    """Guardia para páginas de administración. True si puede continuar."""
    if puede(permiso):
        return True
    from ui.componentes import enlace  # import tardío: evita ciclo
    if usuario_actual() is None:
        st.error("🔒 Esta sección requiere iniciar sesión. Si acabas de refrescar la página, "
                 "la sesión se cierra: vuelve a entrar.")
        enlace("vistas/acceso.py", "Iniciar sesión", "🔐")
    else:
        st.error("🔒 Tu rol no tiene permiso para esta sección.")
    enlace("vistas/panel.py", "← Volver al panel público", "📊")
    return False


def formulario_login() -> None:
    try:
        creado = us.inicializar_desde_clave(clave_inicial())
    except us.UsuariosError as exc:
        st.error(str(exc))
        return
    if creado:
        st.success("Primer arranque: se creó el usuario **admin** con la clave de `.streamlit/secrets.toml`.")

    if not us.hay_usuarios():
        _formulario_primer_administrador()
        return

    u = usuario_actual()
    if u is not None:
        st.success(f"Sesión iniciada como **{u.nombre}** ({u.rol}). {us.DESCRIPCION_ROL[u.rol]}")
        c1, c2 = st.columns(2)
        if c1.button("Ir al panel administrador", type="primary", width="stretch"):
            ir_a_panel_admin()
        if c2.button("Cerrar sesión", width="stretch"):
            cerrar_sesion()
            st.rerun()
        return

    fallos = st.session_state.get(_KEY_FALLOS, 0)
    bloqueado_hasta = st.session_state.get("mh_bloqueo", 0.0)
    if time.time() < bloqueado_hasta:
        st.warning(f"Demasiados intentos. Espera {int(bloqueado_hasta - time.time())} segundos.")
        return

    with st.form("login", border=False):
        nombre = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
    if enviar:
        u = us.verificar(nombre, clave)
        if u is None:
            fallos += 1
            st.session_state[_KEY_FALLOS] = fallos
            if fallos >= MAX_INTENTOS:
                st.session_state["mh_bloqueo"] = time.time() + ESPERA_SEG
                st.session_state[_KEY_FALLOS] = 0
            st.error("Usuario o contraseña incorrectos.")
            return
        st.session_state[_KEY] = {"nombre": u.nombre, "rol": u.rol}
        st.session_state[_KEY_FALLOS] = 0
        ir_a_panel_admin()          # entra directo al panel del administrador


def _formulario_primer_administrador() -> None:
    """Primer arranque sin secrets.toml: se crea aquí la cuenta del administrador."""
    st.info(
        "**Primer arranque.** Todavía no hay cuentas: crea la del administrador. "
        "Con ella podrás subir reportes y crear más usuarios."
    )
    with st.form("primer_admin", border=False):
        nombre = st.text_input("Usuario", value="admin")
        clave = st.text_input("Contraseña", type="password")
        clave2 = st.text_input("Repite la contraseña", type="password")
        crear = st.form_submit_button("Crear administrador", type="primary", width="stretch")
    if not crear:
        return
    if clave != clave2:
        st.error("Las contraseñas no coinciden.")
        return
    try:
        u = us.crear(nombre, clave, "administrador", creado_por="primer arranque")
    except us.UsuariosError as exc:
        st.error(str(exc))
        return
    st.session_state[_KEY] = {"nombre": u.nombre, "rol": u.rol}
    st.session_state[_KEY_FALLOS] = 0
    ir_a_panel_admin()


def ir_a_panel_admin() -> None:
    """Salta a la página de administración. Fuera de st.navigation (pruebas)
    st.switch_page falla: en ese caso solo se vuelve a ejecutar la página."""
    try:
        st.switch_page(PAGINA_ADMIN)
    except Exception:
        st.rerun()
