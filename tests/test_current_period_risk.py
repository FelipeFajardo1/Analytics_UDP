import pandas as pd

from src.services.metrics import (
    calcular_detalle_estudiante_periodo,
    calcular_kpis_globales,
    calcular_riesgo_periodo_vigente,
    calcular_rendimiento_materias,
    obtener_estudiantes_sin_calificaciones,
    obtener_periodo_vigente,
    resumir_materias_periodo,
)


def _datos_periodo_vigente():
    return pd.DataFrame(
        [
            {
                "PERIODO": "2026-2",
                "CALIDAD_CIERRE": "PERIODO_EN_CURSO_NO_FINAL",
                "TIPO_REGISTRO": "CON_BOLETIN",
                "ID_ESTUDIANTE": "1",
                "NUMERO_DOCUMENTO": "100",
                "NOMBRE_COMPLETO": "Ana",
                "ASIGNATURA": "Algebra",
                "SEMESTRE_ASIGNATURA": "PRIMER SEMESTRE",
                "PRIMER_PARCIAL": 2.0,
                "SEGUNDO_PARCIAL": 2.0,
            },
            {
                "PERIODO": "2026-2",
                "CALIDAD_CIERRE": "PERIODO_EN_CURSO_NO_FINAL",
                "TIPO_REGISTRO": "CON_BOLETIN",
                "ID_ESTUDIANTE": "1",
                "NUMERO_DOCUMENTO": "100",
                "NOMBRE_COMPLETO": "Ana",
                "ASIGNATURA": "Calculo",
                "SEMESTRE_ASIGNATURA": "SEGUNDO SEMESTRE",
                "PRIMER_PARCIAL": 3.5,
                "SEGUNDO_PARCIAL": 3.0,
            },
            {
                "PERIODO": "2026-2",
                "CALIDAD_CIERRE": "PERIODO_EN_CURSO_NO_FINAL",
                "TIPO_REGISTRO": "CON_BOLETIN",
                "ID_ESTUDIANTE": "2",
                "NUMERO_DOCUMENTO": "200",
                "NOMBRE_COMPLETO": "Luis",
                "ASIGNATURA": "Algebra",
                "SEMESTRE_ASIGNATURA": "PRIMER SEMESTRE",
                "PRIMER_PARCIAL": 1.0,
                "SEGUNDO_PARCIAL": 1.0,
            },
        ]
    )


def test_detecta_automaticamente_el_ultimo_periodo_vigente():
    assert obtener_periodo_vigente(_datos_periodo_vigente()) == "2026-2"


def test_calcula_nota_final_y_cantidad_de_materias_en_peligro():
    resultado = calcular_riesgo_periodo_vigente(_datos_periodo_vigente())

    ana = resultado[resultado["ID_ESTUDIANTE"] == "1"]
    algebra_ana = ana[ana["ASIGNATURA"] == "Algebra"].iloc[0]
    assert algebra_ana["Necesita examen final"] == 4.5
    assert algebra_ana["Nivel de peligro"] == "Peligro alto"
    assert set(ana["Materias en peligro"]) == {1}

    luis = resultado[resultado["ID_ESTUDIANTE"] == "2"].iloc[0]
    assert luis["Necesita examen final"] == 6.0
    assert luis["Nivel de peligro"] == "No puede aprobar"
    assert set(resultado["SEMESTRE_ASIGNATURA"]) == {"PRIMER SEMESTRE"}


def test_excluye_estudiante_con_ceros_en_todas_sus_materias():
    datos = _datos_periodo_vigente()
    datos = pd.concat(
        [
            datos,
            pd.DataFrame(
                [
                    {
                        "PERIODO": "2026-2",
                        "TIPO_REGISTRO": "CON_BOLETIN",
                        "ID_ESTUDIANTE": "3",
                        "NUMERO_DOCUMENTO": "300",
                        "NOMBRE_COMPLETO": "Marta",
                        "ASIGNATURA": "Algebra",
                        "PRIMER_PARCIAL": 0.0,
                        "SEGUNDO_PARCIAL": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    sin_calificaciones = obtener_estudiantes_sin_calificaciones(datos, "2026-2")
    riesgo = calcular_riesgo_periodo_vigente(datos, "2026-2")

    assert list(sin_calificaciones["ID_ESTUDIANTE"]) == ["3"]
    assert "Marta" in sin_calificaciones.loc[0, "NOMBRE_COMPLETO"]
    assert "3" not in set(riesgo["ID_ESTUDIANTE"])


def test_lista_sin_calificaciones_respetando_semestre_curricular():
    datos = _datos_periodo_vigente()
    resultado = obtener_estudiantes_sin_calificaciones(
        datos,
        "2026-2",
        "PRIMER SEMESTRE",
    )

    assert resultado.empty


def test_muestra_materias_con_ambos_cortes_en_cero_si_el_estudiante_tiene_avance():
    datos = _datos_periodo_vigente()
    datos = pd.concat(
        [
            datos,
            pd.DataFrame(
                [
                    {
                        "PERIODO": "2026-2",
                        "TIPO_REGISTRO": "CON_BOLETIN",
                        "ID_ESTUDIANTE": "1",
                        "NUMERO_DOCUMENTO": "100",
                        "NOMBRE_COMPLETO": "Ana",
                        "ASIGNATURA": "Fisica",
                        "SEMESTRE_ASIGNATURA": "TERCER SEMESTRE",
                        "PRIMER_PARCIAL": 0.0,
                        "SEGUNDO_PARCIAL": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    resultado = calcular_riesgo_periodo_vigente(datos, "2026-2")

    fisica = resultado[resultado["ASIGNATURA"] == "Fisica"].iloc[0]
    assert fisica["Necesita examen final"] == 7.5


def test_calcula_detalle_de_todas_las_materias_del_estudiante():
    detalle = calcular_detalle_estudiante_periodo(
        _datos_periodo_vigente(),
        "2026-2",
        "1",
    )

    assert set(detalle["ASIGNATURA"]) == {"Algebra", "Calculo"}
    assert detalle.loc[
        detalle["ASIGNATURA"] == "Algebra", "Necesita examen final"
    ].iloc[0] == 4.5


def test_resume_profesor_inscritos_y_peligro_por_materia():
    datos = _datos_periodo_vigente()
    datos["DOCENTE"] = ["Profesora A", "Profesor B", "Profesora A"]
    riesgo = calcular_riesgo_periodo_vigente(datos, "2026-2")

    resumen = resumir_materias_periodo(
        datos,
        riesgo,
        "2026-2",
        "PRIMER SEMESTRE",
    )

    algebra = resumen[resumen["ASIGNATURA"] == "Algebra"].iloc[0]
    assert algebra["Profesor(es)"] == "Profesora A"
    assert algebra["Estudiantes inscritos"] == 2
    assert algebra["Estudiantes en peligro"] == 2


def test_tasas_ignoran_estados_academicos_desconocidos():
    datos = pd.DataFrame(
        {
            "ID_ESTUDIANTE": ["1", "2", "3"],
            "ID_MATRICULA": ["m1", "m2", "m3"],
            "TIPO_REGISTRO": ["CON_BOLETIN"] * 3,
            "DEFINITIVA_ALMACENADA": [4.0, 2.0, 3.5],
            "ESTADO_MATERIA": ["APROBO", "PERDIO", "EN PROCESO"],
        }
    )

    kpis = calcular_kpis_globales(datos)

    assert kpis["tasa_aprobacion"] == 50.0
    assert kpis["tasa_reprobacion"] == 50.0


def test_inscritos_no_duplica_registros_del_mismo_estudiante():
    datos = pd.DataFrame(
        {
            "ASIGNATURA": ["Algebra", "Algebra"],
            "ID_ESTUDIANTE": ["1", "1"],
            "TIPO_REGISTRO": ["CON_BOLETIN", "CON_BOLETIN"],
            "DEFINITIVA_ALMACENADA": [2.0, 2.5],
            "ESTADO_MATERIA": ["PERDIO", "PERDIO"],
        }
    )

    rendimiento = calcular_rendimiento_materias(datos)

    assert rendimiento.loc[0, "num_inscritos"] == 1
