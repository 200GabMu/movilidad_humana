"""Página: historial de versiones (restaurar, descargar, eliminar)."""

import pandas as pd
import streamlit as st

from core import almacen
from core.exportar import to_excel_bytes
from ui import auth, nube_ui
from ui.componentes import boton_pagina, enlace, marcar_admin, portada

marcar_admin()

if not auth.requiere("historial"):
    st.stop()

with portada("Administración · Movilidad Humana", "Historial y copias de seguridad", "Cada unificación crea una versión nueva. Activar una versión anterior es la forma de deshacer una subida equivocada: el panel pasa a leer esa versión y la otra queda aquí por si hace falta revisarla."):
    b1, b2, _ = st.columns([1.4, 1.2, 6])
    with b1:
        boton_pagina("vistas/unificar.py", "Panel administrador")
    if b2.button("Cerrar sesión"):
        auth.cerrar_sesion()
        st.rerun()

puede_activar = auth.puede("activar")
puede_eliminar = auth.puede("eliminar")

try:
    versiones = almacen.listar_versiones()
    activa_id = almacen.id_activa()
except almacen.AlmacenError as exc:
    st.error(f"No se pudo leer el historial: {exc}")
    st.stop()

if not versiones:
    st.info("Todavía no hay versiones. Sube archivos en **📤 Unificar reportes**.")
    st.stop()


# ── Tabla resumen ───────────────────────────────────────────────────────────
tabla = pd.DataFrame([
    {
        "Activa": "✅" if v.id == activa_id else "",
        "Versión": v.id,
        "Fecha": v.fecha_legible,
        "Modo": v.modo,
        "Hojas nuevas": v.hojas,
        "Filas": v.filas,
        "Columnas": v.columnas,
        "Archivos": len(v.archivos),
        "Subido por": v.usuario,
        "Nota": v.nota,
    }
    for v in versiones
])
st.dataframe(tabla, width="stretch", hide_index=True)

st.divider()

# ── Detalle / acciones por versión ──────────────────────────────────────────
ids = [v.id for v in versiones]
etiquetas = {v.id: f"{'✅ ' if v.id == activa_id else ''}{v.id} · {v.fecha_legible} · {v.filas:,} filas" for v in versiones}
sel = st.selectbox("Selecciona una versión", ids, format_func=lambda i: etiquetas[i])
v = almacen.obtener_version(sel)
es_activa = v.id == activa_id

c1, c2, c3 = st.columns(3)
c1.metric("Filas", f"{v.filas:,}")
c2.metric("Hojas nuevas en esta subida", v.hojas)
c3.metric("Espacio en disco", f"{almacen.tamaño_en_disco(v.id) / 1024:.0f} KB")
st.caption(
    f"Modo: **{v.modo}**"
    + (f" · sobre la versión {v.base}" if v.base else "")
    + f" · {len(v.archivos)} archivo(s) subido(s)"
    + (f" · subido por **{v.usuario}**" if v.usuario else "")
)
if v.archivos:
    with st.expander(f"📄 Ver los {len(v.archivos)} archivos de esta versión"):
        st.dataframe(pd.DataFrame({"Archivo": sorted(v.archivos)}), width="stretch", hide_index=True, height=260)

# Nota editable
nueva_nota = st.text_input("Nota", value=v.nota, key=f"nota_{v.id}")
if nueva_nota != v.nota and st.button("💾 Guardar nota"):
    almacen.actualizar_nota(v.id, nueva_nota)
    nube_ui.sincronizar_con_aviso(f"Nota de la versión {v.id}")
    st.rerun()

st.markdown("**Acciones**")
a1, a2, a3, a4 = st.columns(4)

with a1:
    if es_activa:
        st.button("✅ Es la versión activa", disabled=True, width="stretch")
    elif not puede_activar:
        st.button("↩️ Activar (solo administrador)", disabled=True, width="stretch")
    elif st.button("↩️ Activar esta versión", type="primary", width="stretch"):
        try:
            almacen.activar_version(v.id)
            st.success(f"Versión {v.id} activada.")
            nube_ui.sincronizar_con_aviso(f"Versión activa: {v.id}")
            st.rerun()
        except almacen.AlmacenError as exc:
            st.error(str(exc))

with a2:
    try:
        st.download_button(
            "⬇️ Consolidado limpio (.xlsx)",
            data=to_excel_bytes(almacen.cargar(v.id, almacen.TIPO_LIMPIO)),
            file_name=f"CONSOLIDADO_FINAL_{v.id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    except almacen.AlmacenError as exc:
        st.error(str(exc))

with a3:
    try:
        st.download_button(
            "⬇️ Consolidado crudo (.xlsx)",
            data=to_excel_bytes(almacen.cargar(v.id, almacen.TIPO_CRUDO)),
            file_name=f"CONSOLIDADO_CRUDO_{v.id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    except almacen.AlmacenError as exc:
        st.error(str(exc))

with a4:
    if es_activa or not puede_eliminar:
        st.button("🗑️ Eliminar", disabled=True,
                  help="No se puede eliminar la versión activa" if es_activa else "Solo un administrador puede eliminar",
                  width="stretch")
    else:
        confirmar = st.checkbox("Confirmo eliminar", key=f"conf_{v.id}")
        if st.button("🗑️ Eliminar versión", disabled=not confirmar, width="stretch"):
            try:
                almacen.eliminar_version(v.id)
                st.success(f"Versión {v.id} eliminada.")
                nube_ui.sincronizar_con_aviso(f"Versión eliminada: {v.id}")
                st.rerun()
            except almacen.AlmacenError as exc:
                st.error(str(exc))

originales = almacen.originales_de(v.id)
if originales:
    with st.expander(f"📎 Archivos originales de esta subida ({len(originales)})"):
        for ruta in originales:
            st.download_button(
                f"⬇️ {ruta.name}",
                data=ruta.read_bytes(),
                file_name=ruta.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"orig_{v.id}_{ruta.name}",
            )
