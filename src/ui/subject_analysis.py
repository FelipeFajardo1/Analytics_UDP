"""Vista de análisis detallado por asignatura."""

import streamlit as st

from src.components.charts import (
    graficar_reprobados_por_corte,
    graficar_tendencia_promedio_materia,
)


def render_subject_analysis_tab(
    df,
    df_filtrado,
    asignatura_seleccionada,
    periodos_seleccionados,
    periodos_cortes_seleccionados,
):
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
        return

    with st.container(border=True, width="stretch"):
        st.markdown(f"### Promedio de {asignatura_seleccionada} por periodo")
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
