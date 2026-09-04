"""
Almacén de versiones (historial + copias de seguridad).

Cada vez que se unifica se crea una VERSIÓN nueva en disco:

    data/
    ├── historial.json                 # lista de versiones + cuál está activa
    └── versiones/
        └── v_20260903_141522/
            ├── crudo.parquet          # consolidado tal cual sale de los Excel
            ├── limpio.parquet         # consolidado tras el Paso 2 (lo lee el panel)
            ├── meta.json              # qué se subió, cuántas filas, nota, etc.
            └── originales/            # copia de los .xlsx que se subieron
                └── REPORTE 2026.xlsx

Nunca se sobrescribe una versión: si alguien sube algo equivocado, se
"activa" la versión anterior desde la página Historial y listo.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

# Carpeta de datos: por defecto ./data; se puede mover con la variable de
# entorno MH_DATA_DIR (p. ej. a un disco con respaldo automático).
RAIZ_DATA = Path(os.environ.get("MH_DATA_DIR") or Path(__file__).resolve().parent.parent / "data")
DIR_VERSIONES = RAIZ_DATA / "versiones"
ARCHIVO_HISTORIAL = RAIZ_DATA / "historial.json"

TIPO_CRUDO = "crudo"
TIPO_LIMPIO = "limpio"
MODO_AGREGAR = "agregar"     # nuevas hojas + lo que ya había
MODO_REEMPLAZAR = "reemplazar"  # empezar de cero con lo subido


@dataclass
class Version:
    id: str
    fecha: str                       # ISO
    modo: str
    archivos: list[str]
    hojas: int
    filas: int
    columnas: int
    nota: str = ""
    base: str | None = None          # id de la versión sobre la que se agregó
    stats: dict = field(default_factory=dict)
    usuario: str = ""                # quién hizo la subida

    @property
    def fecha_legible(self) -> str:
        try:
            return datetime.fromisoformat(self.fecha).strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return self.fecha


class AlmacenError(Exception):
    pass


# ── Historial ────────────────────────────────────────────────────────────────

def _leer_historial() -> dict:
    if not ARCHIVO_HISTORIAL.exists():
        return {"activa": None, "versiones": []}
    try:
        data = json.loads(ARCHIVO_HISTORIAL.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AlmacenError(f"historial.json está dañado: {exc}") from exc
    data.setdefault("activa", None)
    data.setdefault("versiones", [])
    return data


def _escribir_historial(data: dict) -> None:
    RAIZ_DATA.mkdir(parents=True, exist_ok=True)
    tmp = ARCHIVO_HISTORIAL.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ARCHIVO_HISTORIAL)  # escritura atómica: no queda a medias si se corta


def listar_versiones() -> list[Version]:
    """Más reciente primero."""
    data = _leer_historial()
    versiones = [Version(**v) for v in data["versiones"]]
    return sorted(versiones, key=lambda v: v.fecha, reverse=True)


def id_activa() -> str | None:
    return _leer_historial()["activa"]


def version_activa() -> Version | None:
    act = id_activa()
    if act is None:
        return None
    return next((v for v in listar_versiones() if v.id == act), None)


def obtener_version(id_version: str) -> Version:
    v = next((v for v in listar_versiones() if v.id == id_version), None)
    if v is None:
        raise AlmacenError(f"No existe la versión {id_version}")
    return v


# ── Lectura / escritura de datos ─────────────────────────────────────────────

def _ruta(id_version: str, tipo: str) -> Path:
    if tipo not in (TIPO_CRUDO, TIPO_LIMPIO):
        raise AlmacenError(f"Tipo inválido: {tipo}")
    return DIR_VERSIONES / id_version / f"{tipo}.parquet"


def cargar(id_version: str, tipo: str = TIPO_LIMPIO) -> pd.DataFrame:
    ruta = _ruta(id_version, tipo)
    if not ruta.exists():
        raise AlmacenError(f"No se encontró {ruta.name} de la versión {id_version}")
    return pd.read_parquet(ruta)


def cargar_activa(tipo: str = TIPO_LIMPIO) -> pd.DataFrame | None:
    act = id_activa()
    if act is None:
        return None
    return cargar(act, tipo)


def _nombres_unicos(columnas) -> list[str]:
    """Parquet no admite dos columnas con el mismo nombre: se numeran."""
    vistos: dict[str, int] = {}
    salida = []
    for c in columnas:
        c = str(c)
        if c in vistos:
            vistos[c] += 1
            salida.append(f"{c}__{vistos[c]}")
        else:
            vistos[c] = 0
            salida.append(c)
    return salida


def _a_texto(x):
    if x is None:
        return None
    if isinstance(x, (pd.Timestamp, datetime)):
        return None if pd.isna(x) else x.strftime("%Y-%m-%d")
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):  # listas u objetos raros: no son "na"
        pass
    return str(x)


def _preparar_para_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Parquet exige un solo tipo por columna y nombres únicos: todo lo que
    no sea fecha se guarda como texto (los datos vienen de Excel como str)."""
    df = df.copy()
    df.columns = _nombres_unicos(df.columns)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        df[col] = df[col].map(_a_texto).astype(object)
    return df


def _guardar_parquet(df: pd.DataFrame, ruta: Path) -> None:
    try:
        _preparar_para_parquet(df).to_parquet(ruta, index=False)
    except Exception as exc:
        raise AlmacenError(
            f"No se pudo escribir {ruta.name}: {exc}. "
            "Revisa que la carpeta 'data' exista y no sea de solo lectura, y que pyarrow esté instalado."
        ) from exc


def guardar_version(
    df_crudo: pd.DataFrame,
    df_limpio: pd.DataFrame,
    modo: str,
    archivos: list[tuple[str, bytes]],
    hojas: int,
    nota: str = "",
    stats: dict | None = None,
    activar: bool = True,
    usuario: str = "",
) -> Version:
    """Crea una versión nueva (nunca pisa una existente) y la deja activa."""
    if modo not in (MODO_AGREGAR, MODO_REEMPLAZAR):
        raise AlmacenError(f"Modo inválido: {modo}")

    ahora = datetime.now()
    id_version = "v_" + ahora.strftime("%Y%m%d_%H%M%S")
    carpeta = DIR_VERSIONES / id_version
    if carpeta.exists():  # dos guardados en el mismo segundo
        id_version += "_" + ahora.strftime("%f")
        carpeta = DIR_VERSIONES / id_version

    try:
        (carpeta / "originales").mkdir(parents=True, exist_ok=False)
        _guardar_parquet(df_crudo, carpeta / "crudo.parquet")
        _guardar_parquet(df_limpio, carpeta / "limpio.parquet")
        for nombre, contenido in archivos:
            destino = carpeta / "originales" / Path(nombre).name
            destino.write_bytes(contenido)

        version = Version(
            id=id_version,
            fecha=ahora.isoformat(timespec="seconds"),
            modo=modo,
            archivos=[Path(n).name for n, _ in archivos],
            hojas=hojas,
            filas=int(len(df_limpio)),
            columnas=int(len(df_limpio.columns)),
            nota=nota.strip(),
            base=id_activa() if modo == MODO_AGREGAR else None,
            stats=stats or {},
            usuario=usuario,
        )
        (carpeta / "meta.json").write_text(
            json.dumps(asdict(version), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        data = _leer_historial()
        data["versiones"].append(asdict(version))
        if activar:
            data["activa"] = id_version
        _escribir_historial(data)
        return version
    except Exception:
        shutil.rmtree(carpeta, ignore_errors=True)  # no dejar versiones a medias
        raise


def activar_version(id_version: str) -> None:
    """Restaurar: la versión indicada pasa a ser la que lee el panel."""
    data = _leer_historial()
    if not any(v["id"] == id_version for v in data["versiones"]):
        raise AlmacenError(f"No existe la versión {id_version}")
    if not _ruta(id_version, TIPO_LIMPIO).exists():
        raise AlmacenError(f"La versión {id_version} no tiene datos en disco")
    data["activa"] = id_version
    _escribir_historial(data)


def eliminar_version(id_version: str) -> None:
    data = _leer_historial()
    if data["activa"] == id_version:
        raise AlmacenError("No se puede eliminar la versión ACTIVA. Activa otra primero.")
    if not any(v["id"] == id_version for v in data["versiones"]):
        raise AlmacenError(f"No existe la versión {id_version}")
    data["versiones"] = [v for v in data["versiones"] if v["id"] != id_version]
    _escribir_historial(data)
    shutil.rmtree(DIR_VERSIONES / id_version, ignore_errors=True)


def actualizar_nota(id_version: str, nota: str) -> None:
    data = _leer_historial()
    for v in data["versiones"]:
        if v["id"] == id_version:
            v["nota"] = nota.strip()
            break
    else:
        raise AlmacenError(f"No existe la versión {id_version}")
    _escribir_historial(data)


def originales_de(id_version: str) -> list[Path]:
    carpeta = DIR_VERSIONES / id_version / "originales"
    return sorted(carpeta.glob("*.xlsx")) if carpeta.exists() else []


def tamaño_en_disco(id_version: str) -> int:
    carpeta = DIR_VERSIONES / id_version
    return sum(p.stat().st_size for p in carpeta.rglob("*") if p.is_file()) if carpeta.exists() else 0
