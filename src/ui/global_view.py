"""Vista global y filtros compartidos del dashboard."""

import pandas as pd
import streamlit as st

from src.components.charts import (
    graficar_mapa_reprobacion,
    graficar_tendencia_cantidades,
    graficar_tendencia_promedios,
)
from src.constants import NOTA_MINIMA_APROBACION
from src.services.ai_copilot import generar_analisis_ia
from src.services.metrics import (
    calcular_kpis_globales,
    calcular_rendimiento_materias,
    detectar_alertas_tempranas,
)
from src.services.periods import (
    ordenar_periodos,
    ordenar_semestres_curriculares,
    periodos_historicos as obtener_periodos_historicos,
)


def render_global_tab(df, api_key_google):
    """Renderiza la vista global y retorna el contexto de filtros."""
    st.sidebar.header("Filtros Globales")

    programas_disponibles = ["Todos"]
    if "PROGRAMA" in df.columns:
        programas_disponibles.extend(sorted(df["PROGRAMA"].dropna().unique()))
    programa_seleccionado = st.sidebar.selectbox(
        "Programa", options=programas_disponibles, index=0
    )

    periodos_historicos = obtener_periodos_historicos(df)
    if periodos_historicos:
        periodo_inicio, periodo_fin = st.sidebar.select_slider(
            "Rango de periodos academicos",
            options=periodos_historicos,
            value=(periodos_historicos[0], periodos_historicos[-1]),
        )
        indice_inicio = periodos_historicos.index(periodo_inicio)
        indice_fin = periodos_historicos.index(periodo_fin)
        periodos_seleccionados = periodos_historicos[indice_inicio : indice_fin + 1]
    else:
        st.sidebar.warning("No hay periodos historicos cerrados disponibles.")
        periodos_seleccionados = []

    sedes_disponibles = ["Todas"]
    if "SEDE" in df.columns:
        sedes_disponibles.extend(sorted(df["SEDE"].dropna().unique()))
    sede_seleccionada = st.sidebar.selectbox(
        "Sede", options=sedes_disponibles, index=0
    )

    asignaturas_disponibles = ["Todas"]
    if "ASIGNATURA" in df.columns:
        df_temp_asig = df
        if programa_seleccionado != "Todos" and "PROGRAMA" in df.columns:
            df_temp_asig = df[df["PROGRAMA"] == programa_seleccionado]
        asignaturas_disponibles.extend(
            sorted(df_temp_asig["ASIGNATURA"].dropna().unique())
        )
    asignatura_seleccionada = st.sidebar.selectbox(
        "Asignatura", options=asignaturas_disponibles, index=0
    )

    periodos_cortes_disponibles = []
    if asignatura_seleccionada != "Todas" and "ASIGNATURA" in df.columns:
        datos_materia = df[
            df["ASIGNATURA"].astype(str).str.strip() == asignatura_seleccionada
        ].copy()
        if "TIPO_REGISTRO" in datos_materia.columns:
            datos_materia = datos_materia[
                datos_materia["TIPO_REGISTRO"] == "CON_BOLETIN"
            ]
        if "CALIDAD_CIERRE" in datos_materia.columns:
            datos_materia = datos_materia[
                ~datos_materia["CALIDAD_CIERRE"]
                .astype(str)
                .str.upper()
                .str.contains("PERIODO_EN_CURSO_NO_FINAL", na=False)
            ]
        periodos_cortes_disponibles = ordenar_periodos(
            datos_materia["PERIODO"].dropna().astype(str).str.strip().unique()
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
        semestres_curriculares_disponibles.extend(
            ordenar_semestres_curriculares(
                [
                    str(valor).strip()
                    for valor in df["SEMESTRE_ASIGNATURA"].dropna().unique()
                    if str(valor).strip()
                ]
            )
        )
    semestre_curricular_seleccionado = st.sidebar.selectbox(
        "Semestre curricular (mapa)",
        options=semestres_curriculares_disponibles,
        index=0,
        help="Filtra el mapa de reprobacion usando SEMESTRE_ASIGNATURA.",
    )

    df_filtrado = df.copy()
    if "PERIODO" in df_filtrado.columns and periodos_seleccionados:
        df_filtrado = df_filtrado[
            df_filtrado["PERIODO"].isin(periodos_seleccionados)
        ].copy()
    if programa_seleccionado != "Todos" and "PROGRAMA" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["PROGRAMA"] == programa_seleccionado
        ].copy()
    if sede_seleccionada != "Todas" and "SEDE" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["SEDE"] == sede_seleccionada].copy()
    if asignatura_seleccionada != "Todas" and "ASIGNATURA" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["ASIGNATURA"] == asignatura_seleccionada
        ].copy()

    df_tendencias = df.copy()
    if programa_seleccionado != "Todos" and "PROGRAMA" in df_tendencias.columns:
        df_tendencias = df_tendencias[
            df_tendencias["PROGRAMA"] == programa_seleccionado
        ].copy()
    if sede_seleccionada != "Todas" and "SEDE" in df_tendencias.columns:
        df_tendencias = df_tendencias[
            df_tendencias["SEDE"] == sede_seleccionada
        ].copy()
    st.sidebar.markdown("---")
    st.sidebar.info(f"Registros filtrados: {len(df_filtrado):,}")

    st.subheader("Indicadores Globales")
    kpis = calcular_kpis_globales(df_filtrado)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Estudiantes Unicos", f"{kpis.get('total_estudiantes_unicos', 0):,}")
    col2.metric("Total Matriculas", f"{kpis.get('total_matriculas', 0):,}")
    nota_prom = kpis.get("nota_promedio_global", 0)
    col3.metric(
        "Nota Promedio Global",
        "N/A" if pd.isna(nota_prom) else f"{nota_prom:.2f}",
    )
    col4.metric(
        "Aprobacion / Reprobacion",
        f"{kpis.get('tasa_aprobacion', 0):.1f}% / "
        f"{kpis.get('tasa_reprobacion', 0):.1f}%",
    )

    st.markdown("---")
    st.subheader("Analisis ejecutivo integral con IA")
    st.caption("Interpreta las tablas y metricas agregadas del periodo y filtros seleccionados.")
    if st.button("Generar anAlisis ejecutivo integral", width="stretch", key="btn_ia"):
        if not api_key_google or not api_key_google.strip():
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
    st.caption("Los calculos usan periodos historicos cerrados y excluyen registros SIN_BOLETIN.")
    with st.container(border=True, width="stretch"):
        st.markdown("### Promedio acumulado historico por periodo")
        st.caption("Promedio acumulado general de los estudiantes, separado por grupos acumulados.")
        st.plotly_chart(
            graficar_tendencia_promedios(
                df_tendencias, periodos_visibles=periodos_seleccionados
            ),
            width="stretch",
            key="tendencia_promedios",
        )
    with st.container(border=True, width="stretch"):
        st.markdown("### Cantidad de aprobados y reprobados")
        st.plotly_chart(
            graficar_tendencia_cantidades(
                df_filtrado, periodos_visibles=periodos_seleccionados
            ),
            width="stretch",
            key="tendencia_cantidades",
        )
    with st.container(border=True, width="stretch"):
        st.markdown("### Dificultad por materia y periodo")
        st.caption("Cada celda muestra el porcentaje de estudiantes reprobados en una materia y periodo.")
        semestres_mapa = (
            None
            if semestre_curricular_seleccionado == "Todos"
            else [semestre_curricular_seleccionado]
        )
        st.plotly_chart(
            graficar_mapa_reprobacion(
                df_filtrado, semestres_curriculares=semestres_mapa
            ),
            width="stretch",
            key="mapa_reprobacion",
        )

    st.markdown("---")
    st.subheader("Rendimiento por Asignatura")
    rendimiento_materias = calcular_rendimiento_materias(df_filtrado)
    if rendimiento_materias.empty:
        st.info("No hay datos de rendimiento por materia para mostrar con los filtros seleccionados.")
    else:
        rendimiento_materias = rendimiento_materias.sort_values(
            "porcentaje_reprobacion", ascending=False
        )
        st.dataframe(
            rendimiento_materias,
            width="stretch",
            hide_index=True,
            column_config={
                "ASIGNATURA": st.column_config.TextColumn("Asignatura", width="large"),
                "num_inscritos": st.column_config.NumberColumn("Inscritos", format="%d"),
                "nota_promedio": st.column_config.NumberColumn("Nota Promedio", format="%.2f"),
                "porcentaje_reprobacion": st.column_config.NumberColumn(
                    "% Reprobacion", format="%.2f%%"
                ),
            },
        )

    return {
        "df_filtrado": df_filtrado,
        "periodos_seleccionados": periodos_seleccionados,
        "periodos_cortes_seleccionados": periodos_cortes_seleccionados,
        "asignatura_seleccionada": asignatura_seleccionada,
    }
