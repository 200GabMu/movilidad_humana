"""Piezas de interfaz para la copia de seguridad en GitHub (core/nube.py)."""

from __future__ import annotations

import streamlit as st

from core import nube


@st.cache_resource(show_spinner="Recuperando los datos guardados en GitHub…")
def arranque():
    """Se ejecuta una sola vez por proceso: si el disco está vacío (reinicio
    de Streamlit Cloud) descarga `data/` desde la rama de datos."""
    try:
        return nube.restaurar_si_vacio()
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


def tarjeta_estado() -> None:
    """Bloque para el panel administrador: estado de la copia y botón manual."""
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
    if st.button("🔄 Sincronizar ahora", key="btn_sync_nube", width="stretch"):
        sincronizar_con_aviso("Sincronización manual desde el panel")
        st.rerun()
