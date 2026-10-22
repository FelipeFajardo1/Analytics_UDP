import json
import pandas as pd


MODELO_GEMINI = "gemini-3.8-flash"


def _resumen_anonimo(df):
    """Construye un resumen agregado sin nombres ni identificadores personales."""
    trabajo = df.copy()
    if "TIPO_REGISTRO" in trabajo.columns:
        con_boletin = trabajo[trabajo["TIPO_REGISTRO"] == "CON_BOLETIN"]
        if not con_boletin.empty:
            trabajo = con_boletin

    resumen = {
        "registros_analizados": int(len(trabajo)),
        "columnas_disponibles": list(trabajo.columns),
    }
    if "ID_ESTUDIANTE" in trabajo:
        resumen["estudiantes_unicos"] = int(trabajo["ID_ESTUDIANTE"].nunique())
    if "DEFINITIVA_ALMACENADA" in trabajo:
        notas = pd.to_numeric(trabajo["DEFINITIVA_ALMACENADA"], errors="coerce").dropna()
        if not notas.empty:
            resumen["nota_promedio"] = round(float(notas.mean()), 2)
            resumen["nota_mediana"] = round(float(notas.median()), 2)
            resumen["nota_minima"] = round(float(notas.min()), 2)
            resumen["nota_maxima"] = round(float(notas.max()), 2)
            resumen["notas_menores_que_3"] = int((notas < 3).sum())

    if "ESTADO_MATERIA" in trabajo:
        estados = trabajo["ESTADO_MATERIA"].dropna().astype(str).str.upper()
        resumen["estados_materia"] = {
            str(estado): int(cantidad)
            for estado, cantidad in estados.value_counts().head(10).items()
        }

    for columna in ("PERIODO", "PROGRAMA", "SEDE", "SEMESTRE_ASIGNATURA"):
        if columna in trabajo:
            valores = trabajo[columna].dropna().astype(str)
            resumen[f"distribucion_{columna.lower()}"] = {
                str(valor): int(cantidad)
                for valor, cantidad in valores.value_counts().head(20).items()
            }

    if "ASIGNATURA" in trabajo:
        filas_materias = []
        for asignatura, grupo in trabajo.groupby("ASIGNATURA"):
            fila = {"asignatura": str(asignatura)[:80], "inscritos": int(len(grupo))}
            if "DEFINITIVA_ALMACENADA" in grupo:
                notas = pd.to_numeric(
                    grupo["DEFINITIVA_ALMACENADA"], errors="coerce"
                ).dropna()
                if not notas.empty:
                    fila["promedio"] = round(float(notas.mean()), 2)
                    fila["reprobados_por_nota"] = int((notas < 3).sum())
            if "ESTADO_MATERIA" in grupo:
                fila["perdidos"] = int(
                    grupo["ESTADO_MATERIA"].astype(str).str.upper()
                    .str.contains("PERDIO", na=False).sum()
                )
            filas_materias.append(fila)
        resumen["resumen_por_asignatura"] = sorted(
            filas_materias,
            key=lambda fila: fila.get("perdidos", fila.get("reprobados_por_nota", 0)),
            reverse=True,
        )[:30]

    return resumen


def _generar_con_gemini(prompt, api_key):
    """Genera texto con el SDK vigente de Google Gen AI."""
    try:
        from google import genai
    except ImportError:
        return (
            "La libreria google-genai no esta instalada. "
            "Instalela con: pip install -U google-genai"
        )

    try:
        cliente = genai.Client(api_key=api_key.strip())
        respuesta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt,
        )
        texto = getattr(respuesta, "text", None)
        if texto:
            return texto
        return "Gemini no devolvio texto para esta solicitud."
    except Exception as error:
        return f"Error al generar analisis con IA: {error}"


def generar_analisis_ia(df, api_key):
    """
    Genera un análisis ejecutivo con IA usando Google Gemini.
    
    Extrae un resumen estadístico 100% anonimizado del DataFrame
    (promedio global, tasa de reprobación general, número de estudiantes activos
    y las 3 materias con mayor índice de pérdida).
    
    Args:
        df: DataFrame con datos limpios
        api_key: API Key de Google Gemini
        
    Returns:
        Respuesta generada por el modelo de IA
    """
    if df is None or df.empty:
        return "No hay datos suficientes para generar un análisis."
    
    if not api_key or api_key.strip() == "":
        return "Por favor, ingrese su API Key de Google en la barra lateral."
    
    resumen = _resumen_anonimo(df)
    resumen_texto = json.dumps(resumen, ensure_ascii=False, indent=2)
    prompt = f"""Eres un analista experto en resultados académicos.
Analiza TODOS los apartados del resumen agregado: periodos, programas, sedes,
semestres, asignaturas, notas y estados. Entrega un análisis ejecutivo claro
con estas secciones:
1. Panorama general y hallazgos principales.
2. Comparaciones relevantes entre periodos, programas, sedes y semestres.
3. Asignaturas y patrones con mayor riesgo.
4. Recomendaciones concretas y priorizadas.
Usa únicamente los datos proporcionados, indica cuando falte información y no
menciones estudiantes, nombres ni identificadores individuales.

Resumen agregado:
{resumen_texto}"""
    return _generar_con_gemini(prompt, api_key)


def explicar_grafico_ia(df, api_key, nombre_grafico, descripcion_grafico):
    """Explica únicamente la gráfica seleccionada usando datos agregados."""
    if df is None or df.empty:
        return "No hay datos suficientes para explicar esta gráfica."
    if not api_key or not api_key.strip():
        return "Por favor, ingrese su API Key de Google en la barra lateral."

    resumen_texto = json.dumps(_resumen_anonimo(df), ensure_ascii=False, indent=2)
    prompt = f"""Eres un analista académico. Explica la gráfica seleccionada
de forma breve y útil para un directivo.
Gráfica: {nombre_grafico}
Descripción: {descripcion_grafico}
Incluye: qué representa, dos o tres hallazgos visibles, posibles riesgos y
una recomendación. No inventes cifras, no menciones datos individuales y usa
solo el resumen agregado.

Resumen agregado:
{resumen_texto}"""
    return _generar_con_gemini(prompt, api_key)
