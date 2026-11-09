"""Filtros de datos reutilizables para la interfaz y los servicios."""

import pandas as pd


def solo_con_boletin(df: pd.DataFrame):
    if df is None:
        return pd.DataFrame()
    if "TIPO_REGISTRO" not in df.columns:
        return df.copy()
    return df[df["TIPO_REGISTRO"] == "CON_BOLETIN"].copy()


def filtrar_periodo(df: pd.DataFrame, periodo):
    if df is None or "PERIODO" not in df.columns:
        return pd.DataFrame() if df is None else df.iloc[0:0].copy()
    return df[df["PERIODO"].astype(str).str.strip() == str(periodo).strip()].copy()


def filtrar_semestre(df: pd.DataFrame, semestre):
    if (
        df is None
        or semestre in (None, "Todos")
        or "SEMESTRE_ASIGNATURA" not in df.columns
    ):
        return df.copy() if df is not None else pd.DataFrame()
    return df[
        df["SEMESTRE_ASIGNATURA"].astype(str).str.strip() == str(semestre).strip()
    ].copy()


def filtrar_asignatura(df: pd.DataFrame, asignatura):
    if (
        df is None
        or asignatura in (None, "Todas")
        or "ASIGNATURA" not in df.columns
    ):
        return df.copy() if df is not None else pd.DataFrame()
    return df[
        df["ASIGNATURA"].astype(str).str.strip() == str(asignatura).strip()
    ].copy()


def filtrar_docente(df: pd.DataFrame, docente):
    if (
        df is None
        or docente in (None, "Todos")
        or "DOCENTE" not in df.columns
    ):
        return df.copy() if df is not None else pd.DataFrame()
    return df[
        df["DOCENTE"].astype(str).str.strip() == str(docente).strip()
    ].copy()
