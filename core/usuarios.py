"""
Usuarios y roles de la administración.

Se guardan en  data/usuarios.json  con la clave cifrada (PBKDF2-SHA256 con
sal por usuario): en el archivo NO aparece ninguna contraseña en claro.

Roles (qué puede hacer cada uno):
  administrador  -> todo: subir, reemplazar, historial (activar/eliminar),
                    gestionar usuarios.
  operador       -> subir reportes (solo modo AGREGAR) y ver/descargar el
                    historial. No puede reemplazar, activar, eliminar ni
                    crear usuarios.
  (público)      -> el Panel, sin cuenta.

Primer arranque: si no existe usuarios.json se crea el usuario "admin" con la
clave ADMIN_PASSWORD de .streamlit/secrets.toml. Después todo se maneja desde
la página "Usuarios".
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime

from . import almacen

ROLES: dict[str, set[str]] = {
    "administrador": {"subir", "reemplazar", "historial", "activar", "eliminar", "usuarios", "buscar"},
    "operador": {"subir", "historial", "buscar"},
}
DESCRIPCION_ROL = {
    "administrador": "Sube, reemplaza, restaura y elimina versiones; administra usuarios.",
    "operador": "Solo sube reportes (agregar) y consulta/descarga el historial.",
}
_ITERACIONES = 200_000
_RE_NOMBRE = re.compile(r"^[a-z0-9._-]{3,30}$")
MIN_CLAVE = 8


class UsuariosError(Exception):
    pass


@dataclass
class Usuario:
    nombre: str
    rol: str
    hash: str
    sal: str
    activo: bool = True
    creado: str = ""
    creado_por: str = ""
    ultimo_acceso: str = ""
    extra: dict = field(default_factory=dict)

    def puede(self, permiso: str) -> bool:
        return self.activo and permiso in ROLES.get(self.rol, set())

    def publico(self) -> dict:
        """Datos sin hash/sal para mostrar en pantalla."""
        return {"nombre": self.nombre, "rol": self.rol, "activo": self.activo,
                "creado": self.creado, "creado_por": self.creado_por, "ultimo_acceso": self.ultimo_acceso}


# ── Cifrado ─────────────────────────────────────────────────────────────────

def _hash(clave: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), _ITERACIONES).hex()


def _nueva_sal() -> str:
    return secrets.token_hex(16)


# ── Archivo ─────────────────────────────────────────────────────────────────

def _ruta():
    # se recalcula por si RAIZ_DATA cambió (pruebas / MH_DATA_DIR)
    return almacen.RAIZ_DATA / "usuarios.json"


def _leer() -> dict[str, Usuario]:
    ruta = _ruta()
    if not ruta.exists():
        return {}
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UsuariosError(f"usuarios.json está dañado: {exc}") from exc
    return {u["nombre"]: Usuario(**u) for u in data.get("usuarios", [])}


def _escribir(usuarios: dict[str, Usuario]) -> None:
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps({"usuarios": [asdict(u) for u in usuarios.values()]}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(ruta)
    try:
        os.chmod(ruta, 0o600)  # solo el dueño del archivo puede leerlo (Linux/Mac)
    except OSError:
        pass


def hay_usuarios() -> bool:
    return bool(_leer())


def listar() -> list[Usuario]:
    return sorted(_leer().values(), key=lambda u: (u.rol != "administrador", u.nombre))


def obtener(nombre: str) -> Usuario | None:
    return _leer().get(nombre.strip().lower())


# ── Operaciones ─────────────────────────────────────────────────────────────

def validar_nombre(nombre: str) -> str:
    n = nombre.strip().lower()
    if not _RE_NOMBRE.match(n):
        raise UsuariosError("El usuario debe tener 3-30 caracteres: letras minúsculas, números, punto, guion o guion bajo.")
    return n


def validar_clave(clave: str) -> None:
    if len(clave) < MIN_CLAVE:
        raise UsuariosError(f"La contraseña debe tener al menos {MIN_CLAVE} caracteres.")


def crear(nombre: str, clave: str, rol: str, creado_por: str = "") -> Usuario:
    nombre = validar_nombre(nombre)
    validar_clave(clave)
    if rol not in ROLES:
        raise UsuariosError(f"Rol inválido: {rol}")
    usuarios = _leer()
    if nombre in usuarios:
        raise UsuariosError(f"Ya existe el usuario '{nombre}'.")
    sal = _nueva_sal()
    u = Usuario(nombre=nombre, rol=rol, hash=_hash(clave, sal), sal=sal,
                creado=datetime.now().isoformat(timespec="seconds"), creado_por=creado_por)
    usuarios[nombre] = u
    _escribir(usuarios)
    return u


def verificar(nombre: str, clave: str) -> Usuario | None:
    """Devuelve el usuario si nombre+clave son correctos y está activo."""
    usuarios = _leer()
    u = usuarios.get(nombre.strip().lower())
    if u is None:
        _hash(clave, _nueva_sal())  # mismo tiempo de respuesta exista o no el usuario
        return None
    if not hmac.compare_digest(_hash(clave, u.sal), u.hash) or not u.activo:
        return None
    u.ultimo_acceso = datetime.now().isoformat(timespec="seconds")
    _escribir(usuarios)
    return u


def cambiar_clave(nombre: str, clave_nueva: str) -> None:
    validar_clave(clave_nueva)
    usuarios = _leer()
    u = usuarios.get(nombre)
    if u is None:
        raise UsuariosError(f"No existe el usuario '{nombre}'.")
    u.sal = _nueva_sal()
    u.hash = _hash(clave_nueva, u.sal)
    _escribir(usuarios)


def cambiar_rol(nombre: str, rol: str) -> None:
    if rol not in ROLES:
        raise UsuariosError(f"Rol inválido: {rol}")
    usuarios = _leer()
    u = usuarios.get(nombre)
    if u is None:
        raise UsuariosError(f"No existe el usuario '{nombre}'.")
    if u.rol == "administrador" and rol != "administrador":
        _exigir_otro_admin(usuarios, nombre)
    u.rol = rol
    _escribir(usuarios)


def activar(nombre: str, activo: bool) -> None:
    usuarios = _leer()
    u = usuarios.get(nombre)
    if u is None:
        raise UsuariosError(f"No existe el usuario '{nombre}'.")
    if not activo and u.rol == "administrador":
        _exigir_otro_admin(usuarios, nombre)
    u.activo = activo
    _escribir(usuarios)


def eliminar(nombre: str) -> None:
    usuarios = _leer()
    u = usuarios.get(nombre)
    if u is None:
        raise UsuariosError(f"No existe el usuario '{nombre}'.")
    if u.rol == "administrador":
        _exigir_otro_admin(usuarios, nombre)
    del usuarios[nombre]
    _escribir(usuarios)


def _exigir_otro_admin(usuarios: dict[str, Usuario], excepto: str) -> None:
    otros = [u for n, u in usuarios.items() if n != excepto and u.rol == "administrador" and u.activo]
    if not otros:
        raise UsuariosError("Debe quedar al menos un administrador activo.")


def inicializar_desde_clave(clave_inicial: str | None) -> Usuario | None:
    """Primer arranque: crea 'admin' con ADMIN_PASSWORD si aún no hay usuarios."""
    if hay_usuarios() or not clave_inicial:
        return None
    return crear("admin", clave_inicial, "administrador", creado_por="secrets.toml")
