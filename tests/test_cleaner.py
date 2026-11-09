import numpy as np
import pandas as pd
import pytest

from src.etl.cleaner import (
    _convertir_notas_a_numerico,
    _limpiar_texto,
    cargar_datos_limpios,
)


def test_limpia_columnas_y_texto_sin_alterar_nulos():
    datos = pd.DataFrame({" Nombre ": ["  Ana   Perez  ", None]})

    resultado = _limpiar_texto(datos)

    assert list(resultado.columns) == ["Nombre"]
    assert resultado.loc[0, "Nombre"] == "Ana Perez"
    assert pd.isna(resultado.loc[1, "Nombre"])


def test_convierte_notas_con_coma_y_valores_invalidos():
    datos = pd.DataFrame(
        {
            "NOTA": ["4,5", "3.0", "", "no valida"],
            "DEFINITIVA_ALMACENADA": ["2,75", None, "nan", "5"],
        }
    )

    resultado = _convertir_notas_a_numerico(datos)

    assert resultado["NOTA"].tolist()[:2] == [4.5, 3.0]
    assert pd.isna(resultado.loc[2, "NOTA"])
    assert pd.isna(resultado.loc[3, "NOTA"])
    assert resultado["DEFINITIVA_ALMACENADA"].tolist()[0] == 2.75
    assert pd.isna(resultado.loc[1, "DEFINITIVA_ALMACENADA"])
    assert np.isclose(resultado.loc[3, "DEFINITIVA_ALMACENADA"], 5.0)


def test_carga_cualquier_ano_y_omite_hojas_auxiliares(tmp_path):
    archivo = tmp_path / "academico.xlsx"
    datos = pd.DataFrame(
        {
            "PERIODO": ["2027-1"],
            "ID_ESTUDIANTE": ["1"],
            "ASIGNATURA": ["Algebra"],
        }
    )
    with pd.ExcelWriter(archivo) as writer:
        datos.to_excel(writer, sheet_name="2027 registros academicos", index=False)
        pd.DataFrame({"auxiliar": [1]}).to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )

    resultado = cargar_datos_limpios(str(archivo))

    assert len(resultado) == 1
    assert resultado.loc[0, "PERIODO"] == "2027-1"


def test_rechaza_archivo_sin_columnas_academicas_obligatorias(tmp_path):
    archivo = tmp_path / "invalido.xlsx"
    with pd.ExcelWriter(archivo) as writer:
        pd.DataFrame({"nombre": ["Ana"]}).to_excel(
            writer,
            sheet_name="2027 registros academicos",
            index=False,
        )

    with pytest.raises(ValueError, match="columnas obligatorias"):
        cargar_datos_limpios(str(archivo))
