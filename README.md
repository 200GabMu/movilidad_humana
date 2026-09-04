# Movilidad Humana · Unificador + Panel (Streamlit, modular)

Fundación Mensajeros de la Paz · Servicio de Movilidad Humana

## Instalar y correr

**Windows (lo más fácil):** descomprime el zip y haz doble clic en `ejecutar.bat`.
La primera vez instala todo (tarda 1-2 min); luego abre el navegador en
http://localhost:8501. Necesitas tener Python 3.11 o superior instalado
(python.org, marcando "Add Python to PATH").

Manual:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

**Cuenta del administrador:** la primera vez que abras 🔐 Acceso, la app pide
crear la cuenta (usuario y contraseña). No hace falta ningún archivo de
configuración. Si prefieres fijarla por archivo o en Streamlit Cloud, pon
`ADMIN_PASSWORD = "tu-clave"` en `.streamlit/secrets.toml` (o en Settings → Secrets)
y la cuenta `admin` se crea sola con esa clave.

Opcional: logo — copia el escudo como `assets/logo.png` (aparece en la barra azul).

## Cuentas y roles

| Rol | Cómo entra | Qué puede hacer |
|---|---|---|
| Usuario final | Sin cuenta | 📊 Panel (página de inicio) |
| operador | 🔐 Acceso → usuario + contraseña | 📤 Subir reportes (solo *agregar*) · 🗂️ ver/descargar historial |
| administrador | 🔐 Acceso → usuario + contraseña | Todo: reemplazar, activar/eliminar versiones y 👥 **Usuarios** (crear cuentas, cambiar rol o clave, desactivar, eliminar) |

La primera cuenta (administrador) se crea desde la propia página **Acceso** en el
primer arranque. Desde ahí, las demás cuentas se crean en la página
**Usuarios**; quedan en `data/usuarios.json` con la contraseña cifrada
(PBKDF2-SHA256), nunca en claro. Tras 5 intentos fallidos el acceso espera 30 s.
Cada versión del historial registra qué usuario la subió.

## Módulos

| Página | Qué hace |
|---|---|
| 🔐 Acceso | Iniciar / cerrar sesión (usuario + contraseña) |
| 👥 Usuarios | Solo administradores: crear y administrar cuentas y roles |
| 📤 Unificar reportes | Sube `.xlsx` → unifica hojas `REPORTE MENSUAL…` → limpia (Paso 2) → **guarda una versión nueva** |
| 🗂️ Historial | Lista de versiones; **activar** una anterior (deshacer), descargar limpio/crudo/originales, eliminar, nota |
| 🔍 Buscar persona | Solo con sesión (datos personales): busca por nombre/apellido y muestra la ficha, los meses atendida, los servicios recibidos y sus registros; filtro por año. Se abre desde la portada, el panel administrador o el menú lateral azul |
| 📊 Panel | Réplica del reporte Power BI "Observatorio": INICIO → 6 secciones → 22 páginas, con la barra de segmentadores (Nacionalidad, Ciudad, Rango de edad, Sexo, Situación migratoria, Año, Mes) |

## Estructura

```
app.py                  entrada: encabezado azul global + navegación
core/                   lógica pura (sin Streamlit, probable por consola)
  consolidacion.py      lectura de hojas, encabezados combinados, anti-duplicados, fusión incremental
  limpieza.py           Paso 2: Seleccione→vacío, mayúsculas, nacionalidad, relleno, fecha real
  exportar.py           Excel de salida
  derivados.py          AÑO / MES / RANGO DE EDAD + detección de columnas de filtro
  almacen.py            versiones en disco (parquet + meta.json + originales) e historial.json
  usuarios.py           cuentas y roles (data/usuarios.json, claves cifradas)
  pipeline.py           unificar → fusionar → limpiar → guardar versión
observatorio/           réplica del Power BI
  spec.py               páginas y visuales (extraído del .pbix: tipo, campos, filtros, títulos)
  medidas.py            medidas DAX traducidas (TOTAL DE PERSONAS, % Hombres/Mujeres, Min, CountNonNull)
  visuales.py           tarjetas, pastel/anillo, barras, línea, embudo, matriz (Plotly)
  navegacion.py         INICIO, menú lateral por sección
ui/                     encabezado, barra de filtros, acceso admin
vistas/                 una página por módulo
data/                   se crea sola: historial.json + versiones/v_AAAAMMDD_HHMMSS/
tests/                  Excel sintéticos con la estructura de la plantilla + pruebas
```

## Cómo funciona el historial (copia de seguridad)

Cada vez que se unifica se crea `data/versiones/v_<fecha_hora>/` con:
`crudo.parquet` (tal cual sale de los Excel), `limpio.parquet` (Paso 2, lo que
lee el panel), `meta.json` y la carpeta `originales/` con los `.xlsx` subidos.
Nunca se sobrescribe nada. Si alguien sube algo equivocado: Historial →
seleccionar la versión buena → **Activar**. Para respaldar todo, basta copiar
la carpeta `data/`.

Modo **Agregar**: solo entran hojas nuevas (una hoja se considera repetida si
coincide año + nombre de hoja + número de filas, la misma regla de la versión
original). Modo **Reemplazar**: el consolidado nuevo es solo lo que se sube.

## Publicar en Streamlit Cloud y guardar los datos para siempre

1. Sube la carpeta del proyecto a un repositorio **privado** de GitHub (el
   consolidado tiene datos personales). Puedes incluir `data/` para que la
   nube arranque con datos.
2. En share.streamlit.io → *Create app* → repositorio, rama `main`,
   archivo `app.py`, Python 3.11.
3. **Copia de seguridad automática.** El disco de Streamlit Cloud se borra en
   cada reinicio, así que la app guarda `data/` en una rama del repositorio
   llamada `datos` (separada de `main`: guardar datos no redespliega la app)
   y la recupera sola al arrancar. Para activarla pega en *Settings → Secrets*:

   ```toml
   NUBE = true
   GITHUB_REPO = "TU_USUARIO/movilidad-humana"
   GITHUB_TOKEN = "github_pat_xxxxxxxx"
   ```

   El token se crea en GitHub → *Settings → Developer settings → Personal
   access tokens → Fine-grained tokens → Generate new token*: acceso solo a
   ese repositorio y permiso **Contents: Read and write**. Cuando caduque, el
   panel administrador avisa y basta con pegar uno nuevo en Secrets.
4. Cada unificación, cambio de versión o de usuarios se sube a GitHub al
   instante (barra de progreso "Guardando copia en GitHub…"). El botón
   **Sincronizar ahora** del panel administrador lo fuerza a mano.

Sin esos secretos (por ejemplo en tu computador) la app funciona igual, solo
que guarda en el disco local. `python tests/test_nube.py` prueba la copia
contra un GitHub simulado.

## Pruebas

```bash
python tests/crear_excel_prueba.py   # genera tests/datos_prueba/*.xlsx
python tests/test_pipeline.py        # núcleo de punta a punta
python tests/test_ui.py              # páginas con streamlit.testing (sin navegador)
python tests/test_nube.py            # copia de seguridad en GitHub (servidor simulado)
```

## Plantilla de salida y ortografía

**Lectura por posición.** La plantilla mensual tiene siempre las mismas 78
columnas en el mismo orden, pero los nombres cambian entre años ('Edad años'
vs 'EDAD - AÑOS', 'TELÉFONO' en vez de 'Teléfono de contacto de la MADRE', un
encabezado vacío, una columna en blanco de más). Por eso cada hoja se empareja
con la plantilla por POSICIÓN, comprobando columnas ancla (N°, ZONA, APELLIDOS,
FECHA DE NACIMIENTO, SEXO…). Si una hoja no encaja, se avisa y se empareja por
nombre. Además, en la limpieza un correo escrito en una columna que no es de
correo se vacía, y en OTROS (kit humanitario) 'ALIMENTACIÓN'/'ALMENTOS' pasan a
'ALIMENTOS'.

El consolidado limpio sale SIEMPRE con las 82 columnas y el orden de
`REPORTE_CONSOLIDADO_MOVILIDAD_HUMANA_FINAL.xlsx` (`core/plantilla.py`): las
que falten se agregan vacías, las que sobren van al final. Opcionalmente se
corrige la ortografía de los encabezados (ACOGIMINETO → ACOGIMIENTO,
Parentesto → Parentesco, "del MADRE" → "de la MADRE"…); es una casilla en
Unificar, desactívala si otro sistema lee el archivo con los nombres viejos.

Los valores de las celdas se corrigen siempre (`core/ortografia.py`): tildes
(SITUACION → SITUACIÓN, BASICOS → BÁSICOS), errores de tipeo (LIBERTAR →
LIBERTAD, PESONAS → PERSONAS), puntuación (`A ,B` → `A, B`) y variantes de una
misma opción (ESTUDIO → ESTUDIOS, `NNA -ACOMPAÑADO` → `NNA - ACOMPAÑADO`).
Nombres, apellidos, direcciones, teléfonos y correos no se tocan. Para agregar
correcciones edita los diccionarios `PALABRAS` y `CELDAS`; la sección "Valores
únicos por columna" de Unificar muestra lo que aún queda escrito de varias formas.

## El Panel y el Power BI

La estructura se tomó del archivo `.pbix` (Report/Layout + modelo):

* **Medidas**: `TOTAL DE PERSONAS` = personas distintas por (NOMBRES, APELLIDOS,
  FECHA DE NACIMIENTO); `% Hombres` / `% Mujeres` = total con SEXO = Hombre/Mujer
  dividido por el total ignorando solo el filtro de SEXO. Están en
  `observatorio/medidas.py`.
* **Columnas**: las del formulario. `AÑO` sale del nombre del archivo y `MES`
  del nombre de la hoja (igual que en el Excel que alimentaba al Power BI).
  `RANGO DE EDAD` se respeta tal cual viene (NN · ADOLESCENTE · ADULTO · ADULTO MAYOR).
* **Tema**: colores de datos y tipografía del tema "Mensajeros de la Paz - Azul y
  Amarillo" del .pbix (`observatorio/visuales.py`).
* Para cambiar un visual (título, campo, filtro) edita `observatorio/spec.py`.

## Ajustes frecuentes

* Rangos de edad (solo si el formulario no trae la columna): `RANGOS_EDAD` en `core/derivados.py`.
* Carpeta de datos: variable de entorno `MH_DATA_DIR` (por defecto `./data`).
* Orden/columnas de los filtros: `FILTROS` en `core/derivados.py`.
* Colores del encabezado: `AZUL` en `ui/estilos.py`.
* Nacionalidades unificadas: `MAPA_NACIONALIDADES` en `core/limpieza.py`.
