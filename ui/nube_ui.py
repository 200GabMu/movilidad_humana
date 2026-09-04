"""Piezas de interfaz para la copia de seguridad en GitHub (core/nube.py)."""

from __future__ import annotations

import streamlit as st

from core import nube


@st.cache_resource(show_spinner="Recuperando los datos guardados en GitHub…")
def arranque():
    """Se ejecuta una sola vez por proceso: trae `data/` desde la rama de datos
    (GitHub manda) y conserva lo que solo exista en el disco."""
    try:
        return nube.sincronizar_al_arrancar()
    except Exception as exc:  # nunca debe impedir que la app arranque
        return nube.ResultadoSync(errores=[str(exc)])


def sincronizar_con_aviso(mensaje: str) -> None:
    """Sube los cambios de `data/` a GitHub mostrando progreso y resultado.
    Sin configuración no hace nada (uso en el computador)."""
    if not nube.activa():
        return
    barra = st.progress(0, text="Guardando copia en GitHub…")

    def progreso(i, total, ruta):
        barra.progress(i / max(total, 1), text=f"Guardando copia en GitHub… {i}/{total}")

    res = nube.sincronizar(mensaje, progreso=progreso)
    barra.empty()
    if res.errores:
        st.warning("⚠️ La copia en GitHub no se completó: " + " · ".join(res.errores[:3])
                   + ("…" if len(res.errores) > 3 else "") + ". Los datos sí quedaron guardados en esta app; "
                   "vuelve a intentarlo con **Sincronizar ahora** en el panel administrador.")
    else:
        st.toast(f"☁️ Copia en GitHub actualizada ({res.resumen()}).", icon="✅")


def _texto_arranque(res) -> str | None:
    """Resumen de lo que pasó al arrancar (para que se vea si GitHub se leyó)."""
    if res is None:
        return None
    if res.errores:
        return "⚠️ Al arrancar no se pudo leer GitHub: " + res.errores[0]
    if res.subidos:
        return f"Al arrancar se recuperaron {len(res.subidos)} archivo(s) desde GitHub."
    return "Al arrancar, el disco ya coincidía con GitHub."


def tarjeta_estado() -> None:
    """Bloque para el panel administrador: estado de la copia, qué pasó al
    arrancar y botones manuales (subir / recuperar)."""
    if not nube.activa():
        return
    est = nube.estado()
    if est.get("error"):
        st.error(f"☁️ Copia en GitHub con error: {est['error']}")
    else:
        st.success(
            f"☁️ **Copia en GitHub activa** (rama `{est['rama']}`): {est['versiones']} versión(es), "
            f"{est['archivos']} archivo(s). Cada unificación se guarda allí de forma permanente."
        )
    detalle = _texto_arranque(arranque())
    if detalle:
        st.caption(detalle)
    c1, c2 = st.columns(2)
    if c1.button("🔄 Subir a GitHub", key="btn_sync_nube", width="stretch",
                 help="Sube a GitHub lo que haya cambiado en esta app."):
        sincronizar_con_aviso("Sincronización manual desde el panel")
        st.rerun()
    if c2.button("⬇️ Recuperar desde GitHub", key="btn_restaurar_nube", width="stretch",
                 help="Trae a esta app todas las versiones guardadas en GitHub (no borra nada)."):
        with st.spinner("Recuperando desde GitHub…"):
            res = nube.sincronizar_al_arrancar()
        if res is None or res.errores:
            st.error("No se pudo recuperar: " + (res.errores[0] if res else "sin configuración"))
        else:
            st.cache_data.clear()
            arranque.clear()
            st.toast(f"⬇️ Recuperado desde GitHub ({res.resumen()}).", icon="✅")
            st.rerun()
