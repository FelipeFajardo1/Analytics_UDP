from pathlib import Path
import re
import pandas as pd
import numpy as np
from src.constants import EXTENSIONES_EXCEL


def _limpiar_texto(df):
    """
    Limpia espacios en blanco en nombres de columnas y en todas las columnas de texto.
    """
    # Limpiar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Limpiar columnas de texto
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            # Aplicar strip a valores string, mantener NaN
            df[col] = df[col].apply(
                lambda x: str(x).strip() if pd.notna(x) and isinstance(x, str) else x
            )
            # Si hay strings con espacios extra (no solo al inicio/final)
            df[col] = df[col].apply(
                lambda x: ' '.join(str(x).split()) if pd.notna(x) and isinstance(x, str) else x
            )
    
    return df


def _convertir_notas_a_numerico(df):
    """
    Convierte notas numericas a float, reemplazando comas por puntos
    y manejando valores vacios o nulos de forma segura.
    """
    # Columnas de notas tipicas
    columnas_notas = [
        'PRIMER_PARCIAL', 'SEGUNDO_PARCIAL', 'EXAMEN_FINAL',
        'NOTA_PONDERADA_REFERENCIA', 'NOTA_FINAL_ALMACENADA',
        'HABILITACION', 'DEFINITIVA_ALMACENADA', 'NOTA'
    ]
    
    for col in columnas_notas:
        if col in df.columns:
            # Convertir a string para reemplazar comas
            df[col] = df[col].astype(str)
            # Reemplazar comas por puntos
            df[col] = df[col].str.replace(',', '.', regex=False)
            # Reemplazar valores vacios o 'nan', 'None', etc.
            df[col] = df[col].replace(['nan', 'None', '', 'NaN'], np.nan)
            # Convertir a numerico
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def _encontrar_archivo_excel():
    """Encuentra el unico archivo Excel disponible en la carpeta data."""
    carpeta_data = Path("data")
    archivos_excel = sorted(
        archivo for archivo in carpeta_data.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_EXCEL
    ) if carpeta_data.exists() else []

    if not archivos_excel:
        raise FileNotFoundError(
            "No se encontro ningun archivo Excel dentro de la carpeta data."
        )

    if len(archivos_excel) > 1:
        nombres = ", ".join(archivo.name for archivo in archivos_excel)
        raise ValueError(
            "Debe existir un solo archivo Excel dentro de la carpeta data. "
            f"Archivos encontrados: {nombres}"
        )

    return str(archivos_excel[0])


def cargar_datos_limpios(ruta_excel=None):
    """
    Lee el unico archivo Excel disponible en la carpeta data
    cargando las 4 hojas de registros academicos (2023, 2024, 2025, 2026).
    
    Limpia los datos, convierte notas a numerico y crea columna TIPO_REGISTRO
    basada en ESTADO_BOLETIN. Respeta CALIDAD_CIERRE para identificar periodos
    historicos frente al periodo en curso.
    
    Returns:
        DataFrame consolidado con todas las hojas
    """
    if ruta_excel is None:
        ruta_excel = _encontrar_archivo_excel()
    
    # Leer archivo Excel
    excel_file = pd.ExcelFile(ruta_excel)
    hojas_a_cargar = [
        hoja
        for hoja in excel_file.sheet_names
        if re.match(r"^\s*\d{4}\b", str(hoja))
    ]
    if not hojas_a_cargar:
        raise ValueError(
            "No se encontraron hojas academicas cuyo nombre comience por un año."
        )

    dataframes = []
    for nombre_hoja in hojas_a_cargar:
        df = pd.read_excel(excel_file, sheet_name=nombre_hoja)
        
        # Limpiar
        df = _limpiar_texto(df)
        df = _convertir_notas_a_numerico(df)
        
        # Crear columna TIPO_REGISTRO basada en ESTADO_BOLETIN
        if 'ESTADO_BOLETIN' in df.columns:
            def _mapear_tipo_registro(val):
                if pd.isna(val):
                    return np.nan
                v = str(val).strip().upper()
                if 'CON_BOLETIN' in v:
                    return 'CON_BOLETIN'
                if 'SIN_BOLETIN' in v:
                    return 'SIN_BOLETIN'
                return val
            df['TIPO_REGISTRO'] = df['ESTADO_BOLETIN'].apply(_mapear_tipo_registro)
        else:
            df['TIPO_REGISTRO'] = np.nan
        
        dataframes.append(df)
    
    # Consolidar todos los DataFrames
    df_consolidado = pd.concat(dataframes, ignore_index=True)
    columnas_minimas = {"PERIODO", "ID_ESTUDIANTE", "ASIGNATURA"}
    faltantes = columnas_minimas.difference(df_consolidado.columns)
    if faltantes:
        raise ValueError(
            "El archivo academico no contiene las columnas obligatorias: "
            + ", ".join(sorted(faltantes))
        )
    return df_consolidado
