"""Utilidades para ordenar y filtrar periodos academicos."""

import pandas as pd


def clave_periodo_academico(periodo):
    try:
        anio, semestre = str(periodo).strip().split("-", 1)
        return int(anio), int(semestre)
    except (TypeError, ValueError):
        return 9999, 9999


def ordenar_periodos(periodos):
    return sorted(
        {str(periodo).strip() for periodo in periodos if pd.notna(periodo)},
        key=clave_periodo_academico,
    )


def periodos_historicos(df: pd.DataFrame):
    if df is None or df.empty or "PERIODO" not in df.columns:
        return []
    mascara_vigente = pd.Series(False, index=df.index)
    if "CALIDAD_CIERRE" in df.columns:
        mascara_vigente = df["CALIDAD_CIERRE"].astype(str).str.upper().str.contains(
            "PERIODO_EN_CURSO_NO_FINAL",
            na=False,
        )
    return ordenar_periodos(df.loc[~mascara_vigente, "PERIODO"])


def ordenar_semestres_curriculares(semestres):
    orden = {
        nombre: indice
        for indice, nombre in enumerate(
            (
                "PRIMER",
                "SEGUNDO",
                "TERCER",
                "CUARTO",
                "QUINTO",
                "SEXTO",
                "SEPTIMO",
                "OCTAVO",
                "NOVENO",
                "DECIMO",
            )
        )
    }
    return sorted(
        {str(semestre).strip() for semestre in semestres if str(semestre).strip()},
        key=lambda valor: (
            orden.get(valor.upper().split()[0], 999),
            valor,
        ),
    )
