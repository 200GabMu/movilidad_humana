"""
Plantilla de salida: el consolidado final debe tener EXACTAMENTE las mismas
columnas, en el mismo orden, que REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL.xlsx
(el archivo que alimenta al reporte). Si una columna no viene en los Excel
subidos se agrega vacía; si sobra alguna, va al final.

Los encabezados repetidos "SÓLO PARA CASO DE RESPUESTA OTRO" se distinguen
con sufijos .1 .2 .5 .3 .4 (así están en el archivo original).

CORRECCIONES_ENCABEZADO arregla la ortografía de los encabezados del propio
formulario. Es opcional: desactívala si otro sistema (p. ej. un Power BI)
sigue leyendo el archivo con los nombres antiguos.
"""

from __future__ import annotations

import re

import pandas as pd

from .consolidacion import COL_ARCHIVO, COL_HOJA
from .derivados import COL_AÑO, COL_MES, _clave

COLUMNAS_SALIDA = [
    "N°", "ZONA", "PROVINCIA", "DISTRITO", "CIUDAD", "NOMBRES", "APELLIDOS", "FECHA DE NACIMIENTO",
    "EDAD - AÑOS", "EDAD - MESES", "RANGO DE EDAD", "SEXO", "GÉNERO", "NACIONALIDAD", "ETNIA",
    "SÓLO PARA CASO DE RESPUESTA OTRO", "DIRECCIÓN DOMICILIAR", "DOCUMENTOS DE VIAJE",
    "SÓLO PARA CASO DE RESPUESTA OTRO.1", "NÚMERO DEL DOCUMENTO DE VIAJE", "SITUACIÓN DE MOVILIDAD",
    "FORMA DE INGRESO AL ECUADOR", "Motivo de salida del país de origen", "ATENCIÓN EMERGENTE",
    "INDICAR QUE TIPO DE ATENCIÓN EMERGENTE ACTUAL RECIBE", "SÓLO PARA CASO DE RESPUESTA OTRO.2",
    "KIT DE ASEO", "KIT DE SALUD", "KIT ESCOLAR",
    "OTROS (Se debe especificar que otro tipo de KIT humanitario fue entregado)",
    "CONDICIÓN SOLO PARA NNA", "Nombre y Apellido del MADRE", "Teléfono de contacto de la MADRE",
    "Correo electrónico de la MADRE", "Nombre y Apellido del PADRE", "Teléfono de contacto de la PADRE",
    "Correo electrónico del PADRE", "CON QUIEN SE ENCUENTRA EL NNA",
    "Nombre del tutor/a legal, cuidador habitual o pariente mayor de edad a cargo de NNA separado",
    "Parentesto del tutor/a legal, cuidador habitual o pariente mayor de edad",
    "Número telefónico de la persona a cargo del NNA separado",
    "Correo electrónico de la persona a cargo del NNA separado",
    "OTRO TIPO DE VULNERABILIDAD", "SÓLO PARA CASO DE RESPUESTA OTRO.5",
    "TIENE ENFERMEDAD CATASTRÓFICA", "TIENE DISCAPACIDAD", "Tipo de discapacidad",
    "EMBARAZO  (Sólo para mujeres)", "ACTUALMENTE ESTÁ ESTUDIANDO", "NIVEL DE ESCOLARIDAD / INSTRUCCIÓN",
    "ATENCIÓN DE TRABAJO SOCIAL", "ATENCIÓN PSICOLÓGICA", "ATENCIÓN LEGAL", "SALUD", "EDUCACIÓN",
    "JUNTA CANTONAL", "REUNIFICACIÓN FAMILIAR", "OTRO", "SÓLO PARA CASO DE RESPUESTA OTRO.3", "ETI",
    "ACOGIMINETO INSTITUCIONAL", "APOYO Y CUSTODIA FAMILIAR", "DISCAPACIDADES", "ADULTO MAYOR", "CDI",
    "CNH", "OTRO.1", "SÓLO PARA CASO DE RESPUESTA OTRO.4",
    "PARTICIPACIÓN A TALLERES DE CAPACITACIÓN", "PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN",
    "PARTICIPACIÓN EN ENCUENTROS COMUNITARIOS",
    "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICO DE RECREACIÓN DE NNA", "INSERCIÓN A REDES COMUNITARIAS",
    "SITUACIÓN  MIGRATORIA", "CÓDIGO ÚNICO DE IDENTIFICACIÓN PARA NNA", "REGISTRO MIGRATORIO  -MDI-",
    "VISA VIRTE -MREMH-", "OBTENCIÓN DE LA CÉDULA ECUATORIANA -REGISTRO CIVIL-",
    COL_HOJA, COL_ARCHIVO, COL_MES, COL_AÑO,
]

# Ortografía de los encabezados (nombre en la plantilla -> nombre corregido)
CORRECCIONES_ENCABEZADO = {
    "Nombre y Apellido del MADRE": "Nombre y Apellido de la MADRE",
    "Teléfono de contacto de la PADRE": "Teléfono de contacto del PADRE",
    "Parentesto del tutor/a legal, cuidador habitual o pariente mayor de edad":
        "Parentesco del tutor/a legal, cuidador habitual o pariente mayor de edad",
    "ACOGIMINETO INSTITUCIONAL": "ACOGIMIENTO INSTITUCIONAL",
    "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICO DE RECREACIÓN DE NNA":
        "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICOS DE RECREACIÓN DE NNA",
    "EMBARAZO  (Sólo para mujeres)": "EMBARAZO (Sólo para mujeres)",
    "SITUACIÓN  MIGRATORIA": "SITUACIÓN MIGRATORIA",
    "REGISTRO MIGRATORIO  -MDI-": "REGISTRO MIGRATORIO -MDI-",
    "OTROS (Se debe especificar que otro tipo de KIT humanitario fue entregado)":
        "OTROS (Se debe especificar qué otro tipo de KIT humanitario fue entregado)",
}
# Para que el panel encuentre la columna se llame como se llame
ALIAS_ENCABEZADO = {v: k for k, v in CORRECCIONES_ENCABEZADO.items()}

_RE_SUFIJO = re.compile(r"(__\d+|\.\d+)$")
# encabezado ya corregido (clave) -> encabezado de la plantilla (clave)
_ALIAS_CLAVE = {_clave(v): _clave(k) for k, v in CORRECCIONES_ENCABEZADO.items()}


def _base(nombre: str) -> str:
    """Nombre comparable: sin sufijos __n/.n, sin tildes/espacios/mayúsculas,
    y con la ortografía corregida llevada al nombre de la plantilla (así
    'Nombre y Apellido de la MADRE' y '… del MADRE' son la misma columna)."""
    clave = _clave(_RE_SUFIJO.sub("", str(nombre)))
    return _ALIAS_CLAVE.get(clave, clave)


def fusionar_columnas_duplicadas(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Si dos columnas quedaron con el mismo nombre (variantes del mismo
    encabezado en distintos archivos), se combinan en una: para cada fila se
    toma el primer valor no vacío. Devuelve (df, columnas fusionadas)."""
    if not df.columns.duplicated().any():
        return df, 0
    fusionadas = 0
    piezas: dict[str, pd.Series] = {}
    for nombre in dict.fromkeys(df.columns):           # orden de aparición, sin repetir
        bloque = df.loc[:, df.columns == nombre]
        if bloque.shape[1] == 1:
            piezas[nombre] = bloque.iloc[:, 0]
        else:
            piezas[nombre] = bloque.bfill(axis=1).iloc[:, 0]
            fusionadas += bloque.shape[1] - 1
    return pd.DataFrame(piezas, index=df.index), fusionadas


def ajustar_a_plantilla(df: pd.DataFrame, corregir_encabezados: bool = True) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Reordena/renombra las columnas del consolidado según la plantilla.

    Devuelve (df, columnas agregadas vacías, columnas extra conservadas al final).
    El emparejamiento ignora tildes/mayúsculas/espacios; los encabezados
    repetidos se emparejan por orden de aparición.
    """
    df, _ = fusionar_columnas_duplicadas(df.copy())
    # agrupar columnas reales por nombre base, en orden de aparición
    reales: dict[str, list[str]] = {}
    for c in df.columns:
        reales.setdefault(_base(c), []).append(c)

    renombres: dict[str, str] = {}
    usadas: set[str] = set()
    agregadas: list[str] = []
    for objetivo in COLUMNAS_SALIDA:
        candidatas = [c for c in reales.get(_base(objetivo), []) if c not in usadas]
        if candidatas:
            renombres[candidatas[0]] = objetivo
            usadas.add(candidatas[0])
        else:
            agregadas.append(objetivo)

    # Variantes sobrantes del mismo encabezado (p. ej. 'SITUACIÓN MIGRATORIA' con
    # uno y dos espacios) se llevan a la columna de la plantilla y se fusionan.
    objetivo_por_base: dict[str, str] = {}
    for objetivo in COLUMNAS_SALIDA:
        objetivo_por_base.setdefault(_base(objetivo), objetivo)
    for base, columnas in reales.items():
        for c in columnas:
            if c not in usadas and base in objetivo_por_base:
                renombres[c] = objetivo_por_base[base]

    df = df.rename(columns=renombres)
    df, _ = fusionar_columnas_duplicadas(df)
    for col in agregadas:
        df[col] = None
    extras = [c for c in df.columns if c not in COLUMNAS_SALIDA]
    df = df[COLUMNAS_SALIDA + extras]

    if corregir_encabezados:
        df = df.rename(columns=CORRECCIONES_ENCABEZADO)
        df, _ = fusionar_columnas_duplicadas(df)
    return df, agregadas, extras


# ── Relleno de celdas vacías, igual que en el archivo de referencia ──────────
# En REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL.xlsx ninguna celda queda en
# blanco: las casillas SI/NO vacías son "NO", los campos que no aplican son
# "No aplica", y dos columnas tienen su propio texto. Aquí se replica eso.
RELLENO_NO = {
    "ATENCIÓN EMERGENTE", "KIT DE ASEO", "KIT DE SALUD", "KIT ESCOLAR", "KIT DE ALIMENTOS",
    "TIENE ENFERMEDAD CATASTRÓFICA", "TIENE DISCAPACIDAD", "EMBARAZO  (Sólo para mujeres)",
    "ACTUALMENTE ESTÁ ESTUDIANDO", "ATENCIÓN DE TRABAJO SOCIAL", "ATENCIÓN PSICOLÓGICA", "ATENCIÓN LEGAL",
    "SALUD", "EDUCACIÓN", "JUNTA CANTONAL", "REUNIFICACIÓN FAMILIAR", "OTRO", "OTRO.1", "ETI",
    "ACOGIMINETO INSTITUCIONAL", "APOYO Y CUSTODIA FAMILIAR", "DISCAPACIDADES", "ADULTO MAYOR", "CDI", "CNH",
    "PARTICIPACIÓN A TALLERES DE CAPACITACIÓN", "PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN",
    "PARTICIPACIÓN EN ENCUENTROS COMUNITARIOS", "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICO DE RECREACIÓN DE NNA",
    "INSERCIÓN A REDES COMUNITARIAS", "REGISTRO MIGRATORIO  -MDI-", "VISA VIRTE -MREMH-",
    "OBTENCIÓN DE LA CÉDULA ECUATORIANA -REGISTRO CIVIL-",
}
RELLENO_ESPECIAL = {
    "SÓLO PARA CASO DE RESPUESTA OTRO": "S/N",          # solo la primera (etnia "otro")
    "NÚMERO DEL DOCUMENTO DE VIAJE": "SIN NUMERACIÓN",
}
# Columnas que se dejan en blanco si no hay dato (identidad, trazabilidad y
# NACIONALIDAD, donde un valor que no es nacionalidad se elimina a propósito)
SIN_RELLENO = {"N°", "NOMBRES", "APELLIDOS", "NACIONALIDAD", COL_HOJA, COL_ARCHIVO, COL_MES, COL_AÑO}
NO_APLICA = "No aplica"


def _es_vacio(x) -> bool:
    if x is None:
        return True
    if isinstance(x, str):
        return x.strip() == ""
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False


def rellenar_vacios(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Rellena las celdas vacías con el valor que corresponde a cada columna.
    Devuelve (df, número de celdas rellenadas)."""
    df, _ = fusionar_columnas_duplicadas(df.copy())   # df[col] debe ser una sola columna
    total = 0
    for col in df.columns:
        nombre = ALIAS_ENCABEZADO.get(str(col), str(col))   # nombre de la plantilla (sin corregir)
        if nombre in SIN_RELLENO:
            continue
        if nombre in RELLENO_ESPECIAL:
            valor = RELLENO_ESPECIAL[nombre]
        elif nombre in RELLENO_NO or _base(nombre) in {_base(c) for c in RELLENO_NO}:
            valor = "NO"
        else:
            valor = NO_APLICA
        vacios = df[col].map(_es_vacio)
        n = int(vacios.sum())
        if n:
            if df[col].dtype != object:                   # fechas/números + "No aplica" conviven (como en el archivo)
                df[col] = df[col].astype(object)
            df.loc[vacios, col] = valor
            total += n
    return df, total
