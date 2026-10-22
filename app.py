import streamlit as st
import pandas as pd
import os
import tempfile
import shutil
from src.etl.cleaner import cargar_datos_limpios
from src.services.metrics import (
    calcular_kpis_globales,
    calcular_rendimiento_materias,
    detectar_alertas_tempranas
)
from src.components.charts import (
    graficar_evolucion_historica,
    graficar_ranking_causas,
    graficar_mapa_calor,
    graficar_distribucion_notas,
    graficar_curva_progreso,
    graficar_matriz_riesgo,
    graficar_radar_alertas,
    graficar_trayectoria_individual,
    graficar_tendencia_historica,
    graficar_top_mortalidad
)
from src.components.student_profile import mostrar_ficha_estudiante
from src.services.ai_copilot import generar_analisis_ia, explicar_grafico_ia


st.set_page_config(
    page_title="Analitica Academica ITP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos del archivo Excel con caché para evitar recargas."""
    return cargar_datos_limpios()


def main():
    # Sistema de autenticación
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("Acceso Restringido - Analitica Academica ITP")
        st.markdown("**Información estrictamente confidencial - Solo personal autorizado**")
        
        col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
        with col_login2:
            st.markdown("---")
            password = st.text_input("Contraseña", type="password", placeholder="Ingrese la contraseña")
            if st.button("Ingresar", width="stretch"):
                if password == "adminITP2026":
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta. Acceso denegado.")
            st.markdown("---")
        return
    
    st.title("Analitica Academica ITP")
    st.markdown("Sistema de analisis del rendimiento academico para la toma de decisiones")
    
    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar Sesion"):
        st.session_state.autenticado = False
        st.rerun()
    
    # API Key para IA
    st.sidebar.markdown("---")
    st.sidebar.subheader("Inteligencia Artificial")
    api_key_google = st.sidebar.text_input(
        "API Key de Google Gemini",
        type="password",
        placeholder="Ingrese su API Key",
        help="Opcional - Solo si desea usar el análisis con IA"
    )
    
    # Cargar datos
    with st.spinner("Cargando y limpiando datos..."):
        df = cargar_datos()
    
    if df.empty:
        st.error("No se encontraron datos para mostrar.")
        return
    
    # Pestañas de navegación
    tab1, tab2, tab3 = st.tabs(["Vision Global", "Analisis por Estudiante", "Gestion de Datos (Administrador)"])
    
    with tab1:
        # Barra lateral con filtros globales
        st.sidebar.header("Filtros Globales")
        
        # Filtro de Periodo Académico
        periodos_disponibles = []
        if 'PERIODO' in df.columns:
            periodos_disponibles = sorted(df['PERIODO'].dropna().unique().tolist())
        
        # Identificar periodos históricos y periodo en curso
        opciones_periodo = []
        periodo_en_curso_seleccionado = False
        
        # Verificar si hay periodo en curso
        if 'CALIDAD_CIERRE' in df.columns:
            tiene_periodo_curso = df['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL').any()
            if tiene_periodo_curso:
                opciones_periodo.append("Periodo en Curso (2026-2)")
        
        # Agregar periodos históricos
        if periodos_disponibles:
            for p in periodos_disponibles:
                # Verificar si es periodo en curso
                es_curso = False
                if 'CALIDAD_CIERRE' in df.columns:
                    df_check = df[df['PERIODO'] == p]
                    if not df_check.empty:
                        if df_check['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL').any():
                            es_curso = True
                if not es_curso and p not in opciones_periodo:
                    opciones_periodo.append(f"Histórico - {p}")
        
        if not opciones_periodo:
            # Fallback a todos los periodos
            opciones_periodo = ["Todos los periodos"] + [f"Histórico - {p}" for p in periodos_disponibles]
        
        periodo_seleccionado = st.sidebar.selectbox(
            "Periodo Académico",
            options=opciones_periodo,
            index=0
        )
        
        if "Periodo en Curso" in periodo_seleccionado:
            periodo_en_curso_seleccionado = True
        
        # Filtro de Programa
        programas_disponibles = ["Todos"]
        if 'PROGRAMA' in df.columns:
            programas_unicos = sorted(df['PROGRAMA'].dropna().unique().tolist())
            programas_disponibles.extend(programas_unicos)
        
        programa_seleccionado = st.sidebar.selectbox(
            "Programa",
            options=programas_disponibles,
            index=0
        )
        
        # Filtro de Sede
        sedes_disponibles = ["Todas"]
        if 'SEDE' in df.columns:
            sedes_unicas = sorted(df['SEDE'].dropna().unique().tolist())
            sedes_disponibles.extend(sedes_unicas)
        
        sede_seleccionada = st.sidebar.selectbox(
            "Sede",
            options=sedes_disponibles,
            index=0
        )
        
        # Filtro de Semestre Académico (SEMESTRE_ASIGNATURA)
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtros Avanzados")
        
        semestres_disponibles = ["Todos"]
        if 'SEMESTRE_ASIGNATURA' in df.columns:
            # Obtener semestres únicos ordenados de menor a mayor
            semestres_unicos = df['SEMESTRE_ASIGNATURA'].dropna().unique().tolist()
            try:
                semestres_unicos_ordenados = sorted(semestres_unicos, key=lambda x: int(str(x).strip()))
            except:
                semestres_unicos_ordenados = sorted([str(x) for x in semestres_unicos])
            semestres_disponibles.extend(semestres_unicos_ordenados)
        
        semestre_seleccionado = st.sidebar.selectbox(
            "Semestre Académico",
            options=semestres_disponibles,
            index=0
        )
        
        # Filtro de Asignatura (dependiente del semestre)
        asignaturas_disponibles = ["Todas"]
        if 'ASIGNATURA' in df.columns:
            df_temp_asig = df.copy()
            # Aplicar filtro de semestre temporalmente para filtrar asignaturas
            if semestre_seleccionado != "Todos" and 'SEMESTRE_ASIGNATURA' in df_temp_asig.columns:
                try:
                    df_temp_asig_sem = df_temp_asig[df_temp_asig['SEMESTRE_ASIGNATURA'].astype(str).str.strip() == str(semestre_seleccionado).strip()]
                except:
                    df_temp_asig_sem = df_temp_asig
            else:
                df_temp_asig_sem = df_temp_asig
            
            asignaturas_unicas = sorted(df_temp_asig_sem['ASIGNATURA'].dropna().unique().tolist())
            asignaturas_disponibles.extend(asignaturas_unicas)
        
        asignatura_seleccionada = st.sidebar.selectbox(
            "Asignatura",
            options=asignaturas_disponibles,
            index=0
        )
    
    # Aplicar filtros al DataFrame
    df_filtrado = df.copy()
    
    # Filtrar por periodo
    if periodo_en_curso_seleccionado:
        if 'CALIDAD_CIERRE' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
            ].copy()
    elif "Histórico" in periodo_seleccionado and "Todos" not in periodo_seleccionado:
        periodo_filtrar = periodo_seleccionado.replace("Histórico - ", "").strip()
        if 'PERIODO' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['PERIODO'] == periodo_filtrar].copy()
    
    # Filtrar por programa
    if programa_seleccionado != "Todos" and 'PROGRAMA' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['PROGRAMA'] == programa_seleccionado].copy()
    
    # Filtrar por sede
    if sede_seleccionada != "Todas" and 'SEDE' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['SEDE'] == sede_seleccionada].copy()
    
    # Filtrar por semestre
    if semestre_seleccionado != "Todos" and 'SEMESTRE_ASIGNATURA' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['SEMESTRE_ASIGNATURA'].astype(str).str.strip() == str(semestre_seleccionado).strip()].copy()
    
    # Filtrar por asignatura
    if asignatura_seleccionada != "Todas" and 'ASIGNATURA' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['ASIGNATURA'] == asignatura_seleccionada].copy()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Registros filtrados: {len(df_filtrado):,}")
    
    # Fila superior con 4 tarjetas de metricas
    st.subheader("Indicadores Globales")
    
    kpis = calcular_kpis_globales(df_filtrado)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Estudiantes Unicos",
            value=f"{kpis.get('total_estudiantes_unicos', 0):,}"
        )
        
        with col2:
            st.metric(
                label="Total Matriculas",
                value=f"{kpis.get('total_matriculas', 0):,}"
            )
        
        with col3:
            nota_prom = kpis.get('nota_promedio_global', 0)
            if pd.isna(nota_prom):
                st.metric(label="Nota Promedio Global", value="N/A")
            else:
                st.metric(label="Nota Promedio Global", value=f"{nota_prom:.2f}")
        
        with col4:
            tasa_aprob = kpis.get('tasa_aprobacion', 0)
            tasa_rep = kpis.get('tasa_reprobacion', 0)
            st.metric(
                label="Aprobacion / Reprobacion",
                value=f"{tasa_aprob:.1f}% / {tasa_rep:.1f}%"
            )
    
        st.markdown("---")
        
        # Analisis ejecutivo integral con IA
        st.subheader("Análisis ejecutivo integral con IA")
        st.caption("Interpreta las tablas y métricas agregadas del periodo y filtros seleccionados.")
        if st.button("Generar análisis ejecutivo integral", width="stretch", key="btn_ia"):
            if not api_key_google or api_key_google.strip() == "":
                st.warning("Por favor, ingrese su API Key de Google Gemini en la barra lateral.")
            else:
                with st.spinner("Generando analisis con IA..."):
                    resultado_ia = generar_analisis_ia(df_filtrado, api_key_google)
                if "Error" in resultado_ia or "Por favor" in resultado_ia:
                    st.error(resultado_ia)
                else:
                    st.success("Analisis generado exitosamente")
                    st.info(resultado_ia)
        
        st.markdown("---")
        
        st.subheader("Visualizaciones analíticas")

        graficos = {
            "Evolución histórica": (
                "Barras apiladas + promedio/mediana",
                graficar_evolucion_historica,
                "evol_historica",
            ),
            "Ranking de causas": (
                "Top 15 por causas de reprobación",
                graficar_ranking_causas,
                "ranking_causas",
            ),
            "Mapa de calor": (
                "Mapa de calor curricular",
                graficar_mapa_calor,
                "mapa_calor",
            ),
            "Distribución de notas": (
                "Distribución por grupo/docente",
                graficar_distribucion_notas,
                "distribucion_notas",
            ),
            "Curva de progreso": (
                "Progreso por cortes",
                graficar_curva_progreso,
                "curva_progreso",
            ),
            "Matriz de riesgo": (
                "Riesgo vs volumen",
                graficar_matriz_riesgo,
                "matriz_riesgo",
            ),
            "Radar de alertas": (
                "Alertas del periodo en curso",
                graficar_radar_alertas,
                "radar_alertas",
            ),
            "Tendencia histórica": (
                "Promedio histórico",
                graficar_tendencia_historica,
                "tendencia_hist",
            ),
        }

        with st.container(horizontal_alignment="center"):
            grafico_seleccionado = st.pills(
                "Elige el gráfico que quieres visualizar",
                options=list(graficos),
                default="Evolución histórica",
                key="grafico_seleccionado",
                wrap=True,
            )
            grafico_seleccionado = grafico_seleccionado or "Evolución histórica"
            subtitulo, construir_grafico, clave_grafico = graficos[grafico_seleccionado]
            st.markdown(f"### {subtitulo}")
            figura = construir_grafico(df_filtrado)
            figura.update_layout(height=700, autosize=True, margin=dict(l=70, r=70, t=90, b=70))
            st.plotly_chart(figura, width="stretch", key=clave_grafico)

            if st.button(
                "Usar IA para explicar este gráfico",
                width="stretch",
                key=f"btn_explicar_{clave_grafico}",
            ):
                if not api_key_google or not api_key_google.strip():
                    st.warning("Por favor, ingrese su API Key de Google Gemini en la barra lateral.")
                else:
                    with st.spinner("Analizando el gráfico seleccionado..."):
                        explicacion = explicar_grafico_ia(
                            df_filtrado,
                            api_key_google,
                            grafico_seleccionado,
                            subtitulo,
                        )
                    if "Error" in explicacion or "Por favor" in explicacion:
                        st.error(explicacion)
                    else:
                        st.success("Explicación generada exitosamente")
                        st.info(explicacion)
        
        st.markdown("---")
    
    # Panel principal con rendimiento por materias
        st.subheader("Rendimiento por Asignatura")
    
    rendimiento_materias = calcular_rendimiento_materias(df_filtrado)
    
    if not rendimiento_materias.empty:
        # Ordenar por tasa de reprobación
        rendimiento_materias = rendimiento_materias.sort_values('porcentaje_reprobacion', ascending=False)
        
        # Mostrar dataframe
        st.dataframe(
            rendimiento_materias,
            width="stretch",
            hide_index=True,
            column_config={
                "ASIGNATURA": st.column_config.TextColumn("Asignatura", width="large"),
                "num_inscritos": st.column_config.NumberColumn("Inscritos", format="%d"),
                "nota_promedio": st.column_config.NumberColumn("Nota Promedio", format="%.2f"),
                "porcentaje_reprobacion": st.column_config.NumberColumn("% Reprobación", format="%.2f%%")
            }
        )
    else:
        st.info("No hay datos de rendimiento por materia para mostrar con los filtros seleccionados.")
    
        # Sección condicional para periodo en curso
        if periodo_en_curso_seleccionado:
            st.markdown("---")
            st.subheader("Estudiantes en Riesgo - Periodo en Curso (2026-2)")
            st.caption("Basado unicamente en PRIMER_PARCIAL con calificacion menor a 3.0 en 2 o mas asignaturas")
            
            alertas = detectar_alertas_tempranas(df_filtrado)
            
            if not alertas.empty:
                st.dataframe(
                    alertas,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "ID_ESTUDIANTE": st.column_config.TextColumn("ID Estudiante"),
                        "NOMBRE_COMPLETO": st.column_config.TextColumn("Nombre Completo", width="large"),
                        "num_asignaturas_bajo_rendimiento": st.column_config.NumberColumn("Asignaturas en Riesgo", format="%d"),
                        "asignaturas_afectadas": st.column_config.TextColumn("Asignaturas Afectadas", width="large")
                    }
                )
                st.warning(f"Se detectaron {len(alertas)} estudiante(s) en alerta temprana.")
            else:
                st.success("No se detectaron estudiantes en alerta temprana con los criterios actuales.")
    
    with tab2:
        mostrar_ficha_estudiante(df)
    
    with tab3:
        st.subheader("Gestion de Datos - Administrador")
        st.caption("Carga de archivos Excel semestrales para actualizar el histórico")
        
        st.markdown("---")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Seleccionar archivo Excel (.xlsx)",
            type=['xlsx'],
            help="Suba el archivo consolidado con las hojas de registros académicos"
        )
        
        if uploaded_file is not None:
            st.success(f"Archivo cargado: {uploaded_file.name}")
            
            # Guardar archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                with st.spinner("Procesando y validando datos..."):
                    # Ejecutar cargar_datos_limpios sobre archivo temporal
                    df_nuevo = cargar_datos_limpios(ruta_excel=tmp_path)
                
                st.markdown("### Resumen del Archivo Cargado")
                
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("Total de Filas Nuevas", f"{len(df_nuevo):,}")
                
                with col_r2:
                    if 'PERIODO' in df_nuevo.columns:
                        periodos_detectados = df_nuevo['PERIODO'].dropna().unique()
                        st.metric("Periodos Detectados", f"{len(periodos_detectados)}")
                        st.caption(", ".join(sorted([str(p) for p in periodos_detectados])))
                    else:
                        st.metric("Periodos Detectados", "N/A")
                
                with col_r3:
                    if 'ID_ESTUDIANTE' in df_nuevo.columns:
                        num_estudiantes = df_nuevo['ID_ESTUDIANTE'].nunique()
                        st.metric("Cantidad de Estudiantes", f"{num_estudiantes:,}")
                    else:
                        st.metric("Cantidad de Estudiantes", "N/A")
                
                st.markdown("---")
                
                # Botón para guardar y consolidar
                if st.button("Guardar y Consolidar", width="stretch", type="primary", key="guardar_consolidar"):
                    try:
                        # Ruta de destino
                        ruta_destino = os.path.join("data", "Consolidado_Calificaciones_2023_2026 v2 .xlsx")
                        
                        # Guardar archivo (sobrescribir)
                        shutil.copy(tmp_path, ruta_destino)
                        
                        # Limpiar cache
                        st.cache_data.clear()
                        
                        st.success("Archivo guardado exitosamente. El dashboard se actualizara automaticamente.")
                        st.info("Recarga la pagina para ver los datos actualizados.")
                        
                    except Exception as e:
                        st.error(f"Error al guardar el archivo: {e}")
                
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.caption("Verifique que el archivo tenga el formato correcto con las hojas de registros académicos.")
            
            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        else:
            st.info("Seleccione un archivo .xlsx para comenzar la carga")


if __name__ == "__main__":
    main()
