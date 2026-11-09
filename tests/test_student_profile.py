import pandas as pd

from src.components.student_profile import _resumen_promedios_historicos


def test_resume_promedio_por_periodo_con_materias_y_habilitacion():
    datos = pd.DataFrame(
        [
            {
                "PERIODO": "2024-1",
                "ASIGNATURA": "Algebra",
                "DEFINITIVA_ALMACENADA": 2.0,
                "HABILITACION": 1,
            },
            {
                "PERIODO": "2024-1",
                "ASIGNATURA": "Calculo",
                "DEFINITIVA_ALMACENADA": 4.0,
                "HABILITACION": 0,
            },
            {
                "PERIODO": "2024-2",
                "ASIGNATURA": "Algebra",
                "DEFINITIVA_ALMACENADA": 3.5,
                "HABILITACION": "NO",
            },
        ]
    )

    resultado = _resumen_promedios_historicos(datos)

    assert list(resultado["PERIODO"]) == ["2024-1", "2024-2"]
    assert list(resultado["Promedio"]) == [3.0, 3.5]
    assert "Algebra: 2.00 (Habilito: Si)" in resultado.loc[0, "detalle_materias"]
    assert "Calculo: 4.00 (Habilito: No)" in resultado.loc[0, "detalle_materias"]
    assert "Algebra: 3.50 (Habilito: No)" in resultado.loc[1, "detalle_materias"]


def test_resume_sin_columna_habilitacion_indica_no():
    datos = pd.DataFrame(
        [
            {
                "PERIODO": "2024-1",
                "ASIGNATURA": "Algebra",
                "DEFINITIVA_ALMACENADA": 4.0,
            }
        ]
    )

    resultado = _resumen_promedios_historicos(datos)

    assert "Habilito: No" in resultado.loc[0, "detalle_materias"]
