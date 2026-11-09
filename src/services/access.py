"""Reglas de acceso a los datos según el rol autenticado."""


def filtrar_datos_por_rol(df, usuario):
    if usuario.get("role") != "profesor":
        return df
    if "DOCENTE" not in df.columns:
        return df.iloc[0:0].copy()
    nombre_docente = usuario.get("teacher_name", "").strip().upper()
    return df[
        df["DOCENTE"].astype(str).str.strip().str.upper() == nombre_docente
    ].copy()
