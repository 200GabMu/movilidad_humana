"""Prueba de extremo a extremo del núcleo (sin interfaz).  python tests/test_pipeline.py"""

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import almacen, pipeline  # noqa: E402
from core.derivados import agregar_columnas_derivadas, columnas_de_filtros  # noqa: E402
from tests.crear_excel_prueba import crear  # noqa: E402

# almacén temporal para no tocar data/ real
TMP = RAIZ / "tests" / "_data_tmp"
shutil.rmtree(TMP, ignore_errors=True)
almacen.RAIZ_DATA = TMP
almacen.DIR_VERSIONES = TMP / "versiones"
almacen.ARCHIVO_HISTORIAL = TMP / "historial.json"

a = crear("REPORTE MENSUAL 2025.xlsx", 2025, [("REPORTE MENSUAL OCTUBRE", 40), ("REPORTE MENSUAL NOVIEMBRE", 35)])
b = crear("REPORTE MENSUAL 2026.xlsx", 2026, [("REPORTE MENSUAL ENERO", 50), ("REPORTE MENSUAL FEBRERO", 45)])
c = crear("REPORTE MENSUAL 2026 marzo.xlsx", 2026, [("REPORTE MENSUAL MARZO", 30)])


def leer(p):
    return (p.name, p.read_bytes())


# 1) primera subida (reemplazar porque no hay nada)
r1 = pipeline.ejecutar([leer(a), leer(b)], modo=almacen.MODO_REEMPLAZAR, nota="carga inicial")
assert r1.ok, [m.texto for m in r1.mensajes]
assert r1.consolidacion.hojas_incluidas == 4
print("v1:", r1.version.id, len(r1.df_limpio), "filas", len(r1.df_limpio.columns), "cols")
print("columnas:", list(r1.df_limpio.columns))
assert "NOTAS INTERNAS (fuera de matriz)" not in r1.df_limpio.columns  # corte tras CÉDULA
assert "KIT DE ALIMENTOS" in r1.df_limpio.columns
assert "EDAD - AÑOS" in r1.df_limpio.columns and "KIT DE ASEO" in r1.df_limpio.columns
assert "AÑO" in r1.df_limpio.columns and "MES" in r1.df_limpio.columns
assert (r1.df_limpio["NACIONALIDAD"].dropna().isin(["VENEZOLANO/A", "COLOMBIANO/A", "ECUATORIANO/A", "PERUANO/A", "CUBANO/A"])).all()
assert not (r1.df_limpio.astype(str) == "Seleccione").any().any()

# 2) subida incremental de marzo + archivo repetido (2026) → solo entra marzo
r2 = pipeline.ejecutar([leer(c), leer(b)], modo=almacen.MODO_AGREGAR, nota="marzo")
assert r2.ok, [m.texto for m in r2.mensajes]
dup = [m for m in r2.mensajes if "duplicada" in m.texto]
assert len(dup) == 2, dup
assert r2.consolidacion.hojas_incluidas == 1
assert len(r2.df_crudo) == len(r1.df_crudo) + 30
print("v2:", r2.version.id, len(r2.df_limpio), "filas")

# 3) subir exactamente lo mismo otra vez → no hay hojas nuevas, no se crea versión
r3 = pipeline.ejecutar([leer(c)], modo=almacen.MODO_AGREGAR)
assert not r3.ok and len(almacen.listar_versiones()) == 2

# 4) historial: activar v1, eliminar v2, etc.
assert almacen.id_activa() == r2.version.id
almacen.activar_version(r1.version.id)
assert almacen.id_activa() == r1.version.id
try:
    almacen.eliminar_version(r1.version.id)
    raise AssertionError("no debía dejar eliminar la activa")
except almacen.AlmacenError:
    pass
assert len(almacen.originales_de(r2.version.id)) == 2
almacen.actualizar_nota(r2.version.id, "nota editada")
assert almacen.obtener_version(r2.version.id).nota == "nota editada"

# 5) derivados para el panel
df = agregar_columnas_derivadas(almacen.cargar(r2.version.id))
cols = columnas_de_filtros(df)
print("filtros:", cols)
assert all(v is not None for v in cols.values()), cols
assert cols["AÑO"] == "AÑO" and cols["MES"] == "MES" and cols["RANGO DE EDAD"] == "RANGO DE EDAD", cols
print(df["MES"].value_counts().to_dict())
print(df["RANGO DE EDAD"].value_counts().to_dict())
assert set(df["MES"].unique()) <= {"ENERO", "FEBRERO", "MARZO", "OCTUBRE", "NOVIEMBRE"}, df["MES"].unique()

# medidas del panel
from observatorio import medidas  # noqa: E402
ctx = medidas.Contexto(df, df)
tot = medidas.total_personas(df)
assert 0 < tot <= len(df)
assert abs(medidas.pct_hombres(ctx) + medidas.pct_mujeres(ctx) - 1) < 0.15  # hay 'Seleccione' -> vacío
print("TOTAL DE PERSONAS:", tot, "hombres:", medidas.formato_pct(medidas.pct_hombres(ctx)))
print(df["FECHA DE NACIMIENTO"].dtype)

almacen.eliminar_version(r2.version.id)
assert len(almacen.listar_versiones()) == 1
shutil.rmtree(TMP, ignore_errors=True)
print("✅ núcleo OK")

# ── plantilla de salida y ortografía ──
from core.plantilla import COLUMNAS_SALIDA, CORRECCIONES_ENCABEZADO  # noqa: E402
from core.ortografia import corregir_valor  # noqa: E402
esperadas = [CORRECCIONES_ENCABEZADO.get(c, c) for c in COLUMNAS_SALIDA]
assert list(r1.df_limpio.columns)[: len(esperadas)] == esperadas, list(r1.df_limpio.columns)[:10]
assert r1.stats["columnas_extra"] == ["KIT DE ALIMENTOS"], r1.stats["columnas_extra"]
assert corregir_valor("AMENAZAS CONTRA LA VIDA/SEGURIDAD/LIBERTAR E INTEGRIDAD") == "AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD"
assert corregir_valor("SITUACION ECONOMICA Y CONDICION MIGRATORIA") == "SITUACIÓN ECONÓMICA Y CONDICIÓN MIGRATORIA"
assert corregir_valor("NO APLICA") == "No aplica" and corregir_valor("TIA MATERNA") == "TÍA MATERNA"
assert corregir_valor("HACINAMIENTO,MENDICIDAD,") == "HACINAMIENTO, MENDICIDAD"
print("✅ plantilla + ortografía OK")
