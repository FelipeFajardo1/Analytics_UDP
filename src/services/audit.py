"""Auditoria local de eventos administrativos y de autenticacion."""

from datetime import datetime, timezone
from pathlib import Path
import json


AUDIT_PATH = Path(__file__).resolve().parents[2] / "audit.log"


def registrar_evento(evento, usuario="", detalle=None):
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evento": str(evento),
        "usuario": str(usuario),
        "detalle": detalle or {},
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
