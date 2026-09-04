"""
Búsqueda de personas y ficha individual (solo para usuarios con sesión: la
información es personal). Sin Streamlit: todo son funciones sobre DataFrames.

Identidad de una persona = (NOMBRES, APELLIDOS, FECHA DE NACIMIENTO), la
misma llave con la que el Power BI cuenta TOTAL DE PERSONAS.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

import pandas as pd

from core.derivados import COL_AÑO, COL_MES, orden_mes, resolver_columna
from observatorio.medidas import COL_APELLIDOS, COL_FECHA_NAC, COL_NOMBRES, MedidaError

SIN_VALOR = {"", "NO APLICA", "NAN", "NONE", "S/N", "SIN NUMERACIÓN", "SIN NUMERACION"}

# ── Campos de la ficha (etiqueta que se muestra -> columna del consolidado) ──
CAMPOS_FICHA = [
    ("Nombres", "NOMBRES"), ("Apellidos", "APELLIDOS"), ("Fecha de nacimiento", "FECHA DE NACIMIENTO"),
    ("Edad (años)", "EDAD - AÑOS"), ("Rango de edad", "RANGO DE EDAD"), ("Sexo", "SEXO"), ("Género", "GÉNERO"),
    ("Nacionalidad", "NACIONALIDAD"), ("Etnia", "ETNIA"), ("Zona", "ZONA"), ("Provincia", "PROVINCIA"),
    ("Ciudad", "CIUDAD"), ("Dirección", "DIRECCIÓN DOMICILIAR"),
    ("Documento de viaje", "DOCUMENTOS DE VIAJE"), ("Número del documento", "NÚMERO DEL DOCUMENTO DE VIAJE"),
    ("Situación de movilidad", "SITUACIÓN DE MOVILIDAD"), ("Situación migratoria", "SITUACIÓN MIGRATORIA"),
    ("Forma de ingreso al Ecuador", "FORMA DE INGRESO AL ECUADOR"),
    ("Motivo de salida del país", "Motivo de salida del país de origen"),
    ("Nivel de escolaridad", "NIVEL DE ESCOLARIDAD / INSTRUCCIÓN"), ("Está estudiando", "ACTUALMENTE ESTÁ ESTUDIANDO"),
    ("Tiene discapacidad", "TIENE DISCAPACIDAD"), ("Tipo de discapacidad", "Tipo de discapacidad"),
    ("Enfermedad catastrófica", "TIENE ENFERMEDAD CATASTRÓFICA"), ("Embarazo", "EMBARAZO (Sólo para mujeres)"),
    ("Otro tipo de vulnerabilidad", "OTRO TIPO DE VULNERABILIDAD"),
    ("Condición (NNA)", "CONDICIÓN SOLO PARA NNA"), ("Con quién se encuentra el NNA", "CON QUIEN SE ENCUENTRA EL NNA"),
    ("Madre", "Nombre y Apellido de la MADRE"), ("Teléfono de la madre", "Teléfono de contacto de la MADRE"),
    ("Padre", "Nombre y Apellido del PADRE"), ("Teléfono del padre", "Teléfono de contacto del PADRE"),
    ("Tutor/a o persona a cargo", "Nombre del tutor/a legal, cuidador habitual o pariente mayor de edad a cargo de NNA separado"),
    ("Código único NNA", "CÓDIGO ÚNICO DE IDENTIFICACIÓN PARA NNA"),
]

# ── Grupos de columnas SI/NO para los gráficos de la persona ────────────────
GRUPOS_SI_NO = {
    "Atenciones e intervenciones": [
        "ATENCIÓN EMERGENTE", "ATENCIÓN DE TRABAJO SOCIAL", "ATENCIÓN PSICOLÓGICA", "ATENCIÓN LEGAL", "SALUD",
        "EDUCACIÓN", "JUNTA CANTONAL", "REUNIFICACIÓN FAMILIAR", "ETI", "ACOGIMIENTO INSTITUCIONAL",
        "APOYO Y CUSTODIA FAMILIAR", "DISCAPACIDADES", "ADULTO MAYOR", "CDI", "CNH",
    ],
    "Kits humanitarios": ["KIT DE ASEO", "KIT DE SALUD", "KIT DE ALIMENTOS", "KIT ESCOLAR"],
    "Integración comunitaria": [
        "PARTICIPACIÓN A TALLERES DE CAPACITACIÓN", "PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN",
        "PARTICIPACIÓN EN ENCUENTROS COMUNITARIOS",
        "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICOS DE RECREACIÓN DE NNA", "INSERCIÓN A REDES COMUNITARIAS",
    ],
    "Regularización migratoria": [
        "REGISTRO MIGRATORIO -MDI-", "VISA VIRTE -MREMH-", "OBTENCIÓN DE LA CÉDULA ECUATORIANA -REGISTRO CIVIL-",
    ],
}


def _norm(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto if texto is not None else ""))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t).strip().upper()


def _vacio(x) -> bool:
    if x is None:
        return True
    try:
        if pd.isna(x):
            return True
    except (TypeError, ValueError):
        pass
    return _norm(x) in SIN_VALOR


def _cols_identidad(df: pd.DataFrame) -> tuple[str, str, str]:
    cols = [resolver_columna(df, c) for c in (COL_NOMBRES, COL_APELLIDOS, COL_FECHA_NAC)]
    if any(c is None for c in cols):
        raise MedidaError("El consolidado no tiene NOMBRES, APELLIDOS o FECHA DE NACIMIENTO.")
    return cols[0], cols[1], cols[2]  # type: ignore[return-value]


def _texto_fecha(x) -> str:
    if _vacio(x):
        return ""
    if isinstance(x, (pd.Timestamp, date)):
        return pd.Timestamp(x).strftime("%Y-%m-%d")
    return str(x)[:10]


# ── Índice y búsqueda ────────────────────────────────────────────────────────
def indice_personas(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por persona: clave, nombres, apellidos, fecha, nº de registros,
    primer y último año, y un texto normalizado para buscar."""
    cn, ca, cf = _cols_identidad(df)
    cy = resolver_columna(df, COL_AÑO)
    d = pd.DataFrame({
        "nombres": df[cn].map(lambda x: "" if _vacio(x) else str(x).strip()),
        "apellidos": df[ca].map(lambda x: "" if _vacio(x) else str(x).strip()),
        "fecha": df[cf].map(_texto_fecha),
        "año": df[cy].astype(str).str.strip() if cy else "",
    })
    d["clave"] = d["nombres"] + "|" + d["apellidos"] + "|" + d["fecha"]
    g = d.groupby("clave", sort=False)
    idx = g.agg(nombres=("nombres", "first"), apellidos=("apellidos", "first"), fecha=("fecha", "first"),
                registros=("clave", "size"), desde=("año", "min"), hasta=("año", "max")).reset_index()
    idx["busqueda"] = (idx["apellidos"] + " " + idx["nombres"]).map(_norm)
    return idx


def buscar(indice: pd.DataFrame, texto: str, limite: int = 40) -> pd.DataFrame:
    """Coincidencias cuyo nombre+apellido contiene TODAS las palabras escritas
    (sin importar tildes, mayúsculas ni el orden)."""
    palabras = [p for p in _norm(texto).split(" ") if p]
    if not palabras:
        return indice.iloc[0:0]
    mascara = pd.Series(True, index=indice.index)
    for p in palabras:
        mascara &= indice["busqueda"].str.contains(re.escape(p), regex=True)
    res = indice[mascara].sort_values(["apellidos", "nombres", "fecha"])
    return res.head(limite)


def etiqueta(fila) -> str:
    nac = f" · nac. {fila['fecha']}" if fila["fecha"] else " · sin fecha de nacimiento"
    años = fila["desde"] if fila["desde"] == fila["hasta"] else f"{fila['desde']}–{fila['hasta']}"
    return f"{fila['apellidos']} {fila['nombres']}{nac} · {fila['registros']} registro(s) · {años}"


def filas_de(df: pd.DataFrame, clave: str) -> pd.DataFrame:
    """Todas las filas del consolidado de esa persona, ordenadas por año y mes."""
    cn, ca, cf = _cols_identidad(df)
    n, a, f = clave.split("|", 2)
    m = (df[cn].map(lambda x: "" if _vacio(x) else str(x).strip()) == n) & \
        (df[ca].map(lambda x: "" if _vacio(x) else str(x).strip()) == a) & \
        (df[cf].map(_texto_fecha) == f)
    d = df[m].copy()
    return ordenar_por_periodo(d)


def ordenar_por_periodo(d: pd.DataFrame) -> pd.DataFrame:
    cy, cm = resolver_columna(d, COL_AÑO), resolver_columna(d, COL_MES)
    if cy is None or cm is None or d.empty:
        return d
    orden = d[cy].astype(str).str.strip() + d[cm].astype(str).map(lambda m: f"{orden_mes(m):02d}")
    return d.assign(_orden=orden).sort_values("_orden").drop(columns="_orden")


def años_de(d: pd.DataFrame) -> list[str]:
    cy = resolver_columna(d, COL_AÑO)
    if cy is None:
        return []
    return sorted({str(v).strip() for v in d[cy].dropna() if str(v).strip()})


def filtrar_año(d: pd.DataFrame, año: str | None) -> pd.DataFrame:
    cy = resolver_columna(d, COL_AÑO)
    if not año or cy is None:
        return d
    return d[d[cy].astype(str).str.strip() == str(año)]


# ── Ficha, línea de tiempo y servicios ──────────────────────────────────────
def ficha(d: pd.DataFrame) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) con el dato más reciente de cada campo (última
    fila con valor). Los campos sin dato no se muestran."""
    if d.empty:
        return []
    salida = []
    for etiq, nombre in CAMPOS_FICHA:
        col = resolver_columna(d, nombre)
        if col is None:
            continue
        valores = [v for v in d[col].tolist() if not _vacio(v)]
        if not valores:
            continue
        v = valores[-1]
        salida.append((etiq, _texto_fecha(v) if "FECHA" in nombre.upper() else str(v)))
    return salida


def periodos(d: pd.DataFrame) -> pd.DataFrame:
    """Atenciones por mes: columnas periodo ('2024 · ABRIL'), año, mes, registros."""
    cy, cm = resolver_columna(d, COL_AÑO), resolver_columna(d, COL_MES)
    if cy is None or cm is None or d.empty:
        return pd.DataFrame(columns=["periodo", "año", "mes", "registros"])
    t = pd.DataFrame({"año": d[cy].astype(str).str.strip(), "mes": d[cm].astype(str).str.strip().str.upper()})
    t["orden"] = t["año"] + t["mes"].map(lambda m: f"{orden_mes(m):02d}")
    g = t.groupby(["orden", "año", "mes"]).size().reset_index(name="registros").sort_values("orden")
    g["periodo"] = g["año"] + " · " + g["mes"].str.capitalize()
    return g[["periodo", "año", "mes", "registros"]]


def servicios(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Para cada grupo, cuántos meses la persona tuvo 'SI' en cada columna.
    Devuelve {grupo: DataFrame(servicio, veces)} solo con servicios > 0."""
    salida: dict[str, pd.DataFrame] = {}
    for grupo, columnas in GRUPOS_SI_NO.items():
        filas = []
        for nombre in columnas:
            col = resolver_columna(d, nombre)
            if col is None:
                continue
            veces = int(d[col].map(lambda x: _norm(x) == "SI").sum())
            if veces:
                filas.append((nombre.split(" -")[0].title(), veces))
        if filas:
            salida[grupo] = pd.DataFrame(filas, columns=["servicio", "veces"])
    return salida


def otros_kits(d: pd.DataFrame) -> list[str]:
    col = resolver_columna(d, "OTROS (Se debe especificar qué otro tipo de KIT humanitario fue entregado)")
    if col is None:
        return []
    return sorted({str(v).strip() for v in d[col] if not _vacio(v)})


def resumen(d: pd.DataFrame) -> dict[str, str]:
    p = periodos(d)
    return {
        "registros": str(len(d)),
        "meses": str(len(p)),
        "años": str(p["año"].nunique()) if not p.empty else "0",
        "primera": p["periodo"].iloc[0] if not p.empty else "—",
        "ultima": p["periodo"].iloc[-1] if not p.empty else "—",
    }
