"""Página (solo administradores): crear cuentas, cambiar rol/clave, desactivar, eliminar."""

import pandas as pd
import streamlit as st

from core import usuarios as us
from ui import auth, nube_ui
from ui.componentes import boton_pagina, enlace, marcar_admin, portada

marcar_admin()

if not auth.requiere("usuarios"):
    st.stop()

with portada("Administración · Movilidad Humana", "Usuarios y permisos", "Crea las cuentas del personal que sube reportes y define qué puede hacer cada una. El Panel es público: nadie necesita cuenta para verlo."):
    b1, b2, _ = st.columns([1.4, 1.2, 6])
    with b1:
        boton_pagina("vistas/unificar.py", "Panel administrador")
    if b2.button("Cerrar sesión"):
        auth.cerrar_sesion()
        st.rerun()


yo = auth.usuario_actual()

st.markdown(
    "**Roles disponibles**\n\n"
    + "\n".join(f"- **{rol}**: {desc}" for rol, desc in us.DESCRIPCION_ROL.items())
    + "\n\nEl **Panel** es público: nadie necesita cuenta para verlo."
)

# ── Lista ───────────────────────────────────────────────────────────────────
try:
    lista = us.listar()
except us.UsuariosError as exc:
    st.error(str(exc))
    st.stop()

tabla = pd.DataFrame([
    {
        "Usuario": u.nombre, "Rol": u.rol, "Activo": "✅" if u.activo else "⛔",
        "Creado": u.creado[:16].replace("T", " "), "Creado por": u.creado_por,
        "Último acceso": u.ultimo_acceso[:16].replace("T", " "),
    }
    for u in lista
])
st.dataframe(tabla, width="stretch", hide_index=True)

# ── Crear ───────────────────────────────────────────────────────────────────
st.subheader("Crear cuenta")
with st.form("crear_usuario", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 2, 1.5])
    nombre = c1.text_input("Usuario", placeholder="ej. maria.lopez", help="minúsculas, números, punto, guion")
    clave = c2.text_input("Contraseña", type="password", help=f"mínimo {us.MIN_CLAVE} caracteres")
    rol = c3.selectbox("Rol", list(us.ROLES), index=1)
    crear = st.form_submit_button("➕ Crear", type="primary")
if crear:
    try:
        u = us.crear(nombre, clave, rol, creado_por=yo.nombre)
        st.success(f"Cuenta **{u.nombre}** creada con rol *{u.rol}*. Entrégale la contraseña por un medio seguro.")
        nube_ui.sincronizar_con_aviso("Usuario creado")
        st.rerun()
    except us.UsuariosError as exc:
        st.error(str(exc))

# ── Editar ──────────────────────────────────────────────────────────────────
st.subheader("Modificar una cuenta")
nombres = [u.nombre for u in lista]
sel = st.selectbox("Cuenta", nombres)
u = next(x for x in lista if x.nombre == sel)
es_yo = u.nombre == yo.nombre

e1, e2, e3, e4 = st.columns(4)

with e1:
    st.markdown("**Cambiar contraseña**")
    nueva = st.text_input("Nueva contraseña", type="password", key=f"nc_{sel}")
    if st.button("💾 Guardar clave", key=f"bc_{sel}", width="stretch"):
        try:
            us.cambiar_clave(u.nombre, nueva)
            st.success("Contraseña actualizada.")
            nube_ui.sincronizar_con_aviso("Contraseña de usuario actualizada")
        except us.UsuariosError as exc:
            st.error(str(exc))

with e2:
    st.markdown("**Cambiar rol**")
    nuevo_rol = st.selectbox("Rol", list(us.ROLES), index=list(us.ROLES).index(u.rol), key=f"r_{sel}",
                             label_visibility="collapsed")
    if st.button("💾 Guardar rol", key=f"br_{sel}", width="stretch", disabled=nuevo_rol == u.rol):
        try:
            us.cambiar_rol(u.nombre, nuevo_rol)
            st.success("Rol actualizado.")
            nube_ui.sincronizar_con_aviso("Rol de usuario actualizado")
            st.rerun()
        except us.UsuariosError as exc:
            st.error(str(exc))

with e3:
    st.markdown("**Activar / desactivar**")
    st.caption("Desactivar bloquea el acceso sin borrar la cuenta.")
    etiqueta = "⛔ Desactivar" if u.activo else "✅ Activar"
    if st.button(etiqueta, key=f"ba_{sel}", width="stretch", disabled=es_yo):
        try:
            us.activar(u.nombre, not u.activo)
            nube_ui.sincronizar_con_aviso("Usuario activado/desactivado")
            st.rerun()
        except us.UsuariosError as exc:
            st.error(str(exc))

with e4:
    st.markdown("**Eliminar**")
    conf = st.checkbox("Confirmo eliminar", key=f"ce_{sel}", disabled=es_yo)
    if st.button("🗑️ Eliminar cuenta", key=f"be_{sel}", width="stretch", disabled=not conf or es_yo):
        try:
            us.eliminar(u.nombre)
            st.success(f"Cuenta {u.nombre} eliminada.")
            nube_ui.sincronizar_con_aviso("Usuario eliminado")
            st.rerun()
        except us.UsuariosError as exc:
            st.error(str(exc))

if es_yo:
    st.caption("No puedes desactivar ni eliminar tu propia cuenta (sí cambiar tu contraseña).")
