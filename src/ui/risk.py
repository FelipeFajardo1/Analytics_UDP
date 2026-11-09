"""Vista de riesgo académico del periodo vigente."""

import pandas as pd
import streamlit as st

from src.components.tables import colorear_riesgo
from src.services.filters import filtrar_asignatura, filtrar_docente, filtrar_semestre
from src.services.metrics import (
    calcular_riesgo_periodo_vigente,
    obtener_estudiantes_sin_calificaciones,
    obtener_periodo_vigente,
    resumir_materias_periodo,
)
from src.services.periods import ordenar_periodos


def render_risk_tab(df):
    st.subheader("Riesgo academico del periodo")
    periodo_vigente = obtener_periodo_vigente(df)
    periodos_riesgo = []
    if "PERIODO" in df.columns:
        periodos_riesgo = ordenar_periodos(
            df["PERIODO"].dropna().astype(str).str.strip().unique()
        )
    if not periodo_vigente or not periodos_riesgo:
        st.info("No se encontro un periodo academico para analizar.")
        return

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
    sin_calificaciones = obtener_estudiantes_sin_calificaciones(df, periodo_riesgo)
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
                "ID_ESTUDIANTE": st.column_config.TextColumn("ID estudiante"),
                "NOMBRE_COMPLETO": st.column_config.TextColumn(
                    "Nombre del estudiante", width="large"
                ),
                "Materias sin calificaciones": st.column_config.NumberColumn(
                    "Materias sin calificaciones", format="%d"
                ),
                "Materias del periodo": st.column_config.TextColumn(
                    "Materias del periodo", width="large"
                ),
                "PERIODO": st.column_config.TextColumn("Periodo"),
            },
        )

    riesgo = calcular_riesgo_periodo_vigente(df, periodo_riesgo)
    if riesgo.empty:
        st.success("No hay estudiantes con materias en peligro para este periodo.")
        return

    semestres_riesgo = sorted(
        riesgo["SEMESTRE_ASIGNATURA"].dropna().astype(str).str.strip().unique()
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
        key=lambda valor: (orden_semestres.get(valor.upper(), 999), valor)
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
        df, periodo_riesgo, semestre_riesgo
    )
    if not sin_calificaciones_semestre.empty:
        riesgo_filtrado = riesgo_filtrado[
            ~riesgo_filtrado["ID_ESTUDIANTE"].isin(
                sin_calificaciones_semestre["ID_ESTUDIANTE"]
            )
        ].copy()
    if riesgo_filtrado.empty:
        st.info(
            "No hay materias en peligro para el semestre curricular seleccionado."
        )
        return

    resumen = resumir_materias_periodo(
        df, riesgo_filtrado, periodo_riesgo, semestre_riesgo
    )
    st.markdown("### Resumen de materias del periodo")
    st.dataframe(
        resumen,
        width="stretch",
        hide_index=True,
        column_config={
            "ASIGNATURA": st.column_config.TextColumn("Materia", width="large"),
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
    materia = st.selectbox("Materia", options=materias, key="riesgo_materia")
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
    if not st.button(
        "Ver estudiantes de esta materia",
        width="stretch",
        key="ver_estudiantes_materia",
    ):
        return

    estudiantes_materia = set(datos_materia["ID_ESTUDIANTE"].astype(str))
    detalle_materia = riesgo_filtrado[
        (riesgo_filtrado["ASIGNATURA"] == materia)
        & (
            riesgo_filtrado["ID_ESTUDIANTE"].astype(str).isin(estudiantes_materia)
        )
    ]
    if profesor != "Todos" and "DOCENTE" in detalle_materia.columns:
        detalle_materia = detalle_materia[
            detalle_materia["DOCENTE"].astype(str).str.strip() == profesor
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
        f"#### Estudiantes de {materia} + {cantidad_inscritos} inscritos + "
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
