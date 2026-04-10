"""
Capa de base de datos compatible con SQLite (local) y PostgreSQL (Supabase/cloud).
Detecta automáticamente DATABASE_URL para usar PostgreSQL en producción.
"""
import os
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import StaticPool

# ── Configuración de conexión ──────────────────────────────────────────────────
_DATABASE_URL = os.getenv("DATABASE_URL")

if not _DATABASE_URL:
    _DATA_DIR = Path(__file__).parent.parent / "data"
    _DATA_DIR.mkdir(exist_ok=True)
    _DATABASE_URL = f"sqlite:///{_DATA_DIR / 'avisos.db'}"

_IS_SQLITE = _DATABASE_URL.startswith("sqlite")

if _IS_SQLITE:
    _engine = create_engine(
        _DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
else:
    # PostgreSQL — Supabase añade ?sslmode=require en la URL
    if "sslmode" not in _DATABASE_URL:
        _DATABASE_URL += "?sslmode=require"
    _engine = create_engine(_DATABASE_URL, echo=False, pool_pre_ping=True)


def get_connection():
    """Devuelve una conexión SQLAlchemy (usar con 'with')."""
    return _engine.connect()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """Crea las tablas si no existen e inserta los usuarios por defecto."""
    with _engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                nombre   TEXT    NOT NULL,
                email    TEXT    NOT NULL,
                role     TEXT    NOT NULL,
                active   INTEGER DEFAULT 1
            )
        """ if _IS_SQLITE else """
            CREATE TABLE IF NOT EXISTS users (
                id       SERIAL  PRIMARY KEY,
                username TEXT    UNIQUE NOT NULL,
                nombre   TEXT    NOT NULL,
                email    TEXT    NOT NULL,
                role     TEXT    NOT NULL,
                active   INTEGER DEFAULT 1
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS avisos (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                num_aviso             INTEGER UNIQUE NOT NULL,
                fecha_solicitud       TEXT    NOT NULL,
                generador_ot          TEXT,
                generador_aviso       TEXT,
                esm                   TEXT,
                sede                  TEXT,
                descripcion           TEXT,
                estado                TEXT    DEFAULT 'En proceso',
                coordinador_id        INTEGER,
                enlace_drive          TEXT,
                material_necesario    TEXT,
                fecha_cierre          TEXT,
                created_at            TEXT,
                updated_at            TEXT,
                alerta_1mes_enviada   INTEGER DEFAULT 0,
                alerta_3meses_enviada INTEGER DEFAULT 0
            )
        """ if _IS_SQLITE else """
            CREATE TABLE IF NOT EXISTS avisos (
                id                    SERIAL  PRIMARY KEY,
                num_aviso             INTEGER UNIQUE NOT NULL,
                fecha_solicitud       TEXT    NOT NULL,
                generador_ot          TEXT,
                generador_aviso       TEXT,
                esm                   TEXT,
                sede                  TEXT,
                descripcion           TEXT,
                estado                TEXT    DEFAULT 'En proceso',
                coordinador_id        INTEGER,
                enlace_drive          TEXT,
                material_necesario    TEXT,
                fecha_cierre          TEXT,
                created_at            TEXT,
                updated_at            TEXT,
                alerta_1mes_enviada   INTEGER DEFAULT 0,
                alerta_3meses_enviada INTEGER DEFAULT 0
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                aviso_id         INTEGER NOT NULL,
                user_id          INTEGER NOT NULL,
                texto            TEXT    NOT NULL,
                fecha_comentario TEXT
            )
        """ if _IS_SQLITE else """
            CREATE TABLE IF NOT EXISTS comentarios (
                id               SERIAL  PRIMARY KEY,
                aviso_id         INTEGER NOT NULL,
                user_id          INTEGER NOT NULL,
                texto            TEXT    NOT NULL,
                fecha_comentario TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notificaciones (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                aviso_id       INTEGER,
                mensaje        TEXT    NOT NULL,
                tipo           TEXT,
                leida          INTEGER DEFAULT 0,
                fecha_creacion TEXT
            )
        """ if _IS_SQLITE else """
            CREATE TABLE IF NOT EXISTS notificaciones (
                id             SERIAL  PRIMARY KEY,
                user_id        INTEGER NOT NULL,
                aviso_id       INTEGER,
                mensaje        TEXT    NOT NULL,
                tipo           TEXT,
                leida          INTEGER DEFAULT 0,
                fecha_creacion TEXT
            )
        """))

        # Índices (ignorar si ya existen)
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_avisos_estado    ON avisos(estado)",
            "CREATE INDEX IF NOT EXISTS idx_avisos_sede      ON avisos(sede)",
            "CREATE INDEX IF NOT EXISTS idx_avisos_coord     ON avisos(coordinador_id)",
            "CREATE INDEX IF NOT EXISTS idx_notif_user_leida ON notificaciones(user_id, leida)",
            "CREATE INDEX IF NOT EXISTS idx_coment_aviso     ON comentarios(aviso_id)",
        ]:
            try:
                conn.execute(text(idx_sql))
            except Exception:
                pass

        conn.commit()

        # Usuarios por defecto (solo si la tabla está vacía)
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        if count == 0:
            _seed_users(conn)
            conn.commit()
            _write_auth_config(conn)


def _seed_users(conn):
    usuarios = [
        ("jaime",     "Jaime",      "jaime@justicia.es",      "supervisor"),
        ("luisreina", "Luis Reina", "luisreina@justicia.es",  "supervisor"),
        ("gustavo",   "Gustavo",    "gustavo@justicia.es",    "supervisor"),
        ("fran",      "Fran",       "fran@justicia.es",       "coordinador"),
        ("andres",    "Andrés",     "andres@justicia.es",     "coordinador"),
        ("jonatan",   "Jonatan",    "jonatan@justicia.es",    "coordinador"),
        ("laura",     "Laura",      "laura@justicia.es",      "coordinador"),
    ]
    for username, nombre, email, role in usuarios:
        conn.execute(text(
            "INSERT INTO users (username, nombre, email, role, active) "
            "VALUES (:u, :n, :e, :r, 1)"
        ), {"u": username, "n": nombre, "e": email, "r": role})


def _write_auth_config(conn):
    """Genera config.yaml para streamlit-authenticator con las contraseñas por defecto."""
    import bcrypt, yaml

    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        return

    rows = conn.execute(text("SELECT username, nombre, email FROM users")).fetchall()

    defaults = {
        "jaime":     "jaime1234",
        "luisreina": "luis1234",
        "gustavo":   "gustavo1234",
        "fran":      "fran1234",
        "andres":    "andres1234",
        "jonatan":   "jonatan1234",
        "laura":     "laura1234",
    }

    credentials = {"usernames": {}}
    for row in rows:
        uname = row._mapping["username"]
        pwd   = defaults.get(uname, "cambiar1234")
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        credentials["usernames"][uname] = {
            "name":     row._mapping["nombre"],
            "email":    row._mapping["email"],
            "password": hashed,
        }

    config = {
        "credentials": credentials,
        "cookie": {
            "expiry_days": 30,
            "key":  "mantenimiento_judicial_secret_key_2024",
            "name": "mantenimiento_judicial_cookie",
        },
        "preauthorized": {"emails": []},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
