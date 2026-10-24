import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


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
    
    # Analisis visual del historial cerrado del estudiante.
    st.markdown("### Analisis visual del rendimiento")
    df_analisis = df_estudiante.copy()
    if 'TIPO_REGISTRO' in df_analisis.columns:
        df_analisis = df_analisis[
            df_analisis['TIPO_REGISTRO'] == 'CON_BOLETIN'
        ].copy()
    if 'CALIDAD_CIERRE' in df_analisis.columns:
        df_analisis = df_analisis[
            ~df_analisis['CALIDAD_CIERRE'].astype(str).str.upper().str.contains(
                'PERIODO_EN_CURSO_NO_FINAL',
                na=False,
            )
        ].copy()

    columnas_graficas = {'PERIODO', 'ASIGNATURA', 'DEFINITIVA_ALMACENADA'}
    if not columnas_graficas.issubset(df_analisis.columns):
        st.warning("No hay columnas suficientes para generar las graficas del estudiante.")
    else:
        df_analisis['DEFINITIVA_ALMACENADA'] = pd.to_numeric(
            df_analisis['DEFINITIVA_ALMACENADA'],
            errors='coerce',
        )
        df_analisis['PERIODO'] = df_analisis['PERIODO'].astype(str).str.strip()
        df_analisis['ASIGNATURA'] = df_analisis['ASIGNATURA'].astype(str).str.strip()
        df_analisis = df_analisis.dropna(
            subset=['PERIODO', 'ASIGNATURA', 'DEFINITIVA_ALMACENADA']
        ).copy()
        df_analisis = df_analisis[
            ~df_analisis['PERIODO'].isin(['', 'nan'])
            & ~df_analisis['ASIGNATURA'].isin(['', 'nan'])
        ].copy()

        def clave_periodo(periodo):
            try:
                anio, semestre = str(periodo).split('-', 1)
                return int(anio), int(semestre)
            except (TypeError, ValueError):
                return 9999, 9999

        periodos_estudiante = sorted(
            df_analisis['PERIODO'].unique().tolist(),
            key=clave_periodo,
        )

        if not periodos_estudiante:
            st.info("No hay notas historicas validas para graficar.")
        else:
            if len(periodos_estudiante) == 1:
                periodo_inicio = periodos_estudiante[0]
                periodo_fin = periodo_inicio
                st.info(f"Periodo disponible: {periodo_inicio}")
            else:
                periodo_inicio, periodo_fin = st.select_slider(
                    "Rango de periodos del estudiante",
                    options=periodos_estudiante,
                    value=(periodos_estudiante[0], periodos_estudiante[-1]),
                    key="perfil_rango_periodos",
                )
            inicio = periodos_estudiante.index(periodo_inicio)
            fin = periodos_estudiante.index(periodo_fin)
            periodos_seleccionados = periodos_estudiante[inicio:fin + 1]

            materias_disponibles = sorted(df_analisis['ASIGNATURA'].unique().tolist())
            materias_seleccionadas = st.sidebar.multiselect(
                "Materias del perfil para mostrar",
                options=materias_disponibles,
                default=materias_disponibles,
                key="perfil_materias",
            )

            df_graficas = df_analisis[
                df_analisis['PERIODO'].isin(periodos_seleccionados)
                & df_analisis['ASIGNATURA'].isin(materias_seleccionadas)
            ].copy()

            if df_graficas.empty:
                st.info("No hay datos para los filtros seleccionados.")
            else:
                promedios_materia = (
                    df_graficas.groupby('ASIGNATURA', as_index=False)
                    .agg(
                        Promedio=('DEFINITIVA_ALMACENADA', 'mean'),
                        Intentos=('DEFINITIVA_ALMACENADA', 'size'),
                    )
                    .sort_values('Promedio', ascending=False)
                )
                periodos_por_materia = (
                    df_graficas.groupby('ASIGNATURA')['PERIODO']
                    .agg(lambda valores: ', '.join(dict.fromkeys(
                        sorted(valores, key=clave_periodo)
                    )))
                    .rename('Periodos')
                )
                promedios_materia = promedios_materia.merge(
                    periodos_por_materia,
                    left_on='ASIGNATURA',
                    right_index=True,
                )
                promedios_materia['Promedio'] = promedios_materia['Promedio'].round(2)
                figura_promedios = px.line(
                    promedios_materia,
                    x='ASIGNATURA',
                    y='Promedio',
                    text='Promedio',
                    markers=True,
                    title='Promedio de notas por materia',
                    labels={
                        'ASIGNATURA': 'Materia',
                        'Promedio': 'Promedio de nota',
                    },
                )
                figura_promedios.update_traces(
                    textposition='top center',
                    customdata=promedios_materia[['Intentos', 'Periodos']],
                    hovertemplate=(
                        '<b>%{x}</b><br>'
                        'Promedio: %{y:.2f}<br>'
                        'Intentos: %{customdata[0]}<br>'
                        'Periodos: %{customdata[1]}<extra></extra>'
                    ),
                )
                figura_promedios.update_layout(
                    yaxis=dict(range=[0, 5], title='Promedio de nota'),
                    xaxis=dict(type='category', title='Materia', tickangle=-35),
                    height=620,
                )
                st.plotly_chart(
                    figura_promedios,
                    width='stretch',
                    key="perfil_promedios_materia",
                )

                df_intentos = df_graficas.sort_values(
                    ['ASIGNATURA', 'PERIODO'],
                    key=lambda columna: columna.map(clave_periodo)
                    if columna.name == 'PERIODO' else columna,
                ).copy()
                repeticiones = df_intentos['ASIGNATURA'].value_counts()
                materias_repetidas = repeticiones[repeticiones > 1].index.tolist()
                df_intentos = df_intentos[
                    df_intentos['ASIGNATURA'].isin(materias_repetidas)
                ].copy()

                if df_intentos.empty:
                    st.info(
                        "El estudiante no tiene materias cursadas mas de una vez "
                        "en el rango seleccionado."
                    )
                else:
                    orden_materias = (
                        df_intentos.groupby('ASIGNATURA')['PERIODO']
                        .min()
                        .sort_values(key=lambda valores: valores.map(clave_periodo))
                        .index.tolist()
                    )
                    df_intentos['Intento'] = (
                        df_intentos.groupby('ASIGNATURA').cumcount() + 1
                    )
                    df_intentos['Valor_Bloque'] = 1
                    df_intentos['Rango_Nota'] = pd.cut(
                        df_intentos['DEFINITIVA_ALMACENADA'],
                        bins=[-np.inf, 3.0, 4.0, np.inf],
                        labels=['< 3.0', '3.0 - 3.9', '>= 4.0'],
                        right=False,
                    )
                    figura_intentos = px.bar(
                        df_intentos,
                        x='Valor_Bloque',
                        y='ASIGNATURA',
                        color='Rango_Nota',
                        text='DEFINITIVA_ALMACENADA',
                        custom_data=['PERIODO', 'Intento'],
                        category_orders={
                            'ASIGNATURA': orden_materias,
                            'Rango_Nota': ['< 3.0', '3.0 - 3.9', '>= 4.0'],
                        },
                        title='Historial de intentos por materia',
                        labels={
                            'ASIGNATURA': 'Materia',
                            'Valor_Bloque': '',
                            'Rango_Nota': 'Rango de nota',
                        },
                        color_discrete_map={
                            '< 3.0': '#ef4444',
                            '3.0 - 3.9': '#eab308',
                            '>= 4.0': '#22c55e',
                        },
                    )
                    figura_intentos.update_traces(
                        texttemplate='%{text:.2f}',
                        textposition='inside',
                        insidetextanchor='middle',
                        hovertemplate=(
                            '<b>%{y}</b><br>'
                            'Nota definitiva: %{text:.2f}<br>'
                            'Periodo: %{customdata[0]}<br>'
                            'Intento: %{customdata[1]}<extra></extra>'
                        ),
                    )
                    figura_intentos.update_layout(
                        barmode='stack',
                        xaxis=dict(
                            showticklabels=False,
                            title='',
                            showgrid=False,
                            zeroline=False,
                        ),
                        yaxis_title='Materia',
                        legend_title='Rango de nota',
                        height=max(360, 90 * len(orden_materias)),
                    )
                    st.plotly_chart(
                        figura_intentos,
                        width='stretch',
                        key="perfil_intentos_materia",
                    )

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
            width="stretch",
            hide_index=True
        )
    else:
        st.warning("No se pudo mostrar el historial completo.")
