"""
Flujo completo de una subida: unificar -> (fusionar con lo anterior) ->
limpiar -> guardar versión. Es lo que llama la página "Unificar"; también
sirve desde consola:  python -m core.pipeline archivo1.xlsx archivo2.xlsx
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import almacen
from .consolidacion import Mensaje, ResultadoConsolidacion, claves_de, fusionar, unify_files
from .limpieza import procesar_limpieza_y_relleno


@dataclass
class ResultadoPipeline:
    version: almacen.Version | None
    consolidacion: ResultadoConsolidacion
    df_crudo: pd.DataFrame | None = None
    df_limpio: pd.DataFrame | None = None
    stats: dict = field(default_factory=dict)
    mensajes: list[Mensaje] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.version is not None


def ejecutar(
    archivos: list[tuple[str, bytes]],
    modo: str = almacen.MODO_AGREGAR,
    nota: str = "",
    progreso=None,
    corregir_encabezados: bool = True,
    usuario: str = "",
) -> ResultadoPipeline:
    # 1) ¿Sobre qué base trabajamos?
    df_base: pd.DataFrame | None = None
    claves_existentes: set[tuple] = set()
    if modo == almacen.MODO_AGREGAR:
        try:
            df_base = almacen.cargar_activa(almacen.TIPO_CRUDO)
        except almacen.AlmacenError as exc:
            return ResultadoPipeline(
                version=None,
                consolidacion=ResultadoConsolidacion(df=None),
                mensajes=[Mensaje("error", f"No pude leer la versión activa: {exc}")],
            )
        claves_existentes = claves_de(df_base)

    # 2) Unificar lo subido (omitiendo hojas repetidas)
    res = unify_files(archivos, claves_existentes=claves_existentes, progreso=progreso)
    salida = ResultadoPipeline(version=None, consolidacion=res, mensajes=list(res.mensajes))
    if res.df is None:
        return salida

    # 3) Fusionar con la base (modo agregar) y limpiar TODO junto: el relleno
    #    por Nombre+Apellido aprovecha los datos de meses anteriores.
    df_crudo = fusionar(df_base, res.df) if modo == almacen.MODO_AGREGAR else res.df
    try:
        df_limpio, stats = procesar_limpieza_y_relleno(df_crudo, corregir_encabezados=corregir_encabezados)
    except ValueError as exc:
        salida.mensajes.append(Mensaje("error", str(exc)))
        return salida

    # 4) Guardar versión nueva (copia de seguridad automática)
    try:
        version = almacen.guardar_version(
            df_crudo=df_crudo,
            df_limpio=df_limpio,
            modo=modo,
            archivos=archivos,
            hojas=res.hojas_incluidas,
            nota=nota,
            stats={**stats, "hojas_nuevas": res.hojas_incluidas, "filas_nuevas": res.filas},
            usuario=usuario,
        )
    except Exception as exc:  # disco lleno, permisos, parquet…
        salida.mensajes.append(Mensaje("error", f"Se unificó pero NO se pudo guardar la versión. Motivo: {exc}"))
        salida.df_crudo, salida.df_limpio, salida.stats = df_crudo, df_limpio, stats
        return salida

    salida.version = version
    salida.df_crudo = df_crudo
    salida.df_limpio = df_limpio
    salida.stats = stats
    salida.mensajes.append(Mensaje(
        "success",
        f"Versión **{version.id}** guardada y activada: "
        f"{len(df_limpio):,} filas · {len(df_limpio.columns)} columnas.",
    ))
    return salida


if __name__ == "__main__":  # uso por consola
    import sys
    from pathlib import Path

    rutas = [Path(p) for p in sys.argv[1:]]
    if not rutas:
        print("Uso: python -m core.pipeline archivo1.xlsx [archivo2.xlsx …]")
        sys.exit(1)
    r = ejecutar([(p.name, p.read_bytes()) for p in rutas])
    for m in r.mensajes:
        print(f"[{m.nivel}] {m.texto}")
    sys.exit(0 if r.ok else 2)
