# Analítica Académica ITP

Dashboard web para explorar el rendimiento académico del Instituto Tecnológico del Putumayo (ITP). La aplicación consolida registros históricos y del periodo en curso desde un archivo Excel, calcula indicadores académicos, permite analizar asignaturas y estudiantes, identifica alertas tempranas y ofrece explicaciones generadas con Google Gemini.

## Características

- Autenticación por roles para restringir el acceso al dashboard.
- Carga y limpieza automática del consolidado Excel.
- Filtros globales por:
  - Periodo académico.
  - Programa.
  - Sede.
  - Semestre curricular de la asignatura (`SEMESTRE_ASIGNATURA`) para el mapa de reprobación.
  - Semestre de la asignatura.
  - Asignatura.
- Indicadores globales:
  - Estudiantes únicos.
  - Matrículas.
  - Nota promedio global.
  - Tasas de aprobación y reprobación.
- Visualizaciones interactivas con Plotly:
  - Tendencia del promedio acumulado histórico por periodo.
  - Tendencia de cantidades aprobadas y reprobadas por periodo.
  - Mapa de reprobación por asignatura y periodo.
  - Promedio e historial de intentos por materia en la ficha individual.
- Ficha académica individual con búsqueda por documento o nombre.
- Detección de estudiantes en riesgo durante el periodo en curso.
- Análisis ejecutivo integral con Google Gemini.
- Explicación con IA del gráfico seleccionado.
- Herramienta administrativa para cargar y consolidar un nuevo archivo `.xlsx`.

## Arquitectura

```text
.
├── app.py                         # Punto de entrada de Streamlit
├── requirements.txt               # Dependencias de Python
├── data/
│   └── archivo_academico.xlsx     # Único Excel local; no debe publicarse
└── src/
    ├── etl/
    │   ├── cleaner.py             # Lectura, limpieza y consolidación del Excel
    │   └── validator.py           # Punto de extensión para validaciones
    ├── services/
    │   ├── metrics.py             # KPIs, rendimiento por asignatura y alertas
    │   └── ai_copilot.py          # Análisis integral y explicación de gráficos
    ├── components/
    │   ├── charts.py              # Gráficas interactivas Plotly
    │   ├── kpi_cards.py           # Componente reservado para tarjetas KPI
    │   └── student_profile.py     # Ficha académica individual
    └── database/
        └── models.py              # Punto de extensión para modelos de datos
```

## Flujo de datos

1. `app.py` llama a `cargar_datos_limpios()`.
2. `src/etl/cleaner.py` lee cuatro hojas del Excel:
   - `2023 registros  académicos`
   - `2024 registros  académicos`
   - `2025 registros  académicos`
   - `2026 registros  académicos`
3. El ETL:
   - Limpia nombres y valores de texto.
   - Convierte comas decimales a números.
   - Convierte las columnas de calificaciones a `float`.
   - Crea `TIPO_REGISTRO` a partir de `ESTADO_BOLETIN`.
   - Une todas las hojas en un único `DataFrame`.
4. Los filtros seleccionados se aplican al `DataFrame`.
5. `metrics.py` calcula los indicadores y tablas.
6. `charts.py` construye la visualización seleccionada.
7. `ai_copilot.py` genera análisis únicamente a partir de resúmenes agregados.

Los datos se cargan con `st.cache_data` para evitar leer y limpiar el Excel en cada interacción.

## Reglas académicas importantes

Estas reglas deben conservarse al modificar el ETL o los cálculos:

- **Periodo en curso:** los registros marcados con `CALIDAD_CIERRE = PERIODO_EN_CURSO_NO_FINAL` no se mezclan con los históricos cerrados para calcular resultados definitivos. Las alertas tempranas utilizan `PRIMER_PARCIAL` y consideran en riesgo a estudiantes con calificación menor de `3.0` en dos o más asignaturas.
- **Registros sin boletín:** los registros `SIN_BOLETIN` corresponden principalmente a homologaciones o reconocimientos. Los KPIs y el rendimiento por asignatura priorizan `CON_BOLETIN` para evitar sesgos positivos.
- **Nota histórica:** el cálculo académico utiliza `DEFINITIVA_ALMACENADA`. No se debe sustituir automáticamente por `NOTA_FINAL_ALMACENADA`.
- **Datos incompletos:** los valores nulos o sin estado deben excluirse del denominador cuando el cálculo requiere un estado válido y deben tener un tratamiento alternativo por nota cuando el código lo contempla.
- **Abandono o ceros:** `TODOS_EN_CERO_VERIFICAR` debe interpretarse de acuerdo con la lógica de calidad de datos y no como una aprobación automática.

## Requisitos

- Python 3.10 o superior.
- pip.
- Un archivo Excel consolidado con las hojas académicas esperadas.
- Una API key de Google AI Studio únicamente si se utilizarán las funciones de IA.

## Instalación local

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En Windows, si PowerShell bloquea la activación del entorno:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## Preparar los datos

Coloca un único archivo Excel dentro de la carpeta `data/`. El nombre es libre:

```text
data/archivo_academico.xlsx
```

El archivo debe contener las hojas académicas de 2023 a 2026. La aplicación detecta automáticamente el único archivo con extensión `.xlsx`, `.xls` o `.xlsm` que encuentre en `data/`; no depende de un nombre fijo. Si encuentra más de un archivo Excel, mostrará un error y solicitará dejar solo uno.

Desde la pestaña **Gestión de Datos**, un administrador puede cargar un nuevo archivo. Al confirmar **Guardar y Consolidar**, se eliminan los archivos Excel anteriores de `data/` y se conserva únicamente el archivo nuevo, usando su nombre original.

## Ejecutar la aplicación

```powershell
streamlit run app.py
```

Después abre la URL mostrada por Streamlit, normalmente:

```text
http://localhost:8501
```

El dashboard inicia con una pantalla de acceso por usuario y contraseña. Las cuentas se almacenan localmente en `auth_users.json` usando hashes PBKDF2; el archivo está excluido de Git.

### Roles de acceso

- **Administrador principal (`admin`):** acceso a todas las pestañas, filtros, análisis y gestión de datos. Puede crear cuentas de profesores.
- **Director de carrera (`director`):** acceso a la visión global y al análisis por estudiante, sin acceso para cargar o reemplazar el Excel.
- **Profesor:** acceso a la visión global limitada a las materias donde aparece como docente en el Excel. No puede consultar la gestión de datos ni perfiles de estudiantes.

Las contraseñas iniciales se entregan al administrador por el canal de configuración y deben cambiarse antes de desplegar la aplicación fuera del entorno local. El administrador crea nuevas cuentas desde **Gestión de Datos → Crear cuenta de profesor**.

## Uso del dashboard

### Visión global

1. Selecciona los filtros en la barra lateral.
2. Revisa los KPIs y el rendimiento por asignatura.
3. Escoge una gráfica mediante los botones de visualización.
4. Usa **Usar IA para explicar este gráfico** para obtener una interpretación del gráfico actual.
5. Usa **Generar análisis ejecutivo integral** para analizar el conjunto agregado de resultados correspondiente a los filtros activos.

### Análisis por estudiante

Busca por número de documento o nombre completo. La ficha muestra información general, promedio histórico, materias aprobadas y reprobadas, y el historial académico disponible.

### Gestión de datos

Esta sección permite cargar un `.xlsx`, revisar filas, periodos y estudiantes detectados, y reemplazar el consolidado local. Debe utilizarse únicamente por personal autorizado y con una copia de respaldo del archivo anterior.

## Integración con Google Gemini

La aplicación usa el paquete `google-genai` y el modelo configurado en `src/services/ai_copilot.py`:

```python
MODELO_GEMINI = "gemini-3.8-flash"
```

La API key se introduce en la barra lateral durante la sesión. No la escribas en el código, en `requirements.txt`, en el README ni en un archivo que vaya a Git. En un despliegue productivo, utiliza `st.secrets` o las variables de entorno del proveedor.

El módulo de IA no envía el `DataFrame` completo: construye un resumen agregado con conteos, distribuciones, notas y resultados por asignatura. Aun así, verifica las políticas institucionales antes de enviar cualquier información derivada a un servicio externo.

## Validación y mantenimiento

Para comprobar que los archivos Python compilan:

```powershell
python -m compileall app.py src
```

Antes de subir cambios:

1. Confirma que el archivo Excel y las API keys no aparecen en `git status`.
2. Ejecuta la compilación.
3. Revisa los filtros con un periodo histórico y con el periodo en curso.
4. Comprueba que las gráficas no mezclen resultados definitivos con `PERIODO_EN_CURSO_NO_FINAL`.
5. Prueba la carga de un archivo de prueba, no del consolidado institucional original.

## Limitaciones conocidas

- La autenticación actual es básica y está pensada para uso local o prototipo.
- La aplicación depende de los nombres de columnas y hojas del Excel institucional.
- La actualización administrativa sobrescribe el archivo consolidado local.
- El análisis con IA requiere conectividad, una API key válida y disponibilidad del modelo configurado.
- No hay una suite de pruebas automatizadas incluida actualmente.
