import pandas as pd

from src.components.charts import (
    _ordenar_periodos,
    _preparar_tendencias,
    graficar_tendencia_cantidades,
    graficar_tendencia_promedio_materia,
    graficar_tendencia_promedios,
)


def _datos_tendencias():
    return pd.DataFrame(
        [
            {
                "ID_ESTUDIANTE": "A",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2024-2",
                "DEFINITIVA_ALMACENADA": 4.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "B",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2024-2",
                "DEFINITIVA_ALMACENADA": 2.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "A",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 3.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "B",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 1.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "C",
                "ASIGNATURA": "Otra materia",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 5.0,
                "TIPO_REGISTRO": "SIN_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "D",
                "ASIGNATURA": "Otra materia",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 5.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
                "CALIDAD_CIERRE": "PERIODO_EN_CURSO_NO_FINAL",
            },
        ]
    )


def test_ordena_periodos_academicos_cronologicamente():
    assert _ordenar_periodos(["2025-1", "2024-2", "2024-1"]) == [
        "2024-1",
        "2024-2",
        "2025-1",
    ]


def test_preparar_tendencias_excluye_registros_no_validos():
    resultado = _preparar_tendencias(_datos_tendencias())

    assert len(resultado) == 4
    assert set(resultado["TIPO_REGISTRO"]) == {"CON_BOLETIN"}
    assert set(resultado["PERIODO"]) == {"2024-2", "2025-1"}


def test_tendencia_por_materia_separa_promedios_y_conteos():
    figura = graficar_tendencia_promedio_materia(
        _datos_tendencias(),
        "Algebra Lineal",
    )

    assert [traza.name for traza in figura.data] == [
        "Promedio general de la materia",
        "Promedio de aprobados",
        "Promedio de reprobados",
    ]
    assert list(figura.data[0].x) == ["2024-2", "2025-1"]
    assert list(figura.data[0].customdata) == [2, 2]
    assert list(figura.data[1].customdata) == [1, 1]
    assert list(figura.data[2].customdata) == [1, 1]
    assert list(figura.data[0].y) == [3.0, 2.0]


def test_tendencia_acumulada_no_depende_de_asignatura():
    figura = graficar_tendencia_promedios(
        _datos_tendencias(),
        periodos_visibles=["2025-1"],
    )

    assert len(figura.data) == 3
    assert list(figura.data[0].x) == ["2025-1"]
    assert list(figura.data[0].customdata) == [2]


def test_tendencia_cantidades_cuenta_aprobados_y_reprobados():
    figura = graficar_tendencia_cantidades(
        _datos_tendencias(),
        periodos_visibles=["2024-2"],
    )

    assert [traza.name for traza in figura.data] == ["Aprobados", "Reprobados"]
    assert list(figura.data[0].y) == [1]
    assert list(figura.data[1].y) == [1]
    assert list(figura.data[0].customdata[0]) == [1, 4.0]
    assert list(figura.data[1].customdata[0]) == [1, 2.0]
