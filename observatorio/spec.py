"""
Estructura del reporte Power BI "Observatorio", página por página y visual por
visual, tal como está en el archivo .pbix (Report/Layout). Si en Power BI se
cambia un visual, se cambia aquí.

Convenciones:
  * medida: 'personas' (TOTAL DE PERSONAS), 'pct_hombres', 'pct_mujeres',
            'min:<columna>', 'count:<columna>'
  * filtros: filtros propios del visual {columna: [valores]} (panel Filtros de PBI)
  * etiqueta: texto que acompaña al número en una tarjeta (nombre del campo en PBI)
  * Los nombres de columna son los del formulario; se resuelven aunque cambien
    tildes, mayúsculas o espacios dobles.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Visual:
    tipo: str                      # card | pie | donut | barh | barv | barh_pct | barv_pct | barh_clust | barv_clust | line | funnel | matriz
    titulo: str | None = None
    cat: str | None = None
    serie: str | None = None
    medida: str = "personas"
    filtros: dict[str, list[str]] | None = None
    etiqueta: str | None = None
    columnas: str | None = None    # matriz: campo de las columnas
    leyenda: str | None = "bottom"  # bottom | top | left | right | None
    etiquetas_datos: bool = False
    top: int | None = None
    grande: bool = False
    alto: int | None = None
    sin_blanco: bool = False       # omitir la categoría "(En blanco)"
    eje_x: str | None = None       # título del eje de categorías (como en PBI)
    eje_y: str | None = None       # título del eje de valores


@dataclass
class Fila:
    anchos: list[float]
    celdas: list                   # Visual | list[Visual] (apilados) | Fila (anidada) | None


@dataclass
class Pagina:
    nombre: str
    seccion: str
    icono: str
    filas: list[Fila] = field(default_factory=list)


# ── Atajos ──────────────────────────────────────────────────────────────────

def card(etiqueta, medida="personas", filtros=None, titulo=None, grande=False):
    return Visual("card", titulo=titulo, medida=medida, filtros=filtros, etiqueta=etiqueta, grande=grande)


def pie(titulo, cat, leyenda="bottom", etiquetas=False, filtros=None, alto=None):
    return Visual("pie", titulo, cat, leyenda=leyenda, etiquetas_datos=etiquetas, filtros=filtros, alto=alto)


def donut(titulo, cat, leyenda="bottom", etiquetas=False, filtros=None, alto=None):
    return Visual("donut", titulo, cat, leyenda=leyenda, etiquetas_datos=etiquetas, filtros=filtros, alto=alto)


def barh(titulo, cat, serie=None, medida="personas", filtros=None, top=None, alto=None, etiquetas=True, leyenda="bottom",
         sin_blanco=False):
    return Visual("barh", titulo, cat, serie, medida, filtros, top=top, alto=alto, etiquetas_datos=etiquetas, leyenda=leyenda,
                  sin_blanco=sin_blanco)


def barv(titulo, cat, serie=None, medida="personas", filtros=None, alto=None, etiquetas=True, leyenda="bottom",
         sin_blanco=False, eje_x=None, eje_y=None):
    return Visual("barv", titulo, cat, serie, medida, filtros, alto=alto, etiquetas_datos=etiquetas, leyenda=leyenda,
                  sin_blanco=sin_blanco, eje_x=eje_x, eje_y=eje_y)


def matriz(filas, columnas, alto=None, sin_blanco=False):
    return Visual("matriz", cat=filas, columnas=columnas, alto=alto, sin_blanco=sin_blanco)


# Columnas del formulario que se usan en el reporte
SIT_MIG = "SITUACIÓN  MIGRATORIA"
OTROS_KIT = "OTROS (Se debe especificar que otro tipo de KIT humanitario fue entregado)"
EMBARAZO = "EMBARAZO  (Sólo para mujeres)"
MOTIVO = "Motivo de salida del país de origen"
ESCOLARIDAD = "NIVEL DE ESCOLARIDAD / INSTRUCCIÓN"
TIPO_ATENCION = "INDICAR QUE TIPO DE ATENCIÓN EMERGENTE ACTUAL RECIBE"
MDI = "REGISTRO MIGRATORIO  -MDI-"
VIRTE = "VISA VIRTE -MREMH-"
CEDULA = "OBTENCIÓN DE LA CÉDULA ECUATORIANA -REGISTRO CIVIL-"
LUDICOS = "PARTICIPACIÓN EN TALLERES Y ESPACIOS LÚDICO DE RECREACIÓN DE NNA"

# Tarjetas repetidas en las subpáginas de cada sección
_TARJETAS_PERFIL = Fila([337, 267, 259, 249], [
    card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True),
    card(SIT_MIG, medida=f"min:{SIT_MIG}"),
    card("Hombres", medida="pct_hombres"),
    card("Mujeres", medida="pct_mujeres"),
])
_TARJETAS_MIGRATORIA = Fila([250, 298, 297, 318], [
    card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True),
    card("SITUACIÓN MIGRATORIA REGULAR", filtros={SIT_MIG: ["REGULAR"]}),
    card("SITUACIÓN MIGRATORIA IRREGULAR", filtros={SIT_MIG: ["IRREGULAR"]}),
    card("VOCACION DE PERMANENCIA", filtros={"SITUACIÓN DE MOVILIDAD": ["VOCACION DE PERMANENCIA"]}),
])
_TARJETAS_VULNERABILIDAD = Fila([250, 297, 297, 318], [
    card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True),
    card("TIENE DISCAPACIDAD", filtros={"TIENE DISCAPACIDAD": ["SI"]}),
    card("TIENE ENFERMEDAD CATASTRÓFICA", filtros={"TIENE ENFERMEDAD CATASTRÓFICA": ["SI"]}),
    card("EMBARAZO", filtros={"SEXO": ["MUJER"], EMBARAZO: ["SI"]}),
])


def _tarjetas_asistencia(etiqueta, medida="personas", filtros=None):
    return Fila([700, 319], [
        card(etiqueta, medida=medida, filtros=filtros, grande=True),
        card("Total_Unico_Personas", grande=True),
    ])


# ── Secciones (los 6 botones de INICIO) y sus páginas ───────────────────────

SECCIONES: list[tuple[str, str, list[str]]] = [
    ("Perfil de la Población", "perfil_poblacion",
     ["Perfil de la Población", "Rango de Edad", "Distribución por Sexo y Género",
      "Nacionalidades de Origen", "Estado de Escolaridad"]),
    ("Situación Migratoria", "situacion_migratoria",
     ["Situación Migratoria", "Estatus Migratorio General", "Formas de Ingreso al Ecuador",
      "Motivos de Salida del País", "Avance de Documentación"]),
    ("Vulnerabilidades", "vulnerabilidades",
     ["Vulnerabilidades", "Salud y Discapacidad", "Estado de Embarazo",
      "Riesgos en Menores", "Otros Riesgos"]),
    ("Asistencia Humanitaria", "asistencia_humanitaria",
     ["Asistencia Humanitaria", "Atención Emergente Recibida", "Cobertura de Kits de Aseo",
      "Cobertura de Kits de Alimentos", "Cobertura de Kits Escolares"]),
    ("Intervenciones Técnicas", "intervenciones", ["Intervenciones Técnicas"]),
    ("Integración Comunitaria", "integracion", ["Integración Comunitaria"]),
]

PAGINAS: dict[str, Pagina] = {}


def _p(nombre, seccion, icono, filas):
    PAGINAS[nombre] = Pagina(nombre, seccion, icono, filas)


# ═══ 1. PERFIL DE LA POBLACIÓN ══════════════════════════════════════════════
_p("Perfil de la Población", "Perfil de la Población", "perfil_poblacion", [
    Fila([1], [barv("NACIONALIDAD", "NACIONALIDAD", alto=260, etiquetas=False, sin_blanco=True,
                    eje_x="NACIONALIDAD", eje_y="TOTAL DE PERSONAS")]),
    Fila([1], [matriz("NACIONALIDAD", "RANGO DE EDAD", sin_blanco=True)]),
    Fila([470, 246, 273, 236], [
        Fila([1, 1], [
            [card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS"),
             card(SIT_MIG, medida=f"min:{SIT_MIG}", titulo="SITUACIÓN MIGRATORIA PREDOMINANTE")],
            [card("% Hombres", medida="pct_hombres", titulo="Hombre"),
             card("% Mujeres", medida="pct_mujeres", titulo="Mujer")],
        ]),
        pie("Sexo", "SEXO", alto=230),
        pie("RANGO DE EDAD", "RANGO DE EDAD", alto=230),
        pie("SITUACIÓN MIGRATORIA", SIT_MIG, alto=230),
    ]),
])
_p("Rango de Edad", "Perfil de la Población", "rango_edad", [
    _TARJETAS_PERFIL,
    Fila([491, 550], [
        barv("RANGO DE EDAD", "RANGO DE EDAD", alto=430),
        donut(None, "CONDICIÓN SOLO PARA NNA", alto=430),
    ]),
])
_p("Distribución por Sexo y Género", "Perfil de la Población", "sexo_genero", [
    _TARJETAS_PERFIL,
    Fila([491, 550], [
        barh("GÉNERO", "GÉNERO", alto=430),
        pie(None, "SEXO", etiquetas=True, alto=430),
    ]),
])
_p("Nacionalidades de Origen", "Perfil de la Población", "nacionalidades", [
    _TARJETAS_PERFIL,
    Fila([491, 550], [
        barh("NACIONALIDAD", "NACIONALIDAD", alto=430, etiquetas=False, sin_blanco=True),
        pie("INGRESO AL ECUADOR", "FORMA DE INGRESO AL ECUADOR", alto=430),
    ]),
])
_p("Estado de Escolaridad", "Perfil de la Población", "escolaridad", [
    _TARJETAS_PERFIL,
    Fila([530, 550], [
        barh(ESCOLARIDAD, ESCOLARIDAD, alto=430, etiquetas=False),
        pie("ACTUALMENTE ESTÁ ESTUDIANDO", "ACTUALMENTE ESTÁ ESTUDIANDO", alto=430),
    ]),
])

# ═══ 2. SITUACIÓN MIGRATORIA ════════════════════════════════════════════════
_p("Situación Migratoria", "Situación Migratoria", "situacion_migratoria", [
    Fila([1], [barh("TOP 5 MOTIVOS DE SALIDA DEL PAÍS", MOTIVO, top=5, alto=260)]),
    Fila([1], [Visual("barv_pct", "FORMA DE INGRESO", "FORMA DE INGRESO AL ECUADOR", SIT_MIG, leyenda="left", alto=230)]),
    Fila([470, 246, 273, 236], [
        Fila([1, 1], [
            [card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS"),
             card("Primera fecha: SITUACIÓN MIGRATORIA", medida=f"min:{SIT_MIG}", titulo="SITUACIÓN MIGRATORIA PREDOMINANTE")],
            [card("Hombres", medida="pct_hombres"),
             card("Mujeres", medida="pct_mujeres")],
        ]),
        donut("NIVEL DE ESCOLARIDAD", ESCOLARIDAD, leyenda=None, alto=230),
        donut("RANGO DE EDAD", "RANGO DE EDAD", leyenda=None, alto=230),
        donut("SITUACIÓN MIGRATORIA", "SEXO", leyenda=None, alto=230),
    ]),
])
_p("Estatus Migratorio General", "Situación Migratoria", "estatus_migratorio", [
    _TARJETAS_MIGRATORIA,
    Fila([403, 436, 327], [
        Visual("line", "SITUACIÓN MIGRATORIA", SIT_MIG, alto=450),
        Visual("funnel", "SITUACIÓN DE MOVILIDAD", "SITUACIÓN DE MOVILIDAD", alto=430),
        donut("REGISTRO MIGRATORIO (MDI)", MDI, alto=430),
    ]),
])
_p("Formas de Ingreso al Ecuador", "Situación Migratoria", "formas_ingreso", [
    _TARJETAS_MIGRATORIA,
    Fila([403, 444, 327], [
        barv("INGRESO AL ECUADOR", "FORMA DE INGRESO AL ECUADOR", alto=450),
        Visual("barv_clust", "SITUACIÓN DE MOVILIDAD", "SITUACIÓN DE MOVILIDAD", etiquetas_datos=True, alto=430),
        donut("REGISTRO MIGRATORIO (MDI)", MDI, leyenda="top", alto=430),
    ]),
])
_p("Motivos de Salida del País", "Situación Migratoria", "motivos_salida", [
    _TARJETAS_MIGRATORIA,
    Fila([527, 577], [
        Visual("barh_pct", "MOTIVO DE SALIDA DEL PAÍS POR SEXO", MOTIVO, "SEXO", alto=440),
        Visual("barh_clust", "MOTIVO DE SALIDA POR NIVEL DE ESTUDIO", MOTIVO, "ACTUALMENTE ESTÁ ESTUDIANDO", alto=430),
    ]),
])
_p("Avance de Documentación", "Situación Migratoria", "avance_documentacion", [
    _TARJETAS_MIGRATORIA,
    Fila([377, 323, 430], [
        barh("REGISTRO MIGRATORIO (MDI)", MDI, alto=450),
        barv("VISA VIRTE (MREMH)", VIRTE, alto=440),
        donut("OBTENCIÓN DE LA CÉDULA ECUATORIANA", CEDULA, alto=440),
    ]),
])

# ═══ 3. VULNERABILIDADES ════════════════════════════════════════════════════
_p("Vulnerabilidades", "Vulnerabilidades", "vulnerabilidades", [
    Fila([1], [barv("OTRO TIPO DE VULNERABILIDAD", "OTRO TIPO DE VULNERABILIDAD", alto=260, etiquetas=False,
                    eje_x="OTRO TIPO DE VULNERABILIDAD", eje_y="TOTAL DE PERSONAS")]),
    Fila([1], [matriz("NACIONALIDAD", "RANGO DE EDAD", sin_blanco=True)]),
    Fila([470, 240, 256, 243], [
        Fila([1, 1], [
            [card("TOTAL DE PERSONAS", titulo="TOTAL DE PERSONAS"),
             card("TIENE ENFERMEDAD CATASTRÓFICA", filtros={"TIENE ENFERMEDAD CATASTRÓFICA": ["SI"]})],
            [card("TIENE DISCAPACIDAD", filtros={"TIENE DISCAPACIDAD": ["SI"]}),
             card("EMBARAZO", filtros={"SEXO": ["MUJER"], EMBARAZO: ["SI"]})],
        ]),
        donut("EMBARAZO", EMBARAZO, alto=230),
        pie("DISCAPACIDAD", "TIENE DISCAPACIDAD", alto=230),
        pie("ENFERMEDAD CATASTRÓFICA", "TIENE ENFERMEDAD CATASTRÓFICA", alto=230),
    ]),
])
_p("Salud y Discapacidad", "Vulnerabilidades", "salud_discapacidad", [
    _TARJETAS_VULNERABILIDAD,
    Fila([377, 323, 430], [
        barh("TIPO DE DISCAPACIDAD", "Tipo de discapacidad", alto=450),
        barv("SALUD", "SALUD", alto=440),
        donut("ATENCIÓN PSICOLÓGICA", "ATENCIÓN PSICOLÓGICA", alto=440),
    ]),
])
_p("Estado de Embarazo", "Vulnerabilidades", "embarazo", [
    Fila([250, 297, 297, 318], [
        card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True,
             filtros={EMBARAZO: ["SI"], "SEXO": ["MUJER"]}),
        card("TIENE DISCAPACIDAD", filtros={"TIENE DISCAPACIDAD": ["SI"], "SEXO": ["MUJER"]}),
        card("TIENE ENFERMEDAD CATASTRÓFICA",
             filtros={"SEXO": ["MUJER"], "TIENE ENFERMEDAD CATASTRÓFICA": ["SI"], EMBARAZO: ["SI"]}),
        card("SITUACIÓN DE MOVILIDAD MUJER",
             filtros={"SITUACIÓN DE MOVILIDAD": ["VOCACION DE PERMANENCIA"], "SEXO": ["MUJER"], EMBARAZO: ["SI"]}),
    ]),
    Fila([527, 601], [
        pie("EMBARAZO (MUJERES)", EMBARAZO, filtros={"SEXO": ["MUJER"]}, alto=450),
        barh("EMBARAZO POR RANGO DE EDAD", "RANGO DE EDAD", EMBARAZO, filtros={"SEXO": ["MUJER"]}, alto=430),
    ]),
])
_p("Riesgos en Menores", "Vulnerabilidades", "riesgos_menores", [
    Fila([250, 297, 297, 318], [
        card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True),
        card("TIENE DISCAPACIDAD", filtros={"TIENE DISCAPACIDAD": ["SI"]}),
        card("TIENE ENFERMEDAD CATASTRÓFICA", filtros={"TIENE ENFERMEDAD CATASTRÓFICA": ["SI"]}),
        card(EMBARAZO, filtros={EMBARAZO: ["SI"], "RANGO DE EDAD": ["ADOLESCENTE"], "SEXO": ["MUJER"]}),
    ]),
    Fila([377, 737], [
        barv("CONDICIÓN SOLO PARA NNA", "CONDICIÓN SOLO PARA NNA", alto=450),
        [barh("CONDICIÓN DEL NNA POR ZONA", "ZONA", "CONDICIÓN SOLO PARA NNA", alto=270),
         matriz("CONDICIÓN SOLO PARA NNA", "CON QUIEN SE ENCUENTRA EL NNA")],
    ]),
])
_p("Otros Riesgos", "Vulnerabilidades", "otros_riesgos", [
    _TARJETAS_VULNERABILIDAD,
    Fila([527, 586], [
        barh("OTRO TIPO DE VULNERABILIDAD", "OTRO TIPO DE VULNERABILIDAD", alto=450),
        barv("RANGO DE EDAD POR OTRO TIPO DE VULNERABILIDAD", "RANGO DE EDAD", "OTRO TIPO DE VULNERABILIDAD", alto=440),
    ]),
])

# ═══ 4. ASISTENCIA HUMANITARIA ══════════════════════════════════════════════
_ALIMENTOS = ["ALIMENTOS", "ALMENTOS", "ALIMENTACION"]
_p("Asistencia Humanitaria", "Asistencia Humanitaria", "asistencia_humanitaria", [
    Fila([1], [barv("TIPO DE ATENCIÓN EMERGENTE", TIPO_ATENCION, alto=260, etiquetas=False,
                    eje_x=TIPO_ATENCION, eje_y="TOTAL DE PERSONAS")]),
    Fila([1], [matriz("NACIONALIDAD", "RANGO DE EDAD", sin_blanco=True)]),
    Fila([470, 240, 256, 243], [
        Fila([1, 1], [
            [card("TOTAL DE PERSONAS", titulo="TOTAL DE PERSONAS"),
             card("KIT DE ASEO SI", filtros={"KIT DE ASEO": ["SI"]})],
            [card("KIT DE ALIMENTOS (personas)", filtros={OTROS_KIT: _ALIMENTOS}),
             card("KIT ESCOLAR SI", filtros={"KIT ESCOLAR": ["SI"]})],
        ]),
        donut("ATENCIÓN DE TRABAJO SOCIAL", "ATENCIÓN DE TRABAJO SOCIAL", alto=230),
        pie("ATENCIÓN PSICOLÓGICA", "ATENCIÓN PSICOLÓGICA", alto=230),
        pie("ATENCIÓN LEGAL", "ATENCIÓN LEGAL", alto=230),
    ]),
])
_p("Atención Emergente Recibida", "Asistencia Humanitaria", "atencion_emergente", [
    _tarjetas_asistencia("ATENCIÓN EMERGENTE   SI", filtros={"ATENCIÓN EMERGENTE": ["SI"]}),
    Fila([700, 457], [
        barh(TIPO_ATENCION, TIPO_ATENCION, "SEXO", alto=430),
        pie("TIPO DE ATENCIÓN EMERGENTE", "ATENCIÓN EMERGENTE", alto=430),
    ]),
])
_p("Cobertura de Kits de Aseo", "Asistencia Humanitaria", "kits_aseo", [
    _tarjetas_asistencia("KIT DE ASEO  SI", filtros={"KIT DE ASEO": ["SI"]}),
    Fila([701, 457], [
        barh("KIT DE ASEO POR ZONA", "ZONA", filtros={"KIT DE ASEO": ["NO"]}, alto=430),
        pie("KIT DE ASEO", "KIT DE ASEO", alto=430),
    ]),
])
# Kit de alimentos: se cuenta a la persona (única) que en algún reporte tiene
# 'ALIMENTOS' en la columna OTROS del kit humanitario. Las variantes
# ('ALIMENTACIÓN', 'ALMENTOS') se unifican a 'ALIMENTOS' en la limpieza.
_p("Cobertura de Kits de Alimentos", "Asistencia Humanitaria", "kits_alimentos", [
    _tarjetas_asistencia("KIT DE ALIMENTOS  (personas únicas)", filtros={OTROS_KIT: _ALIMENTOS}),
    Fila([700, 457], [
        barh("KIT DE ALIMENTOS POR ZONA", "ZONA", filtros={OTROS_KIT: _ALIMENTOS}, alto=430),
        pie("KIT DE ALIMENTOS", OTROS_KIT, alto=430),
    ]),
])
_p("Cobertura de Kits Escolares", "Asistencia Humanitaria", "kits_escolares", [
    _tarjetas_asistencia("KIT ESCOLAR  SI", filtros={"KIT ESCOLAR": ["SI"]}),
    Fila([700, 457], [
        barh("KIT ESCOLAR POR ZONA", "ZONA", filtros={"KIT ESCOLAR": ["NO"]}, alto=430),
        pie("KIT ESCOLAR", "KIT ESCOLAR", alto=430),
    ]),
])

# ═══ 5. INTERVENCIONES TÉCNICAS ═════════════════════════════════════════════
_p("Intervenciones Técnicas", "Intervenciones Técnicas", "intervenciones", [
    Fila([233, 259, 224, 229], [
        card("Total_Unico_Personas", titulo="TOTAL DE PERSONAS", grande=True),
        card("TRABAJO SOCIAL  SI", filtros={"ATENCIÓN DE TRABAJO SOCIAL": ["SI"]}),
        card("ATENCIÓN PSICOLÓGICA  SI", filtros={"ATENCIÓN PSICOLÓGICA": ["SI"]}),
        card("ATENCIÓN LEGAL  SI", filtros={"ATENCIÓN LEGAL": ["SI"]}),
    ]),
    Fila([671, 400], [
        barh("RANGO DE EDAD POR ATENCIÓN LEGAL", "RANGO DE EDAD", "ATENCIÓN LEGAL", alto=430),
        [donut("ATENCIÓN DE TRABAJO SOCIAL", "ATENCIÓN DE TRABAJO SOCIAL", alto=232),
         donut("ATENCIÓN PSICOLÓGICA", "ATENCIÓN PSICOLÓGICA", alto=227)],
    ]),
])

# ═══ 6. INTEGRACIÓN COMUNITARIA ═════════════════════════════════════════════
_p("Integración Comunitaria", "Integración Comunitaria", "integracion", [
    Fila([258, 258, 225, 228, 228], [
        card("TALLERES DE CAPACITACIÓN SI", filtros={"PARTICIPACIÓN A TALLERES DE CAPACITACIÓN": ["SI"]}),
        card("TALLERES DE SENSIBILIZACIÓN SI", filtros={"PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN": ["SI"]}),
        card("ENCUENTROS COMUNITARIOS  SI", filtros={"PARTICIPACIÓN EN ENCUENTROS COMUNITARIOS": ["SI"]}),
        card("TALLERES Y ESPACIOS LÚDICO DE RECREACIÓN DE NNA  SI", filtros={LUDICOS: ["SI"]}),
        card("REDES COMUNITARIAS  SI", filtros={"INSERCIÓN A REDES COMUNITARIAS": ["SI"]}),
    ]),
    Fila([365, 447, 337], [
        donut("PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN", "PARTICIPACIÓN A TALLERES DE SENSIBILIZACIÓN", alto=242),
        Visual("barh_clust", None, "ZONA", filtros={"INSERCIÓN A REDES COMUNITARIAS": ["NO"]}, alto=292, etiquetas_datos=True,
               etiqueta="INSERCIÓN A REDES COMUNITARIAS  NO"),
        donut("TALLERES DE CAPACITACIÓN", "PARTICIPACIÓN A TALLERES DE CAPACITACIÓN", alto=242),
    ]),
    Fila([365, 447, 337], [
        donut("ESPACIOS LÚDICOS", LUDICOS, alto=242),
        None,
        donut("ENCUENTROS COMUNITARIOS", "PARTICIPACIÓN EN ENCUENTROS COMUNITARIOS", alto=242),
    ]),
])


def seccion_de(nombre_pagina: str) -> tuple[str, str, list[str]] | None:
    for sec in SECCIONES:
        if nombre_pagina in sec[2]:
            return sec
    return None
