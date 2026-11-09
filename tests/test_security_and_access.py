import json

import pandas as pd
import pytest

from src.services import auth
from src.services.access import filtrar_datos_por_rol
from src.services.data_management import reemplazar_archivos_excel


def test_profesor_solo_ve_sus_registros():
    datos = pd.DataFrame(
        {
            "DOCENTE": ["Ana", "Bruno"],
            "ID_ESTUDIANTE": ["1", "2"],
        }
    )

    resultado = filtrar_datos_por_rol(
        datos,
        {"role": "profesor", "teacher_name": " ana "},
    )

    assert list(resultado["ID_ESTUDIANTE"]) == ["1"]


def test_director_y_admin_ven_todos_los_registros():
    datos = pd.DataFrame({"DOCENTE": ["Ana", "Bruno"]})

    assert len(filtrar_datos_por_rol(datos, {"role": "director"})) == 2
    assert len(filtrar_datos_por_rol(datos, {"role": "admin"})) == 2


def test_cambio_de_contrasena_exige_contrasena_actual(tmp_path, monkeypatch):
    usuarios = [
        {
            "username": "ana",
            "display_name": "Ana",
            "role": "profesor",
            "teacher_name": "Ana",
            "password_hash": auth._password_hash("inicial123"),
        }
    ]
    ruta = tmp_path / "auth_users.json"
    ruta.write_text(json.dumps(usuarios), encoding="utf-8")
    monkeypatch.setattr(auth, "USERS_PATH", ruta)
    monkeypatch.setattr(auth, "registrar_evento", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="actual"):
        auth.change_password("ana", "incorrecta", "nueva1234")

    auth.change_password("ana", "inicial123", "nueva1234")
    assert auth.authenticate("ana", "nueva1234")["username"] == "ana"


def test_reemplazo_crea_respaldo_del_excel_anterior(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = data_dir / "backups"
    data_dir.mkdir()
    anterior = data_dir / "anterior.xlsx"
    nuevo = tmp_path / "nuevo.xlsx"
    anterior.write_bytes(b"anterior")
    nuevo.write_bytes(b"nuevo")

    destino, respaldo = reemplazar_archivos_excel(
        data_dir,
        nuevo,
        "actual.xlsx",
        backup_dir,
    )

    assert destino.read_bytes() == b"nuevo"
    assert respaldo is not None
    assert (respaldo / "anterior.xlsx").read_bytes() == b"anterior"
