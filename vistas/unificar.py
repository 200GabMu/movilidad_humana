"""Panel administrador: subir reportes (unificar) · datos actuales · descargas.

Cada subida crea una versión nueva en el historial (copia de seguridad).
Modo normal = AGREGAR: solo entran las hojas nuevas y se suman a lo guardado.
"""

import streamlit as st

from core import almacen, pipeline
from core.exportar import to_excel_bytes
from core.ortografia import valores_unicos
from observatorio.medidas import formato_entero, total_personas
from ui import auth, nube_ui
from core import nube
from ui.componentes import boton_pagina, enlace, marcar_admin, portada, tabla_datos, tarjeta
from ui.estilos import mostrar_mensajes

marcar_admin()

if not auth.requiere("subir"):
    st.stop()
usuario = auth.usuario_actual()
puede_reemplazar = auth.puede("reemplazar")


def _en_la_nube() -> bool:
    """True si en los Secrets de Streamlit Cloud está NUBE = true."""
    try:
        return str(st.secrets.get("NUBE", "")).strip().lower() in {"true", "1", "si", "sí"}
    except (FileNotFoundError, AttributeError):
        return False




@st.cache_data(show_spinner=False)
def excel_version(id_version: str, tipo: str) -> bytes:
    return to_excel_bytes(almacen.cargar(id_version, tipo))


@st.cache_data(show_spinner=False)
def resumen_version(id_version: str) -> dict:
    df = almacen.cargar(id_version, almacen.TIPO_LIMPIO)
    try:
        personas = formato_entero(total_personas(df))
    except Exception:  # falta alguna columna de identidad
        personas = "—"
    return {"registros": formato_entero(len(df)), "columnas": len(df.columns), "personas": personas,
            "archivos_origen": df["Nombre del Archivo"].nunique() if "Nombre del Archivo" in df.columns else "—"}


activa = almacen.version_activa()

# ── Portada ─────────────────────────────────────────────────────────────────
with portada(
    "Administración · Movilidad Humana",
    "Actualizar datos del panel",
    "Sube los reportes mensuales en Excel (.xlsx). El sistema los unifica con lo que ya está guardado, "
    "corrige la ortografía, guarda una copia de seguridad de la versión anterior y actualiza el panel al instante.",
):
    b1, b3, b2, _ = st.columns([1.2, 1.5, 1.2, 5])
    with b1:
        boton_pagina("vistas/panel.py", "Ver panel")
    with b3:
        boton_pagina("vistas/persona.py", "🔍 Buscar persona", primario=False, key="btn_buscar_persona")
    if b2.button("Cerrar sesión"):
        auth.cerrar_sesion()
        st.rerun()

# ── Tres tarjetas ───────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    with tarjeta("Subir Excel de reportes"):
        archivos_subidos = st.file_uploader("Archivos Excel (.xlsx)", type=["xlsx"], accept_multiple_files=True)
        opciones_modo = ["Agregar a lo ya guardado", "Reemplazar todo (empezar de cero)"]
        modo_etiqueta = st.radio(
            "¿Qué hacer con los datos guardados?", opciones_modo, index=0,
            disabled=activa is None or not puede_reemplazar,
            help="Agregar: entran solo las hojas nuevas y se suman a lo que ya estaba; las repetidas se omiten. "
                 "Reemplazar: el consolidado queda únicamente con lo que subas ahora (la versión anterior sigue en el Historial). "
                 "Reemplazar solo lo puede hacer un administrador.",
        )
        modo = almacen.MODO_AGREGAR
        if activa is None or (modo_etiqueta.startswith("Reemplazar") and puede_reemplazar):
            modo = almacen.MODO_REEMPLAZAR
        nota = st.text_input("Nota para el historial (opcional)", placeholder="Ej.: reporte de agosto 2026")
        corregir_enc = st.checkbox("Corregir ortografía de los encabezados", value=True,
                                   help="ACOGIMINETO → ACOGIMIENTO, Parentesto → Parentesco… Desactívalo solo si otro "
                                        "sistema lee el archivo con los nombres originales.")
        ejecutar = st.button("Unificar y actualizar", type="primary", disabled=not archivos_subidos, width="stretch")
        st.markdown(
            '<div class="mh-tarjeta-texto">Cada hoja «REPORTE MENSUAL …» del libro se toma como un mes. '
            "Las hojas que ya estén guardadas (mismo año, hoja y número de filas) se omiten automáticamente, "
            "así puedes subir el archivo completo cada mes sin duplicar.</div>",
            unsafe_allow_html=True,
        )
        # Copia de seguridad en GitHub (o aviso si estamos en la nube sin copia)
        if nube.activa():
            nube_ui.tarjeta_estado()
        elif _en_la_nube():
            st.warning(
                "☁️ **Copia publicada en Streamlit Cloud.** El disco es temporal: lo que subas aquí se "
                "pierde al reiniciar. Configura la copia en GitHub (GITHUB_TOKEN y GITHUB_REPO en "
                "Settings → Secrets; ver README) para que se guarde para siempre."
            )

with c2:
    with tarjeta("Datos actuales"):
        if activa is None:
            st.info("Todavía no hay datos guardados. Sube el primer Excel.")
        else:
            r = resumen_version(activa.id)
            tabla_datos([
                ("Versión", activa.id.replace("v_", "")),
                ("Actualizado", activa.fecha_legible),
                ("Subido por", activa.usuario or "—"),
                ("Registros", r["registros"]),
                ("Personas únicas", r["personas"]),
                ("Columnas", str(r["columnas"])),
                ("Archivos de origen", str(r["archivos_origen"])),
                ("Versiones guardadas", str(len(almacen.listar_versiones()))),
            ])

with c3:
    with tarjeta("Descargas e historial",
                 "Descarga el consolidado con los datos actuales del panel o revisa las versiones anteriores."):
        if activa is not None:
            st.download_button("⬇️ Consolidado limpio y corregido (.xlsx)",
                               data=excel_version(activa.id, almacen.TIPO_LIMPIO),
                               file_name=f"REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL_{activa.id}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
            st.download_button("⬇️ Consolidado crudo, sin limpiar (.xlsx)",
                               data=excel_version(activa.id, almacen.TIPO_CRUDO),
                               file_name=f"CONSOLIDADO_CRUDO_{activa.id}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        enlace("vistas/historial.py", "Historial y copias de seguridad", "🗂️")
        if auth.puede("usuarios"):
            enlace("vistas/usuarios.py", "Usuarios y permisos", "👥")

# ── Proceso ─────────────────────────────────────────────────────────────────
if ejecutar and archivos_subidos:
    barra = st.progress(0, text="Iniciando…")
    with st.spinner("Unificando, limpiando y guardando…"):
        archivos = [(f.name, f.getvalue()) for f in archivos_subidos]
        resultado = pipeline.ejecutar(
            archivos, modo=modo, nota=nota,
            progreso=lambda frac, txt: barra.progress(frac, text=txt),
            corregir_encabezados=corregir_enc,
            usuario=usuario.nombre if usuario else "",
        )
    barra.empty()
    st.session_state["mh_ultimo_resultado"] = resultado
    if resultado.ok:
        st.cache_data.clear()   # los datos actuales y descargas deben reflejar la versión nueva
        nube_ui.sincronizar_con_aviso(f"Versión {resultado.version.id}: {nota or 'unificación'}")
        st.rerun()

resultado = st.session_state.pop("mh_ultimo_resultado", None)
if resultado is None:
    st.stop()

st.divider()
with st.expander("📋 Detalle del proceso (hojas incluidas, omitidas, avisos)", expanded=not resultado.ok):
    mostrar_mensajes(resultado.mensajes)

if not resultado.ok:
    for m in resultado.mensajes:          # el motivo, visible sin abrir el detalle
        if m.nivel == "error":
            st.error(m.texto)
    if resultado.df_limpio is not None:
        st.warning("Puedes descargar el resultado mientras se resuelve el problema de guardado:")
        st.download_button("⬇️ Descargar consolidado limpio (.xlsx)", data=to_excel_bytes(resultado.df_limpio),
                           file_name="REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.stop()

v = resultado.version
st.success(f"✅ Versión **{v.id}** guardada y activada ({v.fecha_legible}). El panel ya muestra los datos nuevos.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Hojas nuevas incluidas", resultado.consolidacion.hojas_incluidas)
m2.metric("Filas nuevas", f"{resultado.consolidacion.filas:,}")
m3.metric("Total filas", f"{len(resultado.df_limpio):,}")
m4.metric("Celdas corregidas", f"{resultado.stats.get('celdas_ortografia', 0):,}")
if resultado.stats.get("columnas_agregadas"):
    st.info("Columnas de la plantilla que no venían y se agregaron vacías: "
            + ", ".join(f"`{c}`" for c in resultado.stats["columnas_agregadas"]))
if resultado.stats.get("columnas_extra"):
    st.info("Columnas fuera de la plantilla conservadas al final: "
            + ", ".join(f"`{c}`" for c in resultado.stats["columnas_extra"]))

with st.expander("🔤 Valores únicos por columna (para revisar variantes que aún queden)"):
    tabla_valores = valores_unicos(resultado.df_limpio)
    st.dataframe(tabla_valores, width="stretch", height=300)
    st.download_button("⬇️ Descargar valores únicos (.xlsx)", data=to_excel_bytes(tabla_valores, sheet_name="VALORES"),
                       file_name=f"VALORES_UNICOS_{v.id}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with st.expander("📋 Resumen por archivo y hoja"):
    st.dataframe(resultado.df_limpio.groupby(["Nombre del Archivo", "Nombre de la Hoja"]).size().reset_index(name="Filas"),
                 width="stretch")
st.subheader("Vista previa (primeras 100 filas)")
st.dataframe(resultado.df_limpio.head(100), width="stretch", height=350)
