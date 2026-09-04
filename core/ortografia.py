"""
Corrección ortográfica y unificación de valores escritos de varias formas.

Se aplica DESPUÉS de normalizar_texto (todo en mayúsculas, un solo espacio),
así los diccionarios se escriben una sola vez en mayúsculas.

Tres niveles, en este orden:
  1) Puntuación: espacios alrededor de comas y barras, comas colgantes.
  2) Palabras (con límites de palabra): tildes que faltan y errores de tipeo
     que son inequívocos en cualquier columna  (BASICOS -> BÁSICOS,
     SITUACION -> SITUACIÓN, LIBERTAR -> LIBERTAD, PESONAS -> PERSONAS…).
  3) Celda completa: variantes de una misma opción del formulario que
     deben quedar como UNA sola categoría (ESTUDIO -> ESTUDIOS,
     'AMENAZAS CONTRA LA VIDA/SEGURIDAD/LIBERTAD E INTEGRIDAD' ->
     'AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD').

Para agregar una corrección basta añadir una línea al diccionario que
corresponda. El botón "Valores únicos por columna" de la página Unificar
sirve para descubrir variantes nuevas.
"""

from __future__ import annotations

import re

import pandas as pd

from .consolidacion import COLS_TRAZABILIDAD

# Valor canónico para "no aplica" (así lo usa el formulario y el reporte)
NO_APLICA = "No aplica"

# Columnas que NO se corrigen: datos de identidad y contacto (un apellido
# "PAIS" o un nombre "NINA" no son faltas de ortografía).
_PALABRAS_EXCLUIR = ("NOMBRE", "APELLIDO", "DIRECCI", "TEL", "NUMERO", "NÚMERO", "CODIGO", "CÓDIGO", "CORREO")


def columna_corregible(col) -> bool:
    c = str(col).upper()
    return col not in COLS_TRAZABILIDAD and not any(p in c for p in _PALABRAS_EXCLUIR)

# ── 2) Palabras: {palabra mal escrita: palabra correcta} ────────────────────
PALABRAS = {
    # tildes
    "SITUACION": "SITUACIÓN",
    "ECONOMICA": "ECONÓMICA", "ECONOMICO": "ECONÓMICO",
    "SOCIOECONOMICA": "SOCIOECONÓMICA", "SOCIECONOMICA": "SOCIOECONÓMICA", "SOCIECONÓMICA": "SOCIOECONÓMICA",
    "CONDICION": "CONDICIÓN", "PAIS": "PAÍS", "BUSQUEDA": "BÚSQUEDA",
    "PERSECUCION": "PERSECUCIÓN", "ALIMENTACION": "ALIMENTACIÓN", "BASICOS": "BÁSICOS", "BASICA": "BÁSICA",
    "VICTIMA": "VÍCTIMA", "REUNIFICACION": "REUNIFICACIÓN", "VOCACION": "VOCACIÓN",
    "TRANSITO": "TRÁNSITO", "TRAMITE": "TRÁMITE", "POLITICA": "POLÍTICA", "FISICA": "FÍSICA",
    "MULTIPLE": "MÚLTIPLE", "TECNOLOGICOS": "TECNOLÓGICOS", "ARABE": "ÁRABE",
    "ESCOLARIZACION": "ESCOLARIZACIÓN", "REGULARIZACION": "REGULARIZACIÓN",
    "PROSTITUCION": "PROSTITUCIÓN", "MEDICA": "MÉDICA", "CEDULA": "CÉDULA", "TARDIA": "TARDÍA",
    "APATRIDA": "APÁTRIDA", "INDIGENA": "INDÍGENA", "TIA": "TÍA", "TIO": "TÍO",
    "PSICOLOGICA": "PSICOLÓGICA", "ATENCION": "ATENCIÓN", "EDUCACION": "EDUCACIÓN",
    "INSERCION": "INSERCIÓN", "PARTICIPACION": "PARTICIPACIÓN", "SENSIBILIZACION": "SENSIBILIZACIÓN",
    "CAPACITACION": "CAPACITACIÓN", "OBTENCION": "OBTENCIÓN", "ESTADIA": "ESTADÍA",
    "NACIO": "NACIÓ", "DEPRESION": "DEPRESIÓN", "DOCUMENTACION": "DOCUMENTACIÓN",
    "INSCRIPCION": "INSCRIPCIÓN", "IDENTIFICACION": "IDENTIFICACIÓN",
    # errores de tipeo
    "LIBERTAR": "LIBERTAD", "SEGURIDA": "SEGURIDAD", "AMENZA": "AMENAZA", "ALIIMENTACION": "ALIMENTACIÓN",
    "ALMENTOS": "ALIMENTOS", "ESTIDIOS": "ESTUDIOS", "PESONAS": "PERSONAS", "FAMILAR": "FAMILIAR",
    "PARTIDAD": "PARTIDA", "PAARTIDA": "PARTIDA", "NACIMEIENTO": "NACIMIENTO", "DENACIMIENTO": "DE NACIMIENTO",
    "NINA": "NIÑA", "NINO": "NIÑO", "ACOGIMINETO": "ACOGIMIENTO", "PARENTESTO": "PARENTESCO",
    "ECUATORIAN": "ECUATORIANA", "VENEZOLNA": "VENEZOLANA",
}

# ── 3) Celda completa: {valor tal cual: valor unificado} ────────────────────
CELDAS = {
    "NO APLICA": NO_APLICA, "N/A": NO_APLICA, "NA": NO_APLICA,
    # Motivo de salida del país
    "ESTUDIO": "ESTUDIOS",
    "AMENAZAS CONTRA LA VIDA/SEGURIDAD/LIBERTAD E INTEGRIDAD": "AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD",
    "AMENAZAS EN CONTRA DE SU VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD": "AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD",
    "AMENAZA CONTRA LA VIDA, SEGURIDAD Y LIBERTAD E INTEGRIDAD": "AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD",
    "AMENAZAS CONTRA LA VIDA SEGURIDAD Y LIBERTAD": "AMENAZAS CONTRA LA VIDA, SEGURIDAD, LIBERTAD E INTEGRIDAD",
    "FALTA DE ACCESO A MEDICINA ALIMENTACIÓN Y SERVICIOS BÁSICOS": "FALTA DE ACCESO A MEDICINA, ALIMENTACIÓN Y SERVICIOS BÁSICOS",
    "FALTA DE ACCESO A MEDICINA, SALUD, ALIMENTACIÓN Y SERVICIOS BÁSICOS": "FALTA DE ACCESO A MEDICINA, ALIMENTACIÓN Y SERVICIOS BÁSICOS",
    "BÚSQUEDA DE MEJOR CALIDAD DE VIDA": "MEJOR CALIDAD DE VIDA",
    "BUSCAR MEJOR CALIDAD DE VIDA": "MEJOR CALIDAD DE VIDA",
    "NO APLICA NACIÓ EN ECUADOR": "NACIÓ EN ECUADOR", "NO APLICA NACE ECUADOR": "NACIÓ EN ECUADOR",
    # Documentos de viaje (respuesta "otro")
    "PARTIDA NACIMIENTO": "PARTIDA DE NACIMIENTO", "PARTIDA DE NACI": "PARTIDA DE NACIMIENTO",
    "PARTIDA": "PARTIDA DE NACIMIENTO", "PARTIDO DE NACIMIENTO": "PARTIDA DE NACIMIENTO",
    "P/N": "PARTIDA DE NACIMIENTO",
    "PARTIDA DE NACIMIENTO ECUATORIANO": "PARTIDA DE NACIMIENTO ECUATORIANA",
    "ACTA DE NACIDO VIVO": "CERTIFICADO DE NACIDO VIVO", "NACIDO VIVO": "CERTIFICADO DE NACIDO VIVO",
    # Condición NNA (espaciado uniforme)
    "NNA -ACOMPAÑADO": "NNA - ACOMPAÑADO", "NNA-ACOMPAÑADO": "NNA - ACOMPAÑADO",
    "NNA-SEPARADO": "NNA - SEPARADO", "NNA-NO ACOMPAÑADO": "NNA - NO ACOMPAÑADO",
    # Vulnerabilidad (respuesta "otro")
    "SOCIOECONÓMICA": "SITUACIÓN SOCIOECONÓMICA",
    "SITUACIÓN SOCIOECONÓMICA/CONDICIÓN MIGRATORIA": "SITUACIÓN SOCIOECONÓMICA Y CONDICIÓN MIGRATORIA",
    "SITUACIÓN SOCIOECONÓMICA / CONDICIÓN MIGRATORIA": "SITUACIÓN SOCIOECONÓMICA Y CONDICIÓN MIGRATORIA",
    "NO ESCOLARIZADA": "NO ESCOLARIZADO", "NIÑO NO ESCOLARIZADO": "NO ESCOLARIZADO",
    "SIN ESCOLARIDAD": "FALTA DE ESCOLARIZACIÓN",
    "SIN MEDIOS DE VIDA ESTABLE": "FALTA DE MEDIOS DE VIDA",
}

_RE_PALABRA = re.compile(r"[A-ZÁÉÍÓÚÜÑ]+")


def _puntuacion(texto: str) -> str:
    t = re.sub(r"\s*,\s*", ", ", texto)          # 'A ,B' / 'A,B' -> 'A, B'
    t = re.sub(r"\s*/\s*", "/", t)               # 'A / B' -> 'A/B'
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"[,\s]+$", "", t)                # coma colgante al final
    return t


def _palabras(texto: str) -> str:
    return _RE_PALABRA.sub(lambda m: PALABRAS.get(m.group(0), m.group(0)), texto)


def corregir_valor(valor):
    """Aplica los tres niveles a un solo valor de celda."""
    if not isinstance(valor, str):
        return valor
    t = _puntuacion(valor)
    t = _palabras(t)
    return CELDAS.get(t, t)


def corregir_ortografia(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Corrige todas las columnas de texto salvo correos y trazabilidad.
    Devuelve (df, número de celdas que cambiaron)."""
    df = df.copy()
    cambios = 0
    for col in df.columns:
        if not columna_corregible(col):
            continue
        antes = df[col]
        despues = antes.map(corregir_valor)
        cambios += int(((antes != despues) & antes.notna()).sum())
        df[col] = despues
    return df, cambios


def valores_unicos(df: pd.DataFrame, max_valores: int = 300) -> pd.DataFrame:
    """Tabla (Columna, Valor, Registros) para revisar variantes que aún
    queden; omite columnas con demasiados valores (nombres, teléfonos…)."""
    filas = []
    for col in df.columns:
        if col in COLS_TRAZABILIDAD:
            continue
        s = df[col].dropna().astype(str).str.strip()
        vc = s.value_counts()
        if len(vc) == 0 or len(vc) > max_valores:
            continue
        for val, n in vc.items():
            filas.append((str(col), val, int(n)))
    return pd.DataFrame(filas, columns=["Columna", "Valor", "Registros"])
