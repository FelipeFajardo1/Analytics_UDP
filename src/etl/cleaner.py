import os
import pandas as pd
import numpy as np


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
    Convierte notas numéricas a float, reemplazando comas por puntos
    y manejando valores vacíos o nulos de forma segura.
    """
    # Columnas de notas típicas
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
            # Reemplazar valores vacíos o 'nan', 'None', etc.
            df[col] = df[col].replace(['nan', 'None', '', 'NaN'], np.nan)
            # Convertir a numérico
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def cargar_datos_limpios(ruta_excel=None):
    """
    Lee el archivo Excel ubicado en data/Consolidado_Calificaciones_2023_2026 v2 .xlsx
    cargando las 4 hojas de registros académicos (2023, 2024, 2025, 2026).
    
    Limpia los datos, convierte notas a numérico y crea columna TIPO_REGISTRO
    basada en ESTADO_BOLETIN. Respeta CALIDAD_CIERRE para identificar periodos
    históricos frente al periodo en curso.
    
    Returns:
        DataFrame consolidado con todas las hojas
    """
    if ruta_excel is None:
        # Ruta por defecto relativa al proyecto
        ruta_excel = os.path.join('data', 'Consolidado_Calificaciones_2023_2026 v2 .xlsx')
    
    # Hojas a cargar
    hojas_a_cargar = [
        '2023 registros  académicos',
        '2024 registros  académicos',
        '2025 registros  académicos',
        '2026 registros  académicos'
    ]
    
    # Leer archivo Excel
    excel_file = pd.ExcelFile(ruta_excel)
    
    dataframes = []
    
    for hoja in hojas_a_cargar:
        # Buscar la hoja con el nombre correcto (manejar acentos)
        if hoja in excel_file.sheet_names:
            nombre_hoja = hoja
        else:
            # Buscar por patrón
            nombre_hoja = None
            for s in excel_file.sheet_names:
                if str(s).strip().startswith(hoja.split()[0]):
                    nombre_hoja = s
                    break
            if nombre_hoja is None:
                raise ValueError(f"No se encontró la hoja para {hoja}")
        
        # Leer hoja
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
    
    return df_consolidado
