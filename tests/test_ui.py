"""Ejecuta cada página con streamlit.testing (sin navegador) y revisa que no
haya excepciones.   python tests/test_ui.py"""

import os
import shutil
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import almacen, pipeline  # noqa: E402
from tests.crear_excel_prueba import crear  # noqa: E402

TMP = RAIZ / "tests" / "_data_ui"
shutil.rmtree(TMP, ignore_errors=True)
almacen.RAIZ_DATA = TMP
almacen.DIR_VERSIONES = TMP / "versiones"
almacen.ARCHIVO_HISTORIAL = TMP / "historial.json"


from core import usuarios as us  # noqa: E402
os.environ.pop("ADMIN_PASSWORD", None)


def correr(pagina: str, admin: bool = True) -> AppTest:
    at = AppTest.from_file(str(RAIZ / "vistas" / pagina), default_timeout=60)
    if admin:
        if not us.obtener("admin"):
            us.crear("admin", "clave-prueba", "administrador")
        at.session_state["mh_usuario"] = {"nombre": "admin", "rol": "administrador"}
    at.run()
    errores = [e.value for e in at.exception]
    assert not errores, f"{pagina}: {errores}"
    return at


# Roles: sin sesión, Unificar/Historial/Usuarios bloquean y no muestran nada
for p in ("unificar.py", "historial.py", "usuarios.py"):
    at = correr(p, admin=False)
    assert len(at.error) == 1 and "iniciar sesión" in at.error[0].value, p
    assert not at.button and not at.selectbox, p
print("roles: páginas de administración bloqueadas sin sesión OK")

# Login: sin secrets.toml, el primer arranque muestra el formulario "crear administrador"
import tomllib  # noqa: E402
secretos = RAIZ / ".streamlit" / "secrets.toml"
if secretos.exists():
    clave_admin = tomllib.loads(secretos.read_text(encoding="utf-8"))["ADMIN_PASSWORD"]
else:
    clave_admin = "clave-prueba"
    at = correr("acceso.py", admin=False)
    assert at.info and "Primer arranque" in at.info[0].value and not us.hay_usuarios()
    at.text_input[0].input("admin"); at.text_input[1].input(clave_admin); at.text_input[2].input("otra")
    at.button[0].click().run()
    assert at.error and "no coinciden" in at.error[0].value and not us.hay_usuarios()
    at.text_input[0].input("admin"); at.text_input[1].input(clave_admin); at.text_input[2].input(clave_admin)
    at.button[0].click().run()
    assert us.obtener("admin") is not None and at.session_state["mh_usuario"]["rol"] == "administrador"
    print("primer arranque: cuenta admin creada desde la app OK")
    at.session_state["mh_usuario"] = None
at = correr("acceso.py", admin=False)
assert us.obtener("admin") is not None and not at.error, [e.value for e in at.error]
at.text_input[0].input("admin"); at.text_input[1].input("mala"); at.button[0].click().run()
assert at.error and "incorrectos" in at.error[0].value
at.text_input[0].input("admin"); at.text_input[1].input(clave_admin); at.button[0].click().run()
assert at.session_state["mh_usuario"]["rol"] == "administrador"
os.environ.pop("ADMIN_PASSWORD", None)
print("login: usuario+clave incorrectos rechazados, correctos aceptados OK")

# Usuarios: crear operador, permisos limitados
op = us.crear("maria", "clave-maria", "operador", creado_por="admin")
assert op.puede("subir") and op.puede("historial") and not op.puede("reemplazar") and not op.puede("eliminar")
assert us.verificar("maria", "clave-maria") is not None and us.verificar("maria", "otra") is None
try:
    us.eliminar("admin"); raise AssertionError("no debía dejar borrar al único admin")
except us.UsuariosError:
    pass
at = AppTest.from_file(str(RAIZ / "vistas" / "usuarios.py"), default_timeout=60)
at.session_state["mh_usuario"] = {"nombre": "admin", "rol": "administrador"}; at.run()
assert not at.exception and len(at.dataframe) == 1
at = AppTest.from_file(str(RAIZ / "vistas" / "historial.py"), default_timeout=60)
at.session_state["mh_usuario"] = {"nombre": "maria", "rol": "operador"}; at.run()
assert not at.exception
print("usuarios: operador con permisos limitados OK")

# Sin datos: cada página debe avisar, no romperse
for p in ("unificar.py", "historial.py", "panel.py"):
    at = correr(p)
    print(f"{p:14s} sin datos → info={len(at.info)} warn={len(at.warning)} err={len(at.error)}")

# Con datos
a = crear("REPORTE MENSUAL 2025.xlsx", 2025, [("REPORTE MENSUAL OCTUBRE", 40), ("REPORTE MENSUAL NOVIEMBRE", 35)])
b = crear("REPORTE MENSUAL 2026.xlsx", 2026, [("REPORTE MENSUAL ENERO", 50), ("REPORTE MENSUAL FEBRERO", 45)])
r = pipeline.ejecutar([(a.name, a.read_bytes()), (b.name, b.read_bytes())], modo=almacen.MODO_REEMPLAZAR)
assert r.ok
# el almacén se parchea de nuevo porque AppTest reimporta módulos en cada run
for p in ("historial.py", "panel.py"):
    at = correr(p)
    print(f"{p:14s} con datos → metric={len(at.metric)} selectbox={len(at.selectbox)} err={len(at.error)}")

# Panel: INICIO muestra las 6 secciones; cada página del reporte corre sin errores
from observatorio.spec import PAGINAS, SECCIONES  # noqa: E402
at = AppTest.from_file(str(RAIZ / "vistas" / "panel.py"), default_timeout=120); at.run()
assert not at.exception, [e.value for e in at.exception]
assert {b.label for b in at.button} >= {s[0] for s in SECCIONES}
for nombre in PAGINAS:
    at = AppTest.from_file(str(RAIZ / "vistas" / "panel.py"), default_timeout=120)
    at.session_state["pbi_pagina"] = nombre
    at.run()
    assert not at.exception, (nombre, [e.value for e in at.exception])
    assert not at.warning, (nombre, [w.value for w in at.warning])
print(f"panel: {len(PAGINAS)} páginas del reporte OK")

# Panel: el filtro SEXO cambia el total de personas
at = AppTest.from_file(str(RAIZ / "vistas" / "panel.py"), default_timeout=120)
at.session_state["pbi_pagina"] = "Perfil de la Población"
at.run()
def tarjeta_total(at):
    return next(m.value for m in at.markdown if "TOTAL DE PERSONAS" in m.value and "pbi-card" in m.value)
total = tarjeta_total(at)
sb = {s.label: s for s in at.selectbox}
assert "SEXO" in sb and "MES" in sb, list(sb)
sb["SEXO"].select("MUJER").run()
assert not at.exception, [e.value for e in at.exception]
assert tarjeta_total(at) != total
print("panel: filtro SEXO aplicado OK")

# Historial: activar otra versión
r2 = pipeline.ejecutar([(a.name, a.read_bytes())], modo=almacen.MODO_REEMPLAZAR, nota="solo 2025")
at = AppTest.from_file(str(RAIZ / "vistas" / "historial.py"), default_timeout=60)
at.session_state["mh_usuario"] = {"nombre": "admin", "rol": "administrador"}
at.run()
assert not at.exception
at.selectbox[0].select(r.version.id).run()
boton = next(b for b in at.button if "Activar" in b.label)
boton.click().run()
assert almacen.id_activa() == r.version.id, almacen.id_activa()
print("historial: activar versión anterior OK")

shutil.rmtree(TMP, ignore_errors=True)
print("✅ UI OK")
