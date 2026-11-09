import streamlit as st
import pandas as pd
import os
import tempfile
import shutil
from src.etl.cleaner import cargar_datos_limpios
from src.services.metrics import (
    calcular_kpis_globales,
    calcular_rendimiento_materias,
    detectar_alertas_tempranas,
    calcular_riesgo_periodo_vigente,
    resumir_materias_periodo,
    obtener_periodo_vigente,
    obtener_estudiantes_sin_calificaciones,
)
from src.components.tables import colorear_riesgo
from src.constants import NOTA_MINIMA_APROBACION
from src.services.filters import filtrar_asignatura, filtrar_docente, filtrar_semestre
from src.services.periods import (
    ordenar_periodos,
    ordenar_semestres_curriculares,
    periodos_historicos as obtener_periodos_historicos,
)
from src.components.charts import (
    graficar_tendencia_promedios,
    graficar_tendencia_promedio_materia,
    graficar_reprobados_por_corte,
    graficar_tendencia_cantidades,
    graficar_mapa_reprobacion,
)
from src.components.student_profile import mostrar_ficha_estudiante
from src.services.ai_copilot import generar_analisis_ia, explicar_grafico_ia
from src.services.auth import authenticate, create_professor, load_users


st.set_page_config(
    page_title="Analitica Academica UDP",
    page_icon="YS",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos del archivo Excel con cachA para evitar recargas."""
    return cargar_datos_limpios()


def _filtrar_datos_por_rol(df, usuario):
    if usuario.get("role") != "profesor":
        return df
    if "DOCENTE" not in df.columns:
        return df.iloc[0:0].copy()
    nombre_docente = usuario.get("teacher_name", "").strip().upper()
    return df[
        df["DOCENTE"].astype(str).str.strip().str.upper() == nombre_docente
    ].copy()


def main():
    # Sistema de autenticacion
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("Acceso Restringido - Analitica Academica UDP")
        st.markdown("**Informacion estrictamente confidencial - Solo personal autorizado**")
        
        col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
        with col_login2:
            st.markdown("---")
            username = st.text_input("Usuario", placeholder="Ingrese su usuario")
            password = st.text_input(
                "Contrasena",
                type="password",
                placeholder="Ingrese la contrasena",
            )
            if st.button("Ingresar", width="stretch"):
                usuario = authenticate(username, password)
                if usuario is not None:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Contrasena incorrecta. Acceso denegado.")
            st.markdown("---")
        return
    
    st.title("Analitica Academica UDP")
    st.markdown("Sistema de analisis del rendimiento academico para la toma de decisiones")
    usuario = st.session_state.get("usuario", {})
    rol = usuario.get("role", "")
    st.sidebar.caption(
        f"Sesion: {usuario.get('display_name', 'Usuario')} ({rol})"
    )
    
    # Boton de cerrar sesion
    if st.sidebar.button("Cerrar Sesion"):
        st.session_state.autenticado = False
        st.session_state.pop("usuario", None)
        st.rerun()
    
    # API Key para IA
    st.sidebar.markdown("---")
    st.sidebar.subheader("Inteligencia Artificial")
    api_key_google = st.sidebar.text_input(
        "API Key de Google Gemini",
        type="password",
        placeholder="Ingrese su API Key",
        help="Opcional - Solo si desea usar el analisis con IA"
    )
    
    # Cargar datos
    with st.spinner("Cargando y limpiando datos..."):
        df = _filtrar_datos_por_rol(cargar_datos(), usuario)
    
    if df.empty:
        st.error("No se encontraron datos para mostrar.")
        return
    
    # Pestañas de navegacion
    nombres_tabs = [
        "Vision Global",
        "Riesgo periodo vigente",
        "Analisis Detallado",
    ]
    if rol in {"admin", "director"}:
        nombres_tabs.append("Analisis por Estudiante")
    if rol == "admin":
        nombres_tabs.append("Gestion de Datos (Administrador)")
    tabs = st.tabs(nombres_tabs)
    tab1 = tabs[0]
    
    with tab1:
        # Barra lateral con filtros globales
        st.sidebar.header("Filtros Globales")
    
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

        # Los periodos en curso no se mezclan con historicos cerrados.
        periodos_historicos = []
        if 'PERIODO' in df.columns:
            periodos_historicos = obtener_periodos_historicos(df)

        if periodos_historicos:
            periodo_inicio, periodo_fin = st.sidebar.select_slider(
                "Rango de periodos academicos",
                options=periodos_historicos,
                value=(periodos_historicos[0], periodos_historicos[-1]),
            )
            indice_inicio = periodos_historicos.index(periodo_inicio)
            indice_fin = periodos_historicos.index(periodo_fin)
            periodos_seleccionados = periodos_historicos[indice_inicio:indice_fin + 1]
        else:
            st.sidebar.warning("No hay periodos historicos cerrados disponibles.")
            periodos_seleccionados = []
        periodo_en_curso_seleccionado = False
    
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
    
        # Filtro de Asignatura dependiente del programa
        asignaturas_disponibles = ["Todas"]
        if 'ASIGNATURA' in df.columns:
            df_temp_asig = df
            if programa_seleccionado != "Todos" and 'PROGRAMA' in df.columns:
                df_temp_asig = df[df['PROGRAMA'] == programa_seleccionado]
            asignaturas_unicas = sorted(df_temp_asig['ASIGNATURA'].dropna().unique().tolist())
            asignaturas_disponibles.extend(asignaturas_unicas)

        asignatura_seleccionada = st.sidebar.selectbox(
            "Asignatura",
            options=asignaturas_disponibles,
            index=0
        )

        periodos_cortes_disponibles = []
        if asignatura_seleccionada != "Todas" and "ASIGNATURA" in df.columns:
            datos_materia = df[
                df["ASIGNATURA"].astype(str).str.strip()
                == asignatura_seleccionada
            ].copy()
            if "TIPO_REGISTRO" in datos_materia.columns:
                datos_materia = datos_materia[
                    datos_materia["TIPO_REGISTRO"] == "CON_BOLETIN"
                ]
            if "CALIDAD_CIERRE" in datos_materia.columns:
                datos_materia = datos_materia[
                    ~datos_materia["CALIDAD_CIERRE"].astype(str).str.upper().str.contains(
                        "PERIODO_EN_CURSO_NO_FINAL", na=False
                    )
                ]
            periodos_cortes_disponibles = ordenar_periodos(
                datos_materia["PERIODO"].dropna().astype(str).str.strip().unique(),
            )
        periodos_cortes_seleccionados = st.sidebar.multiselect(
            "Periodos para grafica de cortes",
            options=periodos_cortes_disponibles,
            default=periodos_cortes_disponibles[-3:],
            disabled=asignatura_seleccionada == "Todas",
            help="Solo aparecen periodos en los que se curso la materia seleccionada.",
        )

        semestres_curriculares_disponibles = ["Todos"]
        if "SEMESTRE_ASIGNATURA" in df.columns:
            semestres_curriculares = [
                str(valor).strip()
                for valor in df["SEMESTRE_ASIGNATURA"].dropna().unique()
                if str(valor).strip()
            ]
            semestres_curriculares_disponibles.extend(
                ordenar_semestres_curriculares(semestres_curriculares)
            )

        semestre_curricular_seleccionado = st.sidebar.selectbox(
            "Semestre curricular (mapa)",
            options=semestres_curriculares_disponibles,
            index=0,
            help="Filtra el mapa de reprobacion usando SEMESTRE_ASIGNATURA.",
        )
    
        # Aplicar filtros al DataFrame
        df_filtrado = df.copy()
    
        # Filtrar por el rango de periodos historicos seleccionado
        if 'PERIODO' in df_filtrado.columns and periodos_seleccionados:
            df_filtrado = df_filtrado[
                df_filtrado['PERIODO'].isin(periodos_seleccionados)
            ].copy()
    
        # Filtrar por programa
        if programa_seleccionado != "Todos" and 'PROGRAMA' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['PROGRAMA'] == programa_seleccionado].copy()
    
        # Filtrar por sede
        if sede_seleccionada != "Todas" and 'SEDE' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['SEDE'] == sede_seleccionada].copy()
    
        # Filtrar por asignatura
        if asignatura_seleccionada != "Todas" and 'ASIGNATURA' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['ASIGNATURA'] == asignatura_seleccionada].copy()

        # Conserva todo el historico para calcular correctamente el acumulado
        # aunque el usuario visualice un rango que empiece despues.
        df_tendencias = df.copy()
        if programa_seleccionado != "Todos" and 'PROGRAMA' in df_tendencias.columns:
            df_tendencias = df_tendencias[
                df_tendencias['PROGRAMA'] == programa_seleccionado
            ].copy()
        if sede_seleccionada != "Todas" and 'SEDE' in df_tendencias.columns:
            df_tendencias = df_tendencias[
                df_tendencias['SEDE'] == sede_seleccionada
            ].copy()
    
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
        st.subheader("Analisis ejecutivo integral con IA")
        st.caption("Interpreta las tablas y metricas agregadas del periodo y filtros seleccionados.")
        if st.button("Generar anAlisis ejecutivo integral", width="stretch", key="btn_ia"):
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
    
        st.subheader("Tendencias para direccion academica")
        st.caption(
            "Los calculos usan periodos historicos cerrados y excluyen registros SIN_BOLETIN."
        )

        with st.container(border=True, width="stretch"):
            st.markdown("### Promedio acumulado historico por periodo")
            st.caption(
                "Promedio acumulado general de los estudiantes, separado "
                "por grupos acumulados."
            )
            figura_promedios = graficar_tendencia_promedios(
                df_tendencias,
                periodos_visibles=periodos_seleccionados,
            )
            st.plotly_chart(
                figura_promedios,
                width="stretch",
                key="tendencia_promedios",
            )

        with st.container(border=True, width="stretch"):
            st.markdown("### Cantidad de aprobados y reprobados")
            figura_cantidades = graficar_tendencia_cantidades(
                df_filtrado,
                periodos_visibles=periodos_seleccionados,
            )
            st.plotly_chart(
                figura_cantidades,
                width="stretch",
                key="tendencia_cantidades",
            )

        with st.container(border=True, width="stretch"):
            st.markdown("### Dificultad por materia y periodo")
            st.caption(
                "Cada celda muestra el porcentaje de estudiantes reprobados "
                "en una materia y periodo."
            )
            if semestre_curricular_seleccionado == "Todos":
                st.markdown(
                    "## :orange[Selecciona un semestre curricular en los filtros "
                    "para consultar esta grafica]"
                )
            else:
                st.caption(
                    f"Semestre curricular seleccionado: "
                    f"{semestre_curricular_seleccionado}"
                )
            df_mapa = df_filtrado
            semestres_mapa = None
            if semestre_curricular_seleccionado != "Todos":
                semestres_mapa = [semestre_curricular_seleccionado]
            figura_mapa = graficar_mapa_reprobacion(
                df_mapa,
                semestres_curriculares=semestres_mapa,
            )
            st.plotly_chart(
                figura_mapa,
                width="stretch",
                key="mapa_reprobacion",
            )

    
        st.markdown("---")

        # Panel principal con rendimiento por materias
        st.subheader("Rendimiento por Asignatura")

        rendimiento_materias = calcular_rendimiento_materias(df_filtrado)

        if not rendimiento_materias.empty:
            # Ordenar por tasa de reprobacion
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
                    "porcentaje_reprobacion": st.column_config.NumberColumn("% Reprobacion", format="%.2f%%")
                }
            )
        else:
            st.info("No hay datos de rendimiento por materia para mostrar con los filtros seleccionados.")

            # Seccion condicional para periodo en curso
            if periodo_en_curso_seleccionado:
                st.markdown("---")
                st.subheader("Estudiantes en Riesgo - Periodo en Curso (2026-2)")
                st.caption(
                    "Basado unicamente en PRIMER_PARCIAL con calificacion "
                    f"menor a {NOTA_MINIMA_APROBACION:.1f} en 2 o mas asignaturas"
                )
        
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

    with tabs[1]:
        st.subheader("Riesgo academico del periodo")
        periodo_vigente = obtener_periodo_vigente(df)
        periodos_riesgo = []
        if "PERIODO" in df.columns:
            periodos_riesgo = ordenar_periodos(
                df["PERIODO"].dropna().astype(str).str.strip().unique()
            )
        if not periodo_vigente or not periodos_riesgo:
            st.info("No se encontro un periodo academico para analizar.")
        else:
            periodo_riesgo = st.selectbox(
                "Periodo academico",
                options=periodos_riesgo,
                index=periodos_riesgo.index(periodo_vigente),
                help="Por defecto se selecciona el ultimo periodo vigente del Excel.",
            )
            st.caption(
                "La nota necesaria se calcula con 30% para cada parcial y 40% "
                "para el examen final. Se muestran materias que requieren "
                "al menos 2.90 en el examen."
            )
            sin_calificaciones = obtener_estudiantes_sin_calificaciones(
                df,
                periodo_riesgo,
            )
            if not sin_calificaciones.empty:
                st.markdown("### Estudiantes sin calificaciones registradas")
                st.caption(
                    "Estas personas tienen primer y segundo corte en cero "
                    "en todas sus materias del periodo y no se incluyen en "
                    "las tablas de riesgo."
                )
                st.dataframe(
                    sin_calificaciones,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "ID_ESTUDIANTE": st.column_config.TextColumn(
                            "ID estudiante"
                        ),
                        "NOMBRE_COMPLETO": st.column_config.TextColumn(
                            "Nombre del estudiante",
                            width="large",
                        ),
                        "Materias sin calificaciones": st.column_config.NumberColumn(
                            "Materias sin calificaciones",
                            format="%d",
                        ),
                        "Materias del periodo": st.column_config.TextColumn(
                            "Materias del periodo",
                            width="large",
                        ),
                        "PERIODO": st.column_config.TextColumn("Periodo"),
                    },
                )
            riesgo = calcular_riesgo_periodo_vigente(df, periodo_riesgo)
            if riesgo.empty:
                st.success(
                    "No hay estudiantes con materias en peligro para este periodo."
                )
            else:
                semestres_riesgo = sorted(
                    riesgo["SEMESTRE_ASIGNATURA"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                )
                orden_semestres = {
                    nombre: indice
                    for indice, nombre in enumerate(
                        [
                            "PRIMER SEMESTRE",
                            "SEGUNDO SEMESTRE",
                            "TERCER SEMESTRE",
                            "CUARTO SEMESTRE",
                            "QUINTO SEMESTRE",
                            "SEXTO SEMESTRE",
                            "SEPTIMO SEMESTRE",
                            "OCTAVO SEMESTRE",
                            "NOVENO SEMESTRE",
                            "DECIMO SEMESTRE",
                        ]
                    )
                }
                semestres_riesgo.sort(
                    key=lambda valor: (
                        orden_semestres.get(valor.upper(), 999),
                        valor,
                    )
                )
                semestre_riesgo = st.selectbox(
                    "Semestre curricular de las materias",
                    options=["Todos"] + semestres_riesgo,
                    help="Filtra las materias por su semestre curricular.",
                )
                riesgo_filtrado = riesgo
                if semestre_riesgo != "Todos":
                    riesgo_filtrado = riesgo[
                        riesgo["SEMESTRE_ASIGNATURA"].astype(str).str.strip()
                        == semestre_riesgo
                    ].copy()
                sin_calificaciones_semestre = obtener_estudiantes_sin_calificaciones(
                    df,
                    periodo_riesgo,
                    semestre_riesgo,
                )
                if not sin_calificaciones_semestre.empty:
                    riesgo_filtrado = riesgo_filtrado[
                        ~riesgo_filtrado["ID_ESTUDIANTE"].isin(
                            sin_calificaciones_semestre["ID_ESTUDIANTE"]
                        )
                    ].copy()
                if riesgo_filtrado.empty:
                    st.info(
                        "No hay materias en peligro para el semestre curricular "
                        "seleccionado."
                    )
                    st.stop()

                resumen = resumir_materias_periodo(
                    df,
                    riesgo_filtrado,
                    periodo_riesgo,
                    semestre_riesgo,
                )
                st.markdown("### Resumen de materias del periodo")
                st.dataframe(
                    resumen,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "ASIGNATURA": st.column_config.TextColumn(
                            "Materia", width="large"
                        ),
                        "Profesor(es)": st.column_config.TextColumn(
                            "Profesor(es)", width="large"
                        ),
                        "Estudiantes inscritos": st.column_config.NumberColumn(
                            "Estudiantes inscritos", format="%d"
                        ),
                        "Estudiantes en peligro": st.column_config.NumberColumn(
                            "Estudiantes en peligro", format="%d"
                        ),
                    },
                )

                st.markdown("### Consultas interactivas")
                materias = sorted(resumen["ASIGNATURA"].unique())

                materia = st.selectbox(
                    "Materia",
                    options=materias,
                    key="riesgo_materia",
                )
                datos_materia = df[
                    df["PERIODO"].astype(str).str.strip() == str(periodo_riesgo)
                ].copy()
                if "TIPO_REGISTRO" in datos_materia.columns:
                    datos_materia = datos_materia[
                        datos_materia["TIPO_REGISTRO"] == "CON_BOLETIN"
                    ].copy()
                datos_materia = filtrar_semestre(datos_materia, semestre_riesgo)
                datos_materia = filtrar_asignatura(datos_materia, materia)
                profesores = ["Todos"]
                if "DOCENTE" in datos_materia.columns:
                    profesores += sorted(
                        {
                            str(profesor).strip()
                            for profesor in datos_materia["DOCENTE"]
                            if pd.notna(profesor) and str(profesor).strip()
                        }
                    )
                profesor = st.selectbox(
                    "Profesor que dicta la materia",
                    options=profesores,
                    key="riesgo_profesor",
                )
                if profesor != "Todos":
                    datos_materia = filtrar_docente(datos_materia, profesor)
                if st.button(
                    "Ver estudiantes de esta materia",
                    width="stretch",
                    key="ver_estudiantes_materia",
                ):
                    estudiantes_materia = set(
                        datos_materia["ID_ESTUDIANTE"].astype(str)
                    )
                    detalle_materia = riesgo_filtrado[
                        (riesgo_filtrado["ASIGNATURA"] == materia)
                        & (
                            riesgo_filtrado["ID_ESTUDIANTE"].astype(str).isin(
                                estudiantes_materia
                            )
                        )
                    ]
                    if profesor != "Todos" and "DOCENTE" in detalle_materia.columns:
                        detalle_materia = detalle_materia[
                            detalle_materia["DOCENTE"].astype(str).str.strip()
                            == profesor
                        ]
                    cantidad_peligro = detalle_materia["ID_ESTUDIANTE"].nunique()
                    detalle_materia = detalle_materia[
                        [
                            "ASIGNATURA",
                            "NUMERO_DOCUMENTO",
                            "NOMBRE_COMPLETO",
                            "Primer corte",
                            "Segundo corte",
                            "Necesita examen final",
                            "Nivel de peligro",
                        ]
                    ].sort_values("Necesita examen final", ascending=False)
                    cantidad_inscritos = datos_materia["ID_ESTUDIANTE"].nunique()
                    st.markdown(
                        f"#### Estudiantes de {materia} + "
                        f"{cantidad_inscritos} inscritos + "
                        f"{cantidad_peligro} en peligro"
                    )
                    st.dataframe(
                        detalle_materia.style.apply(colorear_riesgo, axis=1).format(
                            {
                                "Primer corte": "{:.2f}",
                                "Segundo corte": "{:.2f}",
                                "Necesita examen final": "{:.2f}",
                            }
                        ),
                        width="stretch",
                        hide_index=True,
                    )

    with tabs[2]:
        st.subheader("Analisis detallado por materia")
        st.caption(
            "Estas visualizaciones aparecen de acuerdo con la asignatura "
            "seleccionada en los filtros globales."
        )
        if asignatura_seleccionada == "Todas":
            st.info(
                "Selecciona una asignatura en los filtros globales para "
                "consultar sus graficas detalladas."
            )
        else:
            with st.container(border=True, width="stretch"):
                st.markdown(
                    f"### Promedio de {asignatura_seleccionada} por periodo"
                )
                st.caption(
                    "Promedio general de la materia y promedios separados "
                    "por aprobados y reprobados."
                )
                figura_materia = graficar_tendencia_promedio_materia(
                    df_filtrado,
                    asignatura_seleccionada,
                    periodos_visibles=periodos_seleccionados,
                )
                st.plotly_chart(
                    figura_materia,
                    width="stretch",
                    key="tendencia_promedio_materia",
                )

            with st.container(border=True, width="stretch"):
                st.markdown("### Reprobados por corte y periodo")
                st.caption(
                    "Compara cuantos estudiantes reprobaron en cada corte y "
                    "muestra el promedio de sus notas al pasar el mouse."
                )
                figura_cortes = graficar_reprobados_por_corte(
                    df,
                    asignatura_seleccionada,
                    periodos_cortes_seleccionados,
                )
                st.plotly_chart(
                    figura_cortes,
                    width="stretch",
                    key="reprobados_por_corte",
                )

    indice_estudiante = 3
    if rol in {"admin", "director"}:
        with tabs[indice_estudiante]:
            mostrar_ficha_estudiante(df)
        indice_estudiante += 1
    
    if rol == "admin":
        with tabs[indice_estudiante]:
            st.subheader("Gestion de Datos - Administrador")
            st.caption("Carga de archivos Excel y administracion de cuentas.")

            st.markdown("### Crear cuenta de profesor")
            st.caption(
                "La cuenta solo podra consultar estadisticas de las materias "
                "asignadas al docente seleccionado."
            )
            docentes_disponibles = []
            if "DOCENTE" in cargar_datos().columns:
                docentes_disponibles = sorted(
                    nombre
                    for nombre in cargar_datos()["DOCENTE"].dropna().astype(str).str.strip().unique()
                    if nombre
                )
            with st.form("crear_cuenta_profesor"):
                nuevo_usuario = st.text_input("Usuario del profesor")
                nombre_profesor = st.text_input("Nombre visible")
                docente_asociado = st.selectbox(
                    "Docente del archivo academico",
                    options=docentes_disponibles,
                )
                nueva_contrasena = st.text_input(
                    "Contrasena inicial",
                    type="password",
                )
                crear_cuenta = st.form_submit_button(
                    "Crear cuenta",
                    width="stretch",
                )
            if crear_cuenta:
                try:
                    create_professor(
                        nuevo_usuario,
                        nombre_profesor,
                        docente_asociado,
                        nueva_contrasena,
                    )
                    st.success(
                        f"Cuenta '{nuevo_usuario.strip().lower()}' creada correctamente."
                    )
                except ValueError as error:
                    st.error(str(error))

            st.markdown("### Cuentas registradas")
            cuentas = pd.DataFrame(
                [
                    {
                        "Usuario": user.get("username", ""),
                        "Nombre": user.get("display_name", ""),
                        "Rol": user.get("role", ""),
                        "Docente asociado": user.get("teacher_name", ""),
                    }
                    for user in load_users()
                ]
            )
            st.dataframe(cuentas, width="stretch", hide_index=True)

            st.markdown("---")
            uploaded_file = st.file_uploader(
                "Seleccionar archivo Excel (.xlsx)",
                type=["xlsx"],
                help="Suba el archivo consolidado con las hojas de registros academicos",
            )

            if uploaded_file is not None:
                st.success(f"Archivo cargado: {uploaded_file.name}")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                try:
                    with st.spinner("Procesando y validando datos..."):
                        df_nuevo = cargar_datos_limpios(ruta_excel=tmp_path)
                    st.markdown("### Resumen del archivo cargado")
                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.metric("Total de filas nuevas", f"{len(df_nuevo):,}")
                    with col_r2:
                        if "PERIODO" in df_nuevo.columns:
                            periodos_detectados = df_nuevo["PERIODO"].dropna().unique()
                            st.metric("Periodos detectados", f"{len(periodos_detectados)}")
                            st.caption(", ".join(sorted(str(p) for p in periodos_detectados)))
                        else:
                            st.metric("Periodos detectados", "N/A")
                    with col_r3:
                        if "ID_ESTUDIANTE" in df_nuevo.columns:
                            st.metric(
                                "Cantidad de estudiantes",
                                f"{df_nuevo['ID_ESTUDIANTE'].nunique():,}",
                            )
                        else:
                            st.metric("Cantidad de estudiantes", "N/A")

                    if st.button(
                        "Guardar y consolidar",
                        width="stretch",
                        type="primary",
                        key="guardar_consolidar",
                    ):
                        carpeta_data = "data"
                        os.makedirs(carpeta_data, exist_ok=True)
                        nombre_seguro = os.path.basename(uploaded_file.name)
                        if not nombre_seguro:
                            raise ValueError("El archivo cargado no tiene un nombre valido.")
                        ruta_destino = os.path.join(carpeta_data, nombre_seguro)
                        ruta_temporal_data = f"{ruta_destino}.uploading"
                        shutil.copy2(tmp_path, ruta_temporal_data)
                        for nombre_archivo in os.listdir(carpeta_data):
                            ruta_archivo = os.path.join(carpeta_data, nombre_archivo)
                            if (
                                os.path.isfile(ruta_archivo)
                                and os.path.splitext(nombre_archivo)[1].lower()
                                in {".xlsx", ".xls", ".xlsm"}
                            ):
                                os.remove(ruta_archivo)
                        os.replace(ruta_temporal_data, ruta_destino)
                        st.cache_data.clear()
                        st.success(
                            f"Archivo guardado exitosamente como '{nombre_seguro}'. "
                            "El archivo Excel anterior fue reemplazado."
                        )
                        st.info("Recarga la pagina para ver los datos actualizados.")
                except (OSError, ValueError) as error:
                    st.error(f"Error al procesar o guardar el archivo: {error}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            else:
                st.info("Seleccione un archivo .xlsx para comenzar la carga")


if __name__ == "__main__":
    main()
