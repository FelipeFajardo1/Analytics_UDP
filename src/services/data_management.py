"""Operaciones seguras para reemplazar el archivo academico."""

from datetime import datetime
from pathlib import Path
import shutil

from src.constants import EXTENSIONES_EXCEL
from src.services.audit import registrar_evento


def respaldar_archivos_excel(data_dir, backup_dir):
    """Copia los Excel actuales a un respaldo fechado antes de reemplazarlos."""
    data_path = Path(data_dir)
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = backup_path / timestamp
    archivos = [
        archivo
        for archivo in data_path.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_EXCEL
    ] if data_path.exists() else []
    if not archivos:
        return None
    destino.mkdir(parents=True, exist_ok=False)
    for archivo in archivos:
        shutil.copy2(archivo, destino / archivo.name)
    return destino


def reemplazar_archivos_excel(data_dir, archivo_nuevo, nombre_archivo, backup_dir):
    """Respalda y reemplaza atómicamente el Excel activo."""
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    respaldo = respaldar_archivos_excel(data_path, backup_dir)
    nombre_seguro = Path(nombre_archivo).name
    if not nombre_seguro:
        raise ValueError("El archivo cargado no tiene un nombre valido.")

    destino = data_path / nombre_seguro
    temporal = data_path / f"{nombre_seguro}.uploading"
    shutil.copy2(archivo_nuevo, temporal)
    try:
        for archivo in data_path.iterdir():
            if (
                archivo.is_file()
                and archivo.suffix.lower() in EXTENSIONES_EXCEL
                and archivo != temporal
            ):
                archivo.unlink()
        temporal.replace(destino)
    except Exception:
        if temporal.exists():
            temporal.unlink()
        raise
    registrar_evento(
        "archivo_academico_reemplazado",
        detalle={
            "archivo": nombre_seguro,
            "respaldo": str(respaldo) if respaldo else "",
        },
    )
    return destino, respaldo
