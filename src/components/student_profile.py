import streamlit as st
import pandas as pd
import numpy as np


def mostrar_ficha_estudiante(df):
    """
    Muestra la ficha individual del estudiante con buscador por documento o nombre.
    Cumple con reglas de confidencialidad al mostrar solo el estudiante consultado.
    
    Args:
        df: DataFrame con todos los datos cargados
    """
    st.subheader("Ficha Academica Individual")
    st.caption("Buscar estudiante por numero de documento o nombre completo para auditoria confidencial")
    
    if df is None or df.empty:
        st.warning("No hay datos disponibles para consultar.")
        return
    
    # Buscador
    termino_busqueda = st.text_input(
        "Buscar por Numero de Documento o Nombre Completo",
        placeholder="Ingrese documento o nombre del estudiante...",
        help="La busqueda es flexible y puede encontrar coincidencias parciales"
    )
    
    if not termino_busqueda or termino_busqueda.strip() == "":
        st.info("Ingrese un termino de busqueda para consultar la ficha del estudiante.")
        return
    
    termino_busqueda_lower = termino_busqueda.strip().lower()
    
    # Buscar estudiante
    df_busqueda = df.copy()
    estudiantes_encontrados = pd.DataFrame()
    
    # Buscar por documento
    if 'NUMERO_DOCUMENTO' in df_busqueda.columns:
        mask_doc = df_busqueda['NUMERO_DOCUMENTO'].astype(str).str.lower().str.contains(termino_busqueda_lower, na=False)
        estudiantes_encontrados = df_busqueda[mask_doc].copy()
    
    # Si no se encuentra por documento, buscar por nombre
    if estudiantes_encontrados.empty and 'NOMBRE_COMPLETO' in df_busqueda.columns:
        mask_nombre = df_busqueda['NOMBRE_COMPLETO'].astype(str).str.lower().str.contains(termino_busqueda_lower, na=False)
        estudiantes_encontrados = df_busqueda[mask_nombre].copy()
    
    if estudiantes_encontrados.empty:
        st.warning("No se encontraron estudiantes con ese criterio de busqueda.")
        return
    
    # Obtener informacion del estudiante
    if 'ID_ESTUDIANTE' in estudiantes_encontrados.columns:
        id_estudiante = estudiantes_encontrados['ID_ESTUDIANTE'].iloc[0]
        df_estudiante = df_busqueda[df_busqueda['ID_ESTUDIANTE'] == id_estudiante].copy()
    else:
        df_estudiante = estudiantes_encontrados.copy()
    
    # Mostrar informacion basica
    st.markdown("### Informacion General")
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        if 'NUMERO_DOCUMENTO' in df_estudiante.columns:
            doc = df_estudiante['NUMERO_DOCUMENTO'].dropna().iloc[0] if not df_estudiante['NUMERO_DOCUMENTO'].dropna().empty else "N/A"
            st.metric("Documento", str(doc))
    
    with col_info2:
        if 'NOMBRE_COMPLETO' in df_estudiante.columns:
            nombre = df_estudiante['NOMBRE_COMPLETO'].dropna().iloc[0] if not df_estudiante['NOMBRE_COMPLETO'].dropna().empty else "N/A"
            st.text_input("Nombre", value=str(nombre), disabled=True)
    
    with col_info3:
        if 'PROGRAMA' in df_estudiante.columns:
            programa = df_estudiante['PROGRAMA'].dropna().iloc[0] if not df_estudiante['PROGRAMA'].dropna().empty else "N/A"
            st.text_input("Programa", value=str(programa), disabled=True)
    
    # Metricas del estudiante
    st.markdown("### Metricas Acumuladas")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    
    # Promedio acumulado historico (usar DEFINITIVA_ALMACENADA para historicos, CON_BOLETIN)
    df_est_historico = df_estudiante.copy()
    if 'TIPO_REGISTRO' in df_est_historico.columns:
        df_est_historico = df_est_historico[df_est_historico['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    # Excluir periodo en curso para promedio acumulado historico
    if 'CALIDAD_CIERRE' in df_est_historico.columns:
        df_est_historico_prom = df_est_historico[
            ~df_est_historico['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    else:
        df_est_historico_prom = df_est_historico.copy()
    
    promedio_acumulado = np.nan
    if not df_est_historico_prom.empty and 'DEFINITIVA_ALMACENADA' in df_est_historico_prom.columns:
        notas_validas = df_est_historico_prom['DEFINITIVA_ALMACENADA'].dropna()
        if not notas_validas.empty:
            promedio_acumulado = float(notas_validas.mean())
    
    with col_m1:
        if pd.isna(promedio_acumulado):
            st.metric("Promedio Acumulado Historico", "N/A")
        else:
            st.metric("Promedio Acumulado Historico", f"{promedio_acumulado:.2f}")
    
    # Materias aprobadas y reprobadas
    aprobadas = 0
    reprobadas = 0
    
    if not df_est_historico_prom.empty:
        if 'ESTADO_MATERIA' in df_est_historico_prom.columns:
            df_est_estado = df_est_historico_prom[df_est_historico_prom['ESTADO_MATERIA'].notna()]
            if not df_est_estado.empty:
                aprobadas = len(df_est_estado[df_est_estado['ESTADO_MATERIA'].astype(str).str.upper().str.contains('APROBO', na=False)])
                reprobadas = len(df_est_estado[df_est_estado['ESTADO_MATERIA'].astype(str).str.upper().str.contains('PERDIO', na=False)])
            else:
                if 'DEFINITIVA_ALMACENADA' in df_est_historico_prom.columns:
                    notas = df_est_historico_prom['DEFINITIVA_ALMACENADA'].dropna()
                    aprobadas = len(notas[notas >= 3.0])
                    reprobadas = len(notas[notas < 3.0])
        elif 'DEFINITIVA_ALMACENADA' in df_est_historico_prom.columns:
            notas = df_est_historico_prom['DEFINITIVA_ALMACENADA'].dropna()
            aprobadas = len(notas[notas >= 3.0])
            reprobadas = len(notas[notas < 3.0])
    
    with col_m2:
        st.metric("Materias Aprobadas", f"{aprobadas}")
    
    with col_m3:
        st.metric("Materias Reprobadas", f"{reprobadas}")
    
    # Historial completo de materias
    st.markdown("### Historial Academico Completo")
    
    columnas_historial = []
    for col in ['PERIODO', 'ANIO', 'SEMESTRE_ASIGNATURA', 'ASIGNATURA', 'CODIGO_ASIGNATURA', 
                'DOCENTE', 'GRUPO', 'PRIMER_PARCIAL', 'SEGUNDO_PARCIAL', 'EXAMEN_FINAL',
                'DEFINITIVA_ALMACENADA', 'ESTADO_MATERIA', 'CALIDAD_CIERRE', 'TIPO_REGISTRO']:
        if col in df_estudiante.columns:
            columnas_historial.append(col)
    
    if columnas_historial:
        df_historial = df_estudiante[columnas_historial].copy()
        # Ordenar por periodo
        if 'ANIO' in df_historial.columns and 'PERIODO' in df_historial.columns:
            try:
                df_historial = df_historial.sort_values(['ANIO', 'PERIODO'])
            except:
                pass
        
        st.dataframe(
            df_historial,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No se pudo mostrar el historial completo.")
