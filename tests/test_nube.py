"""Prueba de core/nube.py contra un GitHub simulado (servidor HTTP local que
imita los 6 endpoints usados). No necesita internet ni token real.

    python tests/test_nube.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
TMP = Path(tempfile.mkdtemp(prefix="mh_nube_"))
os.environ["MH_DATA_DIR"] = str(TMP / "data")
os.environ["GITHUB_TOKEN"] = "token-de-prueba"
os.environ["GITHUB_REPO"] = "alguien/repo"

from core import almacen, nube  # noqa: E402

REPO = {"ramas": {"main": {}}, "default": "main"}   # rama -> {ruta: bytes}


def _sha(datos: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(datos) + datos).hexdigest()


class GitHubFalso(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencio
        pass

    def _json(self, code, obj):
        cuerpo = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)

    def _cuerpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n)) if n else {}

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer token-de-prueba":
            return self._json(401, {"message": "Bad credentials"})
        u = urlparse(self.path); ruta = unquote(u.path); q = dict(p.split("=") for p in u.query.split("&") if p)
        if ruta == "/repos/alguien/repo":
            return self._json(200, {"default_branch": REPO["default"]})
        if ruta.startswith("/repos/alguien/repo/git/ref/heads/"):
            rama = ruta.rsplit("/", 1)[1]
            if rama not in REPO["ramas"]:
                return self._json(404, {"message": "Not Found"})
            return self._json(200, {"object": {"sha": "sha-" + rama}})
        if ruta.startswith("/repos/alguien/repo/git/trees/"):
            rama = ruta.rsplit("/", 1)[1].replace("sha-", "")
            arbol = [{"path": p, "type": "blob", "sha": _sha(d)} for p, d in REPO["ramas"][rama].items()]
            return self._json(200, {"tree": arbol})
        if ruta.startswith("/repos/alguien/repo/contents/"):
            archivo = ruta[len("/repos/alguien/repo/contents/"):]
            datos = REPO["ramas"].get(q.get("ref", "main"), {}).get(archivo)
            if datos is None:
                return self._json(404, {"message": "Not Found"})
            self.send_response(200); self.send_header("Content-Length", str(len(datos))); self.end_headers()
            self.wfile.write(datos); return
        self._json(404, {"message": "ruta desconocida " + ruta})

    def do_POST(self):
        b = self._cuerpo()
        if self.path == "/repos/alguien/repo/git/refs":
            REPO["ramas"][b["ref"].split("/")[-1]] = {}
            return self._json(201, {})
        self._json(404, {})

    def do_PUT(self):
        b = self._cuerpo(); archivo = unquote(self.path)[len("/repos/alguien/repo/contents/"):]
        rama = REPO["ramas"][b["branch"]]
        if archivo in rama and b.get("sha") != _sha(rama[archivo]):
            return self._json(409, {"message": "sha mismatch"})
        rama[archivo] = base64.b64decode(b["content"])
        self._json(200, {"content": {"sha": _sha(rama[archivo])}})

    def do_DELETE(self):
        b = self._cuerpo(); archivo = unquote(self.path)[len("/repos/alguien/repo/contents/"):]
        REPO["ramas"][b["branch"]].pop(archivo, None)
        self._json(200, {})


servidor = HTTPServer(("127.0.0.1", 0), GitHubFalso)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
nube.API = f"http://127.0.0.1:{servidor.server_port}"

# ── 1) sin datos locales no se sube nada (ni se borra lo remoto) ─────────────
assert nube.activa()
r = nube.sincronizar("nada")
assert r.ok and not r.subidos and "datos" not in REPO["ramas"], r
print("sin historial local: no toca GitHub OK")

# ── 2) crear una versión local y sincronizar ─────────────────────────────────
import pandas as pd  # noqa: E402
df = pd.DataFrame({"NOMBRES": ["ANA"], "APELLIDOS": ["P"], "FECHA DE NACIMIENTO": ["2000-01-01"], "AÑO": ["2024"], "MES": ["ENERO"]})
v1 = almacen.guardar_version(df_crudo=df, df_limpio=df, modo=almacen.MODO_REEMPLAZAR,
                             archivos=[("enero.xlsx", b"excel-falso")], hojas=1, nota="v1", stats={}, usuario="t")
r = nube.sincronizar("v1")
assert r.ok, r.errores
remoto = REPO["ramas"]["datos"]
assert f"data/versiones/{v1.id}/limpio.parquet" in remoto and "data/historial.json" in remoto
assert f"data/versiones/{v1.id}/originales/enero.xlsx" in remoto
print(f"subida inicial: {len(r.subidos)} archivos OK")

# ── 3) segunda sincronización sin cambios: nada que subir ────────────────────
r = nube.sincronizar("otra vez")
assert r.ok and not r.subidos and r.sin_cambios >= 4, r.resumen()
print("sin cambios: no vuelve a subir OK")

# ── 4) eliminar versión local -> se borra en GitHub ──────────────────────────
v2 = almacen.guardar_version(df_crudo=df, df_limpio=df, modo=almacen.MODO_REEMPLAZAR, archivos=[], hojas=1, nota="v2", stats={}, usuario="t")
nube.sincronizar("v2")
almacen.eliminar_version(v1.id)
r = nube.sincronizar("borrar v1")
assert r.ok, r.errores
assert any(v1.id in b for b in r.borrados), (v1.id, v2.id, r.borrados)
assert not any(p.startswith(f"data/versiones/{v1.id}/") for p in remoto), sorted(remoto)
print("versión eliminada también en GitHub OK")

# ── 5) disco vacío (reinicio en la nube) -> restaurar ────────────────────────
shutil.rmtree(TMP / "data")
assert not almacen.ARCHIVO_HISTORIAL.exists()
r = nube.restaurar_si_vacio()
assert r is not None and r.ok, r
assert almacen.id_activa() == v2.id and almacen.cargar(v2.id).shape == (1, 5)
print("restauración tras reinicio OK")

# ── 6) token inválido -> error claro, sin excepción ──────────────────────────
os.environ["GITHUB_TOKEN"] = "malo"
r = nube.sincronizar("x")
assert not r.ok and "401" in r.errores[0] or "rechaz" in r.errores[0], r.errores
print("token inválido: aviso claro OK")

servidor.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
print("✅ nube OK")
