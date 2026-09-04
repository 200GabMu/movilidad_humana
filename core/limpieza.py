"""
Paso 2: limpieza + relleno de datos faltantes (orden fijo e intencional).

  1) 'Seleccione' -> vacío        (si no, el relleno copiaría 'Seleccione' como dato real)
  2) Normalizar texto             (mayúsculas + espacios; no toca correos ni trazabilidad)
  3) Unificar género en Nacionalidad ('VENEZOLANA' -> 'VENEZOLANO/A')
  4) Rellenar por Nombre + Apellido
  5) Eliminar filas sin Nombre ni Apellido
  6) Fecha de nacimiento como fecha real de Excel
  7) Columnas y orden de la plantilla de salida; celdas vacías rellenadas
     ("NO" en casillas, "No aplica" en el resto) como en el archivo de referencia
"""

from __future__ import annotations

import re

import pandas as pd

from .consolidacion import COLS_TRAZABILIDAD

KEYWORD_NOMBRES = "NOMBRE"
KEYWORD_APELLIDOS = "APELLIDO"
FECHA_NACIMIENTO_COL = "FECHA DE NACIMIENTO"

COLUMNAS_SIN_MAYUSCULAS = set(COLS_TRAZABILIDAD)

# Gentilicios con forma masculina/femenina -> forma unificada "…O/A"
_GENTILICIOS_OA = [
    "ARGENTINO", "BOLIVIANO", "BRASILEÑO", "CHILENO", "COLOMBIANO", "CUBANO", "DOMINICANO",
    "ECUATORIANO", "GUATEMALTECO", "HAITIANO", "HONDUREÑO", "MEXICANO", "PANAMEÑO", "PARAGUAYO",
    "PERUANO", "SALVADOREÑO", "URUGUAYO", "VENEZOLANO", "SIRIO", "RUSO", "UCRANIANO", "CHINO",
    "ITALIANO", "INDIO", "NIGERIANO", "AFGANO", "PALESTINO", "TURCO", "FILIPINO", "COREANO",
    "JAPONÉS", "LIBANÉS", "PORTUGUÉS", "IRLANDÉS", "ESPAÑOL", "ALEMÁN", "FRANCÉS", "INGLÉS",
    "CAMERUNÉS", "GHANÉS", "SENEGALÉS", "CONGOLEÑO", "ANGOLEÑO", "MARROQUÍ",
]
MAPA_NACIONALIDADES = {}
for _g in _GENTILICIOS_OA:
    _f = _g[:-1] + "A" if _g.endswith("O") else _g + "A"          # PERUANO->PERUANA, ESPAÑOL->ESPAÑOLA
    _f = _f.replace("ÉSA", "ESA").replace("ÁNA", "ANA")               # JAPONÉS->JAPONESA, ALEMÁN->ALEMANA
    _u = f"{_g}/A"
    MAPA_NACIONALIDADES[_g] = _u
    MAPA_NACIONALIDADES[_f] = _u
MAPA_NACIONALIDADES.update({
    "VENEZOLNA": "VENEZOLANO/A", "VENEZOLANOA": "VENEZOLANO/A", "VENEZOLANO/A.": "VENEZOLANO/A",
    "YEMENI": "YEMENÍ", "IRANI": "IRANÍ", "IRAQUI": "IRAQUÍ", "MARROQUI": "MARROQUÍ/A",
    "PAKISTANI": "PAKISTANÍ", "BANGLADESI": "BANGLADESÍ", "APATRIDA": "APÁTRIDA",
})

# Nacionalidades admitidas en la columna NACIONALIDAD. Cualquier otro valor
# ("MESTIZO", "SI", "S/N"…) NO es una nacionalidad: se saca de la columna y,
# si es una etnia, pasa a ETNIA (cuando ETNIA está vacía).
NACIONALIDADES_VALIDAS = set(MAPA_NACIONALIDADES.values()) | {
    "YEMENÍ", "IRANÍ", "IRAQUÍ", "PAKISTANÍ", "BANGLADESÍ", "MARROQUÍ/A", "APÁTRIDA",
    "COSTARRICENSE", "NICARAGÜENSE", "ESTADOUNIDENSE", "CANADIENSE", "BELICEÑO/A", "JAMAIQUINO/A",
    "GUYANÉS/A", "SURINAMÉS/A", "ESTADOUNIDENSE", "No aplica",
}
ETNIAS = {"MESTIZO", "MESTIZA", "AFRODESCENDIENTE", "AFROECUATORIANO", "AFROECUATORIANA", "BLANCO", "BLANCA",
          "INDÍGENA", "INDIGENA", "MONTUBIO", "MONTUBIA", "MULATO", "MULATA", "NEGRO", "NEGRA", "OTRO"}


def _como_texto_libre(df: pd.DataFrame) -> pd.DataFrame:
    """Deja todas las columnas (salvo fechas) con dtype object, para poder
    mezclar números, textos y 'No aplica' en la misma columna. pandas 3 ya no
    convierte solo una columna numérica cuando se le escribe un texto."""
    df = df.copy()
    for col in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df[col]) and df[col].dtype != object:
            df[col] = df[col].astype(object)
    return df


def encontrar_columna(df: pd.DataFrame, palabra_clave: str) -> str | None:
    """Columna cuyo nombre contenga la palabra clave, evitando falsos
    positivos como 'NOMBRE DE LA HOJA' / 'NOMBRE DEL ARCHIVO'."""
    for col in df.columns:
        c_up = str(col).upper()
        if palabra_clave in c_up and "HOJA" not in c_up and "ARCHIVO" not in c_up:
            return col
    return None


def limpiar_seleccione(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    es_seleccione = df.apply(lambda col: col.astype(str).str.strip().str.lower() == "seleccione")
    celdas = int(es_seleccione.values.sum())
    return df.mask(es_seleccione), celdas


def normalizar_espacios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].map(lambda x: re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else x)
    return df


def normalizar_texto(df: pd.DataFrame) -> pd.DataFrame:
    df = normalizar_espacios(df)
    for col in df.columns:
        if col in COLUMNAS_SIN_MAYUSCULAS or "CORREO" in str(col).upper():
            continue
        df[col] = df[col].map(lambda x: x.upper() if isinstance(x, str) else x)
    return df


def normalizar_nacionalidad(df: pd.DataFrame, col: str = "NACIONALIDAD") -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df[col] = df[col].map(lambda x: MAPA_NACIONALIDADES.get(x, x) if isinstance(x, str) else x)
    return df


def depurar_nacionalidad(df: pd.DataFrame, col: str = "NACIONALIDAD", col_etnia: str = "ETNIA") -> tuple[pd.DataFrame, int]:
    """Deja en NACIONALIDAD solo nacionalidades. Lo que no lo sea se vacía; si
    es una etnia y ETNIA está vacía, se mueve allí. Y al revés: una
    nacionalidad escrita en ETNIA pasa a NACIONALIDAD si esta está vacía.
    Devuelve (df, celdas corregidas)."""
    df = df.copy()
    if col not in df.columns:
        return df, 0
    cambios = 0
    tiene_etnia = col_etnia in df.columns
    for c in (col, col_etnia) if tiene_etnia else (col,):
        if df[c].dtype != object:
            df[c] = df[c].astype(object)
    validas_up = {v.upper() for v in NACIONALIDADES_VALIDAS}
    for i in df.index:
        nac = df.at[i, col]
        if isinstance(nac, str) and nac.strip() and nac.strip().upper() not in validas_up:
            if tiene_etnia and nac.strip().upper() in ETNIAS and not isinstance(df.at[i, col_etnia], str):
                df.at[i, col_etnia] = nac.strip()
            df.at[i, col] = None
            cambios += 1
        if tiene_etnia:
            etn = df.at[i, col_etnia]
            if isinstance(etn, str):
                etn_u = MAPA_NACIONALIDADES.get(etn.strip().upper(), etn.strip().upper())
                if etn_u in validas_up and etn_u != "NO APLICA":
                    if not isinstance(df.at[i, col], str):
                        df.at[i, col] = etn_u
                    df.at[i, col_etnia] = None
                    cambios += 1
    return df, cambios


def rellenar_datos_faltantes(df: pd.DataFrame, col_nombres: str, col_apellidos: str) -> pd.DataFrame:
    """
    Rellena huecos agrupando por (Nombres, Apellidos): asume que dos filas con
    el mismo Nombre + Apellido son la MISMA persona (ffill + bfill).

    Se usa fillna/combine_first con el original para que las filas con la
    llave nula (que pandas descarta al agrupar) conserven sus valores.
    """
    df = df.copy()
    df = df.replace(r"^\s*$", None, regex=True)

    apellidos_original = df[col_apellidos].copy()
    nombres_original = df[col_nombres].copy()

    apellidos_t = df.groupby(col_nombres)[col_apellidos].transform(lambda x: x.ffill().bfill())
    df[col_apellidos] = apellidos_t.fillna(apellidos_original)

    nombres_t = df.groupby(col_apellidos)[col_nombres].transform(lambda x: x.ffill().bfill())
    df[col_nombres] = nombres_t.fillna(nombres_original)

    restantes = [c for c in df.columns if c not in (col_nombres, col_apellidos)]
    if restantes:
        original = df[restantes].copy()
        transformado = (
            df.groupby([col_nombres, col_apellidos])[restantes]
            .transform(lambda x: x.ffill().bfill())
        )
        df[restantes] = transformado.combine_first(original)

    return df


def eliminar_filas_sin_identidad(df: pd.DataFrame, col_nombres: str, col_apellidos: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    sin_identidad = df[col_nombres].isna() & df[col_apellidos].isna()
    n = int(sin_identidad.sum())
    return df[~sin_identidad].reset_index(drop=True), n


def formatear_fecha_nacimiento(df: pd.DataFrame, col_fecha: str = FECHA_NACIMIENTO_COL) -> pd.DataFrame:
    df = df.copy()
    if col_fecha in df.columns:
        df[col_fecha] = pd.to_datetime(df[col_fecha], format="%Y/%m/%d", errors="coerce")
    return df


def procesar_limpieza_y_relleno(df: pd.DataFrame, corregir_encabezados: bool = True) -> tuple[pd.DataFrame, dict]:
    """Paso 2 completo. Lanza ValueError si no encuentra Nombres/Apellidos.

    Orden: Seleccione→vacío · texto · nacionalidad · ORTOGRAFÍA · relleno ·
    filas sin identidad · fecha · AÑO/MES · columnas según la PLANTILLA.
    """
    from .ortografia import corregir_ortografia          # imports tardíos: evitan ciclos
    from .plantilla import ajustar_a_plantilla, rellenar_vacios
    col_nombres = encontrar_columna(df, KEYWORD_NOMBRES)
    col_apellidos = encontrar_columna(df, KEYWORD_APELLIDOS)
    if not col_nombres or not col_apellidos:
        raise ValueError(
            "No encontré columnas de Nombres y/o Apellidos en el consolidado "
            "(busco encabezados que contengan 'NOMBRE' y 'APELLIDO')."
        )

    df = _como_texto_libre(df)
    df, n_seleccione = limpiar_seleccione(df)
    df = normalizar_texto(df)
    df = normalizar_nacionalidad(df)
    df, n_ortografia = corregir_ortografia(df)
    df, n_nacionalidad = depurar_nacionalidad(df)
    df = rellenar_datos_faltantes(df, col_nombres, col_apellidos)
    df, n_eliminadas = eliminar_filas_sin_identidad(df, col_nombres, col_apellidos)
    df = formatear_fecha_nacimiento(df)
    # AÑO y MES al final de la matriz, como en el archivo que alimenta al Power BI
    from .derivados import agregar_columnas_derivadas  # import tardío: evita ciclo
    df = agregar_columnas_derivadas(df)
    df, cols_agregadas, cols_extra = ajustar_a_plantilla(df, corregir_encabezados=corregir_encabezados)
    df, n_vacios = rellenar_vacios(df)   # ninguna celda queda en blanco, como en el archivo de referencia

    stats = {
        "celdas_seleccione": n_seleccione,
        "filas_eliminadas": n_eliminadas,
        "celdas_ortografia": n_ortografia,
        "nacionalidades_corregidas": n_nacionalidad,
        "celdas_rellenadas": n_vacios,
        "columnas_agregadas": cols_agregadas,
        "columnas_extra": cols_extra,
        "col_nombres": col_nombres,
        "col_apellidos": col_apellidos,
    }
    return df, stats
