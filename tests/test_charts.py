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
                "PRIMER_PARCIAL": 4.0,
                "SEGUNDO_PARCIAL": 3.5,
                "EXAMEN_FINAL": 4.0,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "B",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2024-2",
                "DEFINITIVA_ALMACENADA": 2.0,
                "PRIMER_PARCIAL": 2.0,
                "SEGUNDO_PARCIAL": 2.5,
                "EXAMEN_FINAL": 1.5,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "A",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 3.0,
                "PRIMER_PARCIAL": 2.5,
                "SEGUNDO_PARCIAL": 3.0,
                "EXAMEN_FINAL": 3.5,
                "TIPO_REGISTRO": "CON_BOLETIN",
            },
            {
                "ID_ESTUDIANTE": "B",
                "ASIGNATURA": "Algebra Lineal",
                "PERIODO": "2025-1",
                "DEFINITIVA_ALMACENADA": 1.0,
                "PRIMER_PARCIAL": 1.0,
                "SEGUNDO_PARCIAL": 2.0,
                "EXAMEN_FINAL": 1.5,
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
    assert figura.layout.title.text == "Tendencia de promedios por periodo"


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


def test_reprobados_por_corte_crea_una_linea_por_periodo():
    from src.components.charts import graficar_reprobados_por_corte

    figura = graficar_reprobados_por_corte(
        _datos_tendencias(),
        "Algebra Lineal",
        ["2025-1", "2024-2"],
    )

    assert [traza.name for traza in figura.data] == ["2024-2", "2025-1"]
    assert list(figura.data[0].y) == [1, 1, 1]
    assert list(figura.data[1].y) == [2, 1, 1]
    assert figura.data[1].customdata[0][0] == 1.75
    assert [traza.line.color for traza in figura.data] == [
        "#2563eb",
        "#dc2626",
    ]


def test_reprobados_por_corte_ignora_periodos_no_disponibles():
    from src.components.charts import graficar_reprobados_por_corte

    figura = graficar_reprobados_por_corte(
        _datos_tendencias(),
        "Algebra Lineal",
        ["2023-1"],
    )

    assert len(figura.data) == 0
    assert "Sin datos disponibles" in figura.layout.title.text
