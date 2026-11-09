import numpy as np
import pandas as pd
from src.constants import (
    NOTA_MINIMA_APROBACION,
    NOTA_MINIMA_RIESGO,
    PESO_EXAMEN_FINAL,
    PESO_PRIMER_CORTE,
    PESO_SEGUNDO_CORTE,
)
from src.services.filters import filtrar_periodo, filtrar_semestre, solo_con_boletin
from src.services.periods import clave_periodo_academico


def _clave_periodo_academico(periodo):
    return clave_periodo_academico(periodo)


def _tasas_aprobacion_reprobacion(df):
    """Calcula tasas usando solo estados academicos conocidos."""
    if df is None or df.empty:
        return 0.0, 0.0
    estados = df["ESTADO_MATERIA"].astype(str).str.upper().str.strip()
    aprobados = estados.str.contains("APROBO", na=False)
    reprobados = estados.str.contains("PERDIO", na=False)
    validos = aprobados | reprobados
    if validos.any():
        total = int(validos.sum())
        return (
            float(aprobados[validos].sum() / total * 100),
            float(reprobados[validos].sum() / total * 100),
        )
    if "DEFINITIVA_ALMACENADA" not in df.columns:
        return 0.0, 0.0
    notas = pd.to_numeric(df["DEFINITIVA_ALMACENADA"], errors="coerce").dropna()
    if notas.empty:
        return 0.0, 0.0
    return (
        float((notas >= NOTA_MINIMA_APROBACION).mean() * 100),
        float((notas < NOTA_MINIMA_APROBACION).mean() * 100),
    )


def obtener_periodo_vigente(df: pd.DataFrame):
    """Obtiene el periodo en curso marcado por el ETL o el ultimo disponible."""
    if df is None or df.empty or "PERIODO" not in df.columns:
        return None
    trabajo = df.copy()
    if "CALIDAD_CIERRE" in trabajo.columns:
        vigentes = trabajo[
            trabajo["CALIDAD_CIERRE"].astype(str).str.upper().str.contains(
                "PERIODO_EN_CURSO_NO_FINAL",
                na=False,
            )
        ]
        periodos_vigentes = vigentes["PERIODO"].dropna().astype(str).str.strip()
        if not periodos_vigentes.empty:
            return max(periodos_vigentes, key=_clave_periodo_academico)
    periodos = trabajo["PERIODO"].dropna().astype(str).str.strip()
    if periodos.empty:
        return None
    return max(periodos, key=_clave_periodo_academico)


def obtener_estudiantes_sin_calificaciones(
    df: pd.DataFrame,
    periodo=None,
    semestre_curricular=None,
):
    """Lista estudiantes con ambos cortes en cero en todas sus materias."""
    columnas = {
        "PERIODO",
        "ID_ESTUDIANTE",
        "ASIGNATURA",
        "PRIMER_PARCIAL",
        "SEGUNDO_PARCIAL",
    }
    if df is None or df.empty or not columnas.issubset(df.columns):
        return pd.DataFrame()
    periodo = periodo or obtener_periodo_vigente(df)
    if periodo is None:
        return pd.DataFrame()

    trabajo = filtrar_semestre(
        solo_con_boletin(filtrar_periodo(df, periodo)),
        semestre_curricular,
    )
    if trabajo.empty:
        return pd.DataFrame()
    for columna in ["PRIMER_PARCIAL", "SEGUNDO_PARCIAL"]:
        trabajo[columna] = pd.to_numeric(trabajo[columna], errors="coerce")
    trabajo["ASIGNATURA"] = trabajo["ASIGNATURA"].astype(str).str.strip()
    trabajo = trabajo[~trabajo["ASIGNATURA"].isin(["", "nan"])].copy()
    if trabajo.empty:
        return pd.DataFrame()

    trabajo["_sin_calificaciones"] = (
        trabajo["PRIMER_PARCIAL"].eq(0)
        & trabajo["SEGUNDO_PARCIAL"].eq(0)
    )
    resumen = trabajo.groupby("ID_ESTUDIANTE").agg(
        todas_sin_calificaciones=("_sin_calificaciones", "all"),
        materias=("ASIGNATURA", "nunique"),
        materias_cursadas=(
            "ASIGNATURA",
            lambda valores: ", ".join(sorted(set(valores))),
        ),
    )
    resumen = resumen[resumen["todas_sin_calificaciones"]].reset_index()
    if resumen.empty:
        return pd.DataFrame()

    for columna in ["NOMBRE_COMPLETO"]:
        if columna in trabajo.columns:
            datos = trabajo.groupby("ID_ESTUDIANTE")[columna].first()
            resumen[columna] = resumen["ID_ESTUDIANTE"].map(datos)
        else:
            resumen[columna] = "N/A"
    resumen["PERIODO"] = str(periodo)
    return resumen[
        [
            "ID_ESTUDIANTE",
            "NOMBRE_COMPLETO",
            "materias",
            "materias_cursadas",
            "PERIODO",
        ]
    ].rename(
        columns={
            "materias": "Materias sin calificaciones",
            "materias_cursadas": "Materias del periodo",
        }
    ).sort_values("NOMBRE_COMPLETO").reset_index(drop=True)


def calcular_riesgo_periodo_vigente(df: pd.DataFrame, periodo=None):
    """Calcula la nota necesaria en el examen final para aprobar."""
    columnas = {
        "PERIODO",
        "ASIGNATURA",
        "ID_ESTUDIANTE",
        "PRIMER_PARCIAL",
        "SEGUNDO_PARCIAL",
    }
    if df is None or df.empty or not columnas.issubset(df.columns):
        return pd.DataFrame()
    periodo = periodo or obtener_periodo_vigente(df)
    if periodo is None:
        return pd.DataFrame()

    trabajo = solo_con_boletin(filtrar_periodo(df, periodo))
    if trabajo.empty:
        return pd.DataFrame()

    for columna in ["PRIMER_PARCIAL", "SEGUNDO_PARCIAL"]:
        trabajo[columna] = pd.to_numeric(trabajo[columna], errors="coerce")
    trabajo["ASIGNATURA"] = trabajo["ASIGNATURA"].astype(str).str.strip()
    trabajo = trabajo[~trabajo["ASIGNATURA"].isin(["", "nan"])].copy()
    estudiantes_sin_calificaciones = obtener_estudiantes_sin_calificaciones(
        trabajo,
        periodo,
    )
    if not estudiantes_sin_calificaciones.empty:
        trabajo = trabajo[
            ~trabajo["ID_ESTUDIANTE"].isin(
                estudiantes_sin_calificaciones["ID_ESTUDIANTE"]
            )
        ].copy()
    trabajo = trabajo.dropna(subset=["PRIMER_PARCIAL", "SEGUNDO_PARCIAL"]).copy()
    if trabajo.empty:
        return pd.DataFrame()

    agrupaciones = {
        "Primer corte": ("PRIMER_PARCIAL", "mean"),
        "Segundo corte": ("SEGUNDO_PARCIAL", "mean"),
    }
    identidad = ["ID_ESTUDIANTE", "ASIGNATURA"]
    for columna in ("DOCENTE", "GRUPO"):
        if columna in trabajo.columns:
            identidad.append(columna)
    resultado = trabajo.groupby(identidad, as_index=False).agg(**agrupaciones)
    resultado["Necesita examen final"] = (
        NOTA_MINIMA_APROBACION
        - resultado["Primer corte"] * PESO_PRIMER_CORTE
        - resultado["Segundo corte"] * PESO_SEGUNDO_CORTE
    ) / PESO_EXAMEN_FINAL
    resultado["Necesita examen final"] = resultado["Necesita examen final"].round(2)
    resultado = resultado[resultado["Necesita examen final"] >= NOTA_MINIMA_RIESGO].copy()
    if resultado.empty:
        return pd.DataFrame()

    resultado["Nivel de peligro"] = np.select(
        [
            resultado["Necesita examen final"] > 5.0,
            resultado["Necesita examen final"] >= 4.0,
            resultado["Necesita examen final"] >= NOTA_MINIMA_RIESGO,
        ],
        ["No puede aprobar", "Peligro alto", "Peligro medio"],
        default="",
    )
    for columna in ["NOMBRE_COMPLETO", "NUMERO_DOCUMENTO"]:
        if columna in trabajo.columns:
            datos = trabajo.groupby("ID_ESTUDIANTE")[columna].first()
            resultado[columna] = resultado["ID_ESTUDIANTE"].map(datos)
        else:
            resultado[columna] = "N/A"
    if "SEMESTRE_ASIGNATURA" in trabajo.columns:
        semestres = (
            trabajo.groupby(["ID_ESTUDIANTE", "ASIGNATURA"])[
                "SEMESTRE_ASIGNATURA"
            ]
            .first()
        )
        resultado["SEMESTRE_ASIGNATURA"] = [
            semestres.get((estudiante, asignatura), "Sin semestre")
            for estudiante, asignatura in zip(
                resultado["ID_ESTUDIANTE"],
                resultado["ASIGNATURA"],
            )
        ]
    else:
        resultado["SEMESTRE_ASIGNATURA"] = "Sin semestre"
    cantidades = resultado.groupby("ID_ESTUDIANTE")["ASIGNATURA"].transform("count")
    resultado["Materias en peligro"] = cantidades
    resultado["PERIODO"] = str(periodo)
    return resultado.sort_values(
        ["Necesita examen final", "ASIGNATURA"],
        ascending=[False, True],
    ).reset_index(drop=True)


def calcular_detalle_estudiante_periodo(
    df: pd.DataFrame,
    periodo,
    id_estudiante,
    semestre_curricular=None,
):
    """Calcula la nota necesaria por cada materia cursada por un estudiante."""
    columnas = {
        "PERIODO",
        "ASIGNATURA",
        "ID_ESTUDIANTE",
        "PRIMER_PARCIAL",
        "SEGUNDO_PARCIAL",
    }
    if df is None or df.empty or not columnas.issubset(df.columns):
        return pd.DataFrame()

    trabajo = df[
        (df["PERIODO"].astype(str).str.strip() == str(periodo))
        & (df["ID_ESTUDIANTE"].astype(str) == str(id_estudiante))
    ].copy()
    trabajo = solo_con_boletin(trabajo)
    if (
        semestre_curricular
        and semestre_curricular != "Todos"
        and "SEMESTRE_ASIGNATURA" in trabajo.columns
    ):
        trabajo = trabajo[
            trabajo["SEMESTRE_ASIGNATURA"].astype(str).str.strip()
            == semestre_curricular
        ].copy()
    if trabajo.empty:
        return pd.DataFrame()

    for columna in ["PRIMER_PARCIAL", "SEGUNDO_PARCIAL"]:
        trabajo[columna] = pd.to_numeric(trabajo[columna], errors="coerce")
    trabajo["ASIGNATURA"] = trabajo["ASIGNATURA"].astype(str).str.strip()
    trabajo = trabajo[
        ~trabajo["ASIGNATURA"].isin(["", "nan"])
    ].dropna(subset=["PRIMER_PARCIAL", "SEGUNDO_PARCIAL"])
    if trabajo.empty:
        return pd.DataFrame()

    detalle = trabajo.groupby(
        ["ID_ESTUDIANTE", "ASIGNATURA"],
        as_index=False,
    ).agg(
        **{
            "Primer corte": ("PRIMER_PARCIAL", "mean"),
            "Segundo corte": ("SEGUNDO_PARCIAL", "mean"),
        }
    )
    detalle["Necesita examen final"] = (
        NOTA_MINIMA_APROBACION
        - detalle["Primer corte"] * PESO_PRIMER_CORTE
        - detalle["Segundo corte"] * PESO_SEGUNDO_CORTE
    ) / PESO_EXAMEN_FINAL
    detalle["Necesita examen final"] = detalle[
        "Necesita examen final"
    ].clip(lower=0).round(2)
    detalle["Estado"] = np.where(
        detalle["Necesita examen final"].eq(0),
        "Ya alcanza el promedio mínimo",
        "Debe obtener esta nota",
    )
    return detalle.sort_values("ASIGNATURA").reset_index(drop=True)


def resumir_materias_periodo(
    df: pd.DataFrame,
    riesgo: pd.DataFrame,
    periodo,
    semestre_curricular=None,
):
    """Resume profesor, inscritos y estudiantes en peligro por materia."""
    columnas = {"PERIODO", "ASIGNATURA", "ID_ESTUDIANTE"}
    if df is None or df.empty or not columnas.issubset(df.columns):
        return pd.DataFrame()

    trabajo = df[df["PERIODO"].astype(str).str.strip() == str(periodo)].copy()
    if "TIPO_REGISTRO" in trabajo.columns:
        trabajo = trabajo[trabajo["TIPO_REGISTRO"] == "CON_BOLETIN"].copy()
    if (
        semestre_curricular
        and semestre_curricular != "Todos"
        and "SEMESTRE_ASIGNATURA" in trabajo.columns
    ):
        trabajo = trabajo[
            trabajo["SEMESTRE_ASIGNATURA"].astype(str).str.strip()
            == semestre_curricular
        ].copy()
    trabajo["ASIGNATURA"] = trabajo["ASIGNATURA"].astype(str).str.strip()
    trabajo = trabajo[~trabajo["ASIGNATURA"].isin(["", "nan"])].copy()
    if trabajo.empty:
        return pd.DataFrame()

    resumen = trabajo.groupby("ASIGNATURA", as_index=False).agg(
        **{
            "Estudiantes inscritos": ("ID_ESTUDIANTE", "nunique"),
        }
    )
    if "DOCENTE" in trabajo.columns:
        profesores = trabajo.groupby("ASIGNATURA")["DOCENTE"].agg(
            lambda valores: ", ".join(
                sorted(
                    {
                        str(valor).strip()
                        for valor in valores
                        if pd.notna(valor) and str(valor).strip()
                    }
                )
            )
        )
        resumen["Profesor(es)"] = resumen["ASIGNATURA"].map(profesores)
    else:
        resumen["Profesor(es)"] = "Sin profesor registrado"
    resumen["Profesor(es)"] = resumen["Profesor(es)"].replace(
        "", "Sin profesor registrado"
    )

    riesgo_trabajo = riesgo.copy() if riesgo is not None else pd.DataFrame()
    if not riesgo_trabajo.empty:
        if semestre_curricular and semestre_curricular != "Todos":
            riesgo_trabajo = riesgo_trabajo[
                riesgo_trabajo["SEMESTRE_ASIGNATURA"].astype(str).str.strip()
                == semestre_curricular
            ]
        peligros = riesgo_trabajo.groupby("ASIGNATURA")[
            "ID_ESTUDIANTE"
        ].nunique()
        resumen["Estudiantes en peligro"] = (
            resumen["ASIGNATURA"].map(peligros).fillna(0).astype(int)
        )
    else:
        resumen["Estudiantes en peligro"] = 0

    return resumen[
        [
            "ASIGNATURA",
            "Profesor(es)",
            "Estudiantes inscritos",
            "Estudiantes en peligro",
        ]
    ].sort_values("ASIGNATURA").reset_index(drop=True)


def calcular_kpis_globales(df: pd.DataFrame):
    """
    Calcula los KPIs globales del aplicativo de analitica academica.
    
    Filtra los registros CON_BOLETIN y calcula:
    - Total de estudiantes unicos
    - Total de matriculas
    - Nota promedio global (usando DEFINITIVA_ALMACENADA para periodos historicos)
    - Tasa porcentual de aprobacion vs. reprobacion
    
    Args:
        df: DataFrame limpio retornado por cargar_datos_limpios()
        
    Returns:
        Dict con los KPIs calculados
    """
    if df is None or df.empty:
        return {
            'total_estudiantes_unicos': 0,
            'total_matriculas': 0,
            'nota_promedio_global': np.nan,
            'tasa_aprobacion': 0.0,
            'tasa_reprobacion': 0.0
        }
    
    # Trabajar con una copia
    df_trabajo = df.copy()
    
    # Filtrar solo registros CON_BOLETIN
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    # Eliminar filas con datos criticos nulos
    if df_trabajo.empty:
        return {
            'total_estudiantes_unicos': 0,
            'total_matriculas': 0,
            'nota_promedio_global': np.nan,
            'tasa_aprobacion': 0.0,
            'tasa_reprobacion': 0.0
        }
    
    # Calcular totales
    total_estudiantes_unicos = df_trabajo['ID_ESTUDIANTE'].nunique() if 'ID_ESTUDIANTE' in df_trabajo.columns else 0
    total_matriculas = df_trabajo['ID_MATRICULA'].nunique() if 'ID_MATRICULA' in df_trabajo.columns else len(df_trabajo)
    
    # Calcular nota promedio global
    nota_promedio_global = np.nan
    if 'DEFINITIVA_ALMACENADA' in df_trabajo.columns:
        # Para periodos historicos usar DEFINITIVA_ALMACENADA
        notas_validas = df_trabajo['DEFINITIVA_ALMACENADA'].dropna()
        if not notas_validas.empty:
            nota_promedio_global = float(notas_validas.mean())
    
    # Calcular tasa de aprobacion vs. reprobacion
    if "ESTADO_MATERIA" in df_trabajo.columns:
        tasa_aprobacion, tasa_reprobacion = _tasas_aprobacion_reprobacion(
            df_trabajo
        )
    elif "DEFINITIVA_ALMACENADA" in df_trabajo.columns:
        notas = pd.to_numeric(
            df_trabajo["DEFINITIVA_ALMACENADA"], errors="coerce"
        ).dropna()
        tasa_aprobacion = float(
            (notas >= NOTA_MINIMA_APROBACION).mean() * 100
        ) if not notas.empty else 0.0
        tasa_reprobacion = float(
            (notas < NOTA_MINIMA_APROBACION).mean() * 100
        ) if not notas.empty else 0.0
    
    return {
        'total_estudiantes_unicos': int(total_estudiantes_unicos),
        'total_matriculas': int(total_matriculas),
        'nota_promedio_global': round(float(nota_promedio_global), 2) if not np.isnan(nota_promedio_global) else np.nan,
        'tasa_aprobacion': round(float(tasa_aprobacion), 2),
        'tasa_reprobacion': round(float(tasa_reprobacion), 2)
    }


def calcular_rendimiento_materias(df: pd.DataFrame):
    """
    Calcula el rendimiento por materia.
    
    Agrupa los datos por ASIGNATURA y calcula:
    - Numero de inscritos
    - Nota promedio
    - Porcentaje de reprobacion
    
    Args:
        df: DataFrame limpio retornado por cargar_datos_limpios()
        
    Returns:
        DataFrame con el rendimiento por materia
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['ASIGNATURA', 'num_inscritos', 'nota_promedio', 'porcentaje_reprobacion'])
    
    df_trabajo = df.copy()
    
    # Filtrar solo registros CON_BOLETIN por defecto para evitar sesgo
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'ASIGNATURA' not in df_trabajo.columns:
        return pd.DataFrame(columns=['ASIGNATURA', 'num_inscritos', 'nota_promedio', 'porcentaje_reprobacion'])
    
    resultados = []
    
    for asignatura, grupo in df_trabajo.groupby('ASIGNATURA'):
        num_inscritos = (
            grupo["ID_ESTUDIANTE"].nunique()
            if "ID_ESTUDIANTE" in grupo.columns
            else len(grupo)
        )
        if num_inscritos == 0:
            continue
        
        # Calcular nota promedio
        nota_promedio = np.nan
        if 'DEFINITIVA_ALMACENADA' in grupo.columns:
            notas_validas = grupo['DEFINITIVA_ALMACENADA'].dropna()
            if not notas_validas.empty:
                nota_promedio = float(notas_validas.mean())
        
        # Calcular porcentaje de reprobacion
        porcentaje_reprobacion = 0.0
        if 'ESTADO_MATERIA' in grupo.columns:
            _, porcentaje_reprobacion = _tasas_aprobacion_reprobacion(grupo)
        elif 'DEFINITIVA_ALMACENADA' in grupo.columns:
            notas = grupo['DEFINITIVA_ALMACENADA'].dropna()
            if not notas.empty:
                total = len(notas)
                reprobados = notas[notas < NOTA_MINIMA_APROBACION]
                porcentaje_reprobacion = (len(reprobados) / total) * 100.0
        
        resultados.append({
            'ASIGNATURA': asignatura,
            'num_inscritos': int(num_inscritos),
            'nota_promedio': round(float(nota_promedio), 2) if not np.isnan(nota_promedio) else np.nan,
            'porcentaje_reprobacion': round(float(porcentaje_reprobacion), 2)
        })
    
    df_resultado = pd.DataFrame(resultados)
    # Ordenar por porcentaje de reprobacion descendente
    if not df_resultado.empty:
        df_resultado = df_resultado.sort_values('porcentaje_reprobacion', ascending=False).reset_index(drop=True)
    
    return df_resultado


def detectar_alertas_tempranas(df: pd.DataFrame):
    """
    Detecta alertas tempranas para el periodo en curso.
    
    Filtra exclusivamente el periodo en curso (2026-2), evalua unicamente
    la columna PRIMER_PARCIAL e identifica a los estudiantes (ID_ESTUDIANTE, NOMBRE_COMPLETO)
    que tengan una calificacion menor a 3.0 en 2 o mas asignaturas.
    
    Args:
        df: DataFrame limpio retornado por cargar_datos_limpios()
        
    Returns:
        DataFrame con los estudiantes en alerta temprana
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['ID_ESTUDIANTE', 'NOMBRE_COMPLETO', 'num_asignaturas_bajo_rendimiento', 'asignaturas_afectadas'])
    
    df_trabajo = df.copy()
    
    # Filtrar exclusivamente el periodo en curso (2026-2)
    df_periodo_curso = pd.DataFrame()
    
    if 'CALIDAD_CIERRE' in df_trabajo.columns:
        # Buscar periodo en curso
        df_periodo_curso = df_trabajo[
            df_trabajo['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    
    # Si no se encuentra por CALIDAD_CIERRE, intentar por PERIODO 2026-2
    if df_periodo_curso.empty and 'PERIODO' in df_trabajo.columns and 'ANIO' in df_trabajo.columns:
        df_periodo_curso = df_trabajo[
            (df_trabajo['ANIO'].astype(str).str.contains('2026', na=False)) &
            (df_trabajo['PERIODO'].astype(str).str.contains('2', na=False))
        ].copy()
    
    if df_periodo_curso.empty:
        return pd.DataFrame(columns=['ID_ESTUDIANTE', 'NOMBRE_COMPLETO', 'num_asignaturas_bajo_rendimiento', 'asignaturas_afectadas'])
    
    # Filtrar solo registros CON_BOLETIN si esta disponible
    if 'TIPO_REGISTRO' in df_periodo_curso.columns:
        df_periodo_curso = df_periodo_curso[df_periodo_curso['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_periodo_curso.empty or 'PRIMER_PARCIAL' not in df_periodo_curso.columns:
        return pd.DataFrame(columns=['ID_ESTUDIANTE', 'NOMBRE_COMPLETO', 'num_asignaturas_bajo_rendimiento', 'asignaturas_afectadas'])
    
    alertas = []
    
    # Agrupar por estudiante
    if 'ID_ESTUDIANTE' not in df_periodo_curso.columns:
        return pd.DataFrame(columns=['ID_ESTUDIANTE', 'NOMBRE_COMPLETO', 'num_asignaturas_bajo_rendimiento', 'asignaturas_afectadas'])
    
    for id_estudiante, grupo_est in df_periodo_curso.groupby('ID_ESTUDIANTE'):
        # Buscar notas del primer parcial menores a 3.0
        asignaturas_bajo_rendimiento = []
        
        for idx, row in grupo_est.iterrows():
            nota_p1 = row.get('PRIMER_PARCIAL')
            if pd.notna(nota_p1):
                try:
                    nota_p1_float = float(nota_p1)
                    if nota_p1_float < 3.0:
                        asignatura = row.get('ASIGNATURA', 'DESCONOCIDA')
                        asignaturas_bajo_rendimiento.append(str(asignatura))
                except (ValueError, TypeError):
                    continue
        
        # Identificar si tiene 2 o mas asignaturas con calificacion menor a 3.0
        if len(asignaturas_bajo_rendimiento) >= 2:
            # Obtener nombre completo
            nombre_completo = np.nan
            if 'NOMBRE_COMPLETO' in grupo_est.columns:
                nombres = grupo_est['NOMBRE_COMPLETO'].dropna()
                if not nombres.empty:
                    nombre_completo = nombres.iloc[0]
            
            alertas.append({
                'ID_ESTUDIANTE': id_estudiante,
                'NOMBRE_COMPLETO': nombre_completo,
                'num_asignaturas_bajo_rendimiento': len(asignaturas_bajo_rendimiento),
                'asignaturas_afectadas': ', '.join(asignaturas_bajo_rendimiento)
            })
    
    df_alertas = pd.DataFrame(alertas)
    
    if not df_alertas.empty:
        df_alertas = df_alertas.sort_values('num_asignaturas_bajo_rendimiento', ascending=False).reset_index(drop=True)
    
    return df_alertas
