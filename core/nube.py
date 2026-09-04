"""
Copia de seguridad automática de la carpeta `data/` en GitHub.

Streamlit Cloud borra el disco cada vez que la app se reinicia. Para que lo
unificado no se pierda, todo lo que hay en `data/` (versiones, historial,
usuarios, originales) se sube a una rama del repositorio llamada `datos`
—separada de `main` para que guardar datos NO redespliegue la app— y, al
arrancar con el disco vacío, se descarga de nuevo desde esa rama.

Solo se activa si existen los secretos GITHUB_TOKEN y GITHUB_REPO
(Streamlit Cloud → Settings → Secrets, o variables de entorno). En el
computador, sin esos secretos, no hace nada.

Solo usa la biblioteca estándar (urllib): ninguna dependencia nueva.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import almacen

API = "https://api.github.com"
RAMA_DEFECTO = "datos"
PREFIJO = "data"                     # carpeta dentro de la rama
MAX_BYTES = 95 * 1024 * 1024         # límite de la API de contenidos (100 MB)


class NubeError(Exception):
    pass


@dataclass
class Config:
    token: str
    repo: str            # "usuario/repositorio"
    rama: str = RAMA_DEFECTO


@dataclass
class ResultadoSync:
    subidos: list[str] = field(default_factory=list)
    borrados: list[str] = field(default_factory=list)
    sin_cambios: int = 0
    errores: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores

    def resumen(self) -> str:
        partes = []
        if self.subidos:
            partes.append(f"{len(self.subidos)} archivo(s) subido(s)")
        if self.borrados:
            partes.append(f"{len(self.borrados)} borrado(s)")
        if self.sin_cambios:
            partes.append(f"{self.sin_cambios} sin cambios")
        if self.errores:
            partes.append(f"{len(self.errores)} error(es)")
        return " · ".join(partes) or "nada que sincronizar"


# ── Configuración ────────────────────────────────────────────────────────────
def _secreto(nombre: str) -> str | None:
    valor = os.environ.get(nombre)
    if valor:
        return valor
    try:
        import streamlit as st
        v = st.secrets.get(nombre)
        return str(v) if v else None
    except Exception:  # sin secrets.toml / fuera de Streamlit
        return None


def config() -> Config | None:
    token, repo = _secreto("GITHUB_TOKEN"), _secreto("GITHUB_REPO")
    if not token or not repo:
        return None
    return Config(token=token.strip(), repo=repo.strip().strip("/"), rama=(_secreto("GITHUB_RAMA_DATOS") or RAMA_DEFECTO).strip())


def activa() -> bool:
    return config() is not None


# ── Llamadas a la API ────────────────────────────────────────────────────────
def _llamar(cfg: Config, metodo: str, ruta: str, cuerpo: dict | None = None, crudo: bool = False) -> bytes | dict | list | None:
    url = API + ruta
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo)
    req.add_header("Authorization", f"Bearer {cfg.token}")
    req.add_header("Accept", "application/vnd.github.raw" if crudo else "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "movilidad-humana-app")
    if datos is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            contenido = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        detalle = exc.read().decode("utf-8", "ignore")[:300]
        if exc.code == 401:
            raise NubeError("GitHub rechazó el token (401). Revisa GITHUB_TOKEN en los Secrets.") from exc
        if exc.code == 403:
            raise NubeError(f"GitHub no permite la operación (403): el token necesita permiso 'Contents: Read and write' "
                            f"sobre {cfg.repo}. Detalle: {detalle}") from exc
        raise NubeError(f"GitHub respondió {exc.code} en {metodo} {ruta}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise NubeError(f"No hay conexión con GitHub: {exc.reason}") from exc
    if crudo:
        return contenido
    return json.loads(contenido) if contenido else {}


def _ruta_api(cfg: Config, ruta_repo: str) -> str:
    return f"/repos/{cfg.repo}/contents/{urllib.parse.quote(ruta_repo)}"


def _asegurar_rama(cfg: Config) -> None:
    """Crea la rama de datos (a partir de la rama por defecto) si no existe."""
    if _llamar(cfg, "GET", f"/repos/{cfg.repo}/git/ref/heads/{cfg.rama}") is not None:
        return
    info = _llamar(cfg, "GET", f"/repos/{cfg.repo}")
    if not info:
        raise NubeError(f"No encuentro el repositorio {cfg.repo}. Revisa GITHUB_REPO (usuario/repositorio).")
    base = _llamar(cfg, "GET", f"/repos/{cfg.repo}/git/ref/heads/{info['default_branch']}")
    if not base:
        raise NubeError("El repositorio no tiene rama principal todavía.")
    _llamar(cfg, "POST", f"/repos/{cfg.repo}/git/refs", {"ref": f"refs/heads/{cfg.rama}", "sha": base["object"]["sha"]})


def _arbol_remoto(cfg: Config) -> dict[str, str]:
    """{ruta en el repo: sha del blob} de todo lo que hay bajo `data/` en la rama."""
    ref = _llamar(cfg, "GET", f"/repos/{cfg.repo}/git/ref/heads/{cfg.rama}")
    if ref is None:
        return {}
    arbol = _llamar(cfg, "GET", f"/repos/{cfg.repo}/git/trees/{ref['object']['sha']}?recursive=1")
    salida = {}
    for nodo in (arbol or {}).get("tree", []):
        if nodo.get("type") == "blob" and nodo["path"].startswith(PREFIJO + "/"):
            salida[nodo["path"]] = nodo["sha"]
    return salida


def _sha_git(datos: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(datos) + datos).hexdigest()


def _subir_archivo(cfg: Config, ruta_repo: str, datos: bytes, sha_actual: str | None, mensaje: str) -> None:
    cuerpo = {"message": mensaje, "content": base64.b64encode(datos).decode(), "branch": cfg.rama}
    if sha_actual:
        cuerpo["sha"] = sha_actual
    _llamar(cfg, "PUT", _ruta_api(cfg, ruta_repo), cuerpo)


def _borrar_archivo(cfg: Config, ruta_repo: str, sha_actual: str, mensaje: str) -> None:
    _llamar(cfg, "DELETE", _ruta_api(cfg, ruta_repo), {"message": mensaje, "sha": sha_actual, "branch": cfg.rama})


# ── Sincronizar (local -> GitHub) ────────────────────────────────────────────
def _archivos_locales() -> dict[str, Path]:
    raiz = almacen.RAIZ_DATA
    if not raiz.exists():
        return {}
    salida = {}
    for p in sorted(raiz.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and p.suffix != ".tmp":
            salida[f"{PREFIJO}/{p.relative_to(raiz).as_posix()}"] = p
    return salida


def sincronizar(mensaje: str = "Actualización de datos desde la app", progreso=None) -> ResultadoSync:
    """Sube a la rama de datos lo que cambió en `data/` y borra allí lo que ya
    no existe localmente (versiones eliminadas). Sin configuración: no hace nada."""
    cfg = config()
    res = ResultadoSync()
    if cfg is None:
        return res
    if not almacen.ARCHIVO_HISTORIAL.exists():
        return res          # disco vacío: nunca borrar lo remoto por eso
    try:
        _asegurar_rama(cfg)
        remoto = _arbol_remoto(cfg)
    except NubeError as exc:
        res.errores.append(str(exc))
        return res

    locales = _archivos_locales()
    total = len(locales)
    for i, (ruta_repo, ruta_local) in enumerate(locales.items(), 1):
        if progreso:
            progreso(i, total, ruta_repo)
        try:
            datos = ruta_local.read_bytes()
            if len(datos) > MAX_BYTES:
                res.errores.append(f"{ruta_repo}: supera el límite de GitHub (100 MB), no se subió.")
                continue
            sha_local = _sha_git(datos)
            if remoto.get(ruta_repo) == sha_local:
                res.sin_cambios += 1
                continue
            _subir_archivo(cfg, ruta_repo, datos, remoto.get(ruta_repo), mensaje)
            res.subidos.append(ruta_repo)
        except (NubeError, OSError) as exc:
            res.errores.append(f"{ruta_repo}: {exc}")

    for ruta_repo, sha in remoto.items():
        if ruta_repo not in locales:
            try:
                _borrar_archivo(cfg, ruta_repo, sha, mensaje)
                res.borrados.append(ruta_repo)
            except NubeError as exc:
                res.errores.append(f"{ruta_repo}: {exc}")
    return res


# ── Restaurar (GitHub -> local) ──────────────────────────────────────────────
def restaurar(progreso=None) -> ResultadoSync:
    """Descarga todo `data/` desde la rama de datos (se usa cuando el disco
    está vacío, p. ej. tras un reinicio de Streamlit Cloud)."""
    cfg = config()
    res = ResultadoSync()
    if cfg is None:
        return res
    try:
        remoto = _arbol_remoto(cfg)
    except NubeError as exc:
        res.errores.append(str(exc))
        return res
    total = len(remoto)
    for i, ruta_repo in enumerate(sorted(remoto), 1):
        if progreso:
            progreso(i, total, ruta_repo)
        destino = almacen.RAIZ_DATA / Path(ruta_repo).relative_to(PREFIJO)
        try:
            datos = _llamar(cfg, "GET", _ruta_api(cfg, ruta_repo) + f"?ref={urllib.parse.quote(cfg.rama)}", crudo=True)
            if datos is None:
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(datos)  # type: ignore[arg-type]
            res.subidos.append(ruta_repo)
        except (NubeError, OSError) as exc:
            res.errores.append(f"{ruta_repo}: {exc}")
    return res


def restaurar_si_vacio() -> ResultadoSync | None:
    """Al arrancar: si hay configuración y el disco no tiene historial, trae
    los datos desde GitHub. Devuelve None si no hizo falta."""
    if config() is None or almacen.ARCHIVO_HISTORIAL.exists():
        return None
    return restaurar()


def estado() -> dict:
    """Resumen para mostrar en el panel: configurado, repo, rama, versiones remotas."""
    cfg = config()
    if cfg is None:
        return {"activa": False}
    try:
        remoto = _arbol_remoto(cfg)
        versiones = {p.split("/")[2] for p in remoto if p.startswith(f"{PREFIJO}/versiones/")}
        return {"activa": True, "repo": cfg.repo, "rama": cfg.rama, "archivos": len(remoto),
                "versiones": len(versiones), "error": None}
    except NubeError as exc:
        return {"activa": True, "repo": cfg.repo, "rama": cfg.rama, "archivos": 0, "versiones": 0, "error": str(exc)}
