import numpy as np
import pandas as pd


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
    tasa_aprobacion = 0.0
    tasa_reprobacion = 0.0
    
    if 'ESTADO_MATERIA' in df_trabajo.columns and 'DEFINITIVA_ALMACENADA' in df_trabajo.columns:
        df_estado = df_trabajo.copy()
        # Considerar solo registros con estado definido
        df_estado = df_estado[df_estado['ESTADO_MATERIA'].notna()]
        
        if not df_estado.empty:
            total = len(df_estado)
            if total > 0:
                # Contar aprobados y reprobados
                aprobados = df_estado[df_estado['ESTADO_MATERIA'].str.upper().str.contains('APROBO', na=False)]
                reprobados = df_estado[df_estado['ESTADO_MATERIA'].str.upper().str.contains('PERDIO', na=False)]
                
                tasa_aprobacion = (len(aprobados) / total) * 100.0
                tasa_reprobacion = (len(reprobados) / total) * 100.0
        else:
            # Fallback: calcular por nota
            notas = df_trabajo['DEFINITIVA_ALMACENADA'].dropna()
            if not notas.empty:
                total = len(notas)
                aprobados = notas[notas >= 3.0]
                reprobados = notas[notas < 3.0]
                tasa_aprobacion = (len(aprobados) / total) * 100.0
                tasa_reprobacion = (len(reprobados) / total) * 100.0
    elif 'DEFINITIVA_ALMACENADA' in df_trabajo.columns:
        # Calcular por nota si no hay ESTADO_MATERIA
        notas = df_trabajo['DEFINITIVA_ALMACENADA'].dropna()
        if not notas.empty:
            total = len(notas)
            aprobados = notas[notas >= 3.0]
            reprobados = notas[notas < 3.0]
            tasa_aprobacion = (len(aprobados) / total) * 100.0
            tasa_reprobacion = (len(reprobados) / total) * 100.0
    
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
        num_inscritos = len(grupo)
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
            grupo_estado = grupo[grupo['ESTADO_MATERIA'].notna()]
            if not grupo_estado.empty:
                total = len(grupo_estado)
                if total > 0:
                    reprobados = grupo_estado[grupo_estado['ESTADO_MATERIA'].str.upper().str.contains('PERDIO', na=False)]
                    porcentaje_reprobacion = (len(reprobados) / total) * 100.0
            else:
                # Fallback por nota
                if 'DEFINITIVA_ALMACENADA' in grupo.columns:
                    notas = grupo['DEFINITIVA_ALMACENADA'].dropna()
                    if not notas.empty:
                        total = len(notas)
                        reprobados = notas[notas < 3.0]
                        porcentaje_reprobacion = (len(reprobados) / total) * 100.0
        elif 'DEFINITIVA_ALMACENADA' in grupo.columns:
            notas = grupo['DEFINITIVA_ALMACENADA'].dropna()
            if not notas.empty:
                total = len(notas)
                reprobados = notas[notas < 3.0]
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
