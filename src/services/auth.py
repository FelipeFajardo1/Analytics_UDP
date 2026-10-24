import hashlib
import json
import os
import secrets
from pathlib import Path


USERS_PATH = Path(__file__).resolve().parents[2] / "auth_users.json"
ITERATIONS = 310_000

INITIAL_USERS = [
    {
        "username": "admin",
        "display_name": "Administrador principal",
        "role": "admin",
        "teacher_name": "",
        "password_hash": (
            "2cda834dbc9829444e3800730d706752:"
            "82843f00ca31f17c4fda7305c8bb9e0c9275ed8f1dd6f9199c56050078d1ec2a"
        ),
    },
    {
        "username": "director",
        "display_name": "Director de carrera",
        "role": "director",
        "teacher_name": "",
        "password_hash": (
            "47f7c187a452e13b86c0c5e611778c50:"
            "5f6c7001c841107d3f84074033aac5f47ef423cdcce79fefc7a3880018ba8a11"
        ),
    },
    {
        "username": "edward.alegria",
        "display_name": "Edward Samir Alegria",
        "role": "profesor",
        "teacher_name": "EDWARD SAMIR ALEGRIA SALAZAR",
        "password_hash": (
            "1de080ab8c14f7dce6ee7a45e1f78dae:"
            "a65c95e3cf6908771915b7c73067645cbb677e2fb73a731d2b62b627d788f190"
        ),
    },
]


def _write_users(users):
    temporary_path = USERS_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary_path, USERS_PATH)


def load_users():
    if not USERS_PATH.exists():
        _write_users(INITIAL_USERS)
    try:
        users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("No se pudo leer el archivo local de usuarios.") from error
    if not isinstance(users, list):
        raise RuntimeError("El archivo local de usuarios tiene un formato invalido.")
    return users


def _password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS,
    ).hex()
    return f"{salt}:{digest}"


def verify_password(password, stored_hash):
    try:
        salt, expected_digest = stored_hash.split(":", 1)
        actual_digest = _password_hash(password, salt).split(":", 1)[1]
    except (TypeError, ValueError):
        return False
    return secrets.compare_digest(actual_digest, expected_digest)


def authenticate(username, password):
    username = username.strip().lower()
    for user in load_users():
        if user.get("username", "").lower() == username and verify_password(
            password,
            user.get("password_hash", ""),
        ):
            return user
    return None


def create_professor(username, display_name, teacher_name, password):
    username = username.strip().lower()
    display_name = display_name.strip()
    teacher_name = teacher_name.strip()
    if not username or not display_name or not teacher_name or not password:
        raise ValueError("Todos los campos de la cuenta son obligatorios.")
    users = load_users()
    if any(user.get("username", "").lower() == username for user in users):
        raise ValueError("Ese nombre de usuario ya existe.")
    users.append(
        {
            "username": username,
            "display_name": display_name,
            "role": "profesor",
            "teacher_name": teacher_name,
            "password_hash": _password_hash(password),
        }
    )
    _write_users(users)
