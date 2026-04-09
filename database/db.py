"""
Módulo de base de datos SQLite para la app de gestión de avisos.
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "avisos.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            nombre   TEXT    NOT NULL,
            email    TEXT    NOT NULL,
            role     TEXT    NOT NULL CHECK(role IN ('supervisor','coordinador')),
            active   INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS avisos (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            num_aviso             INTEGER UNIQUE NOT NULL,
            fecha_solicitud       TEXT    NOT NULL,
            generador_ot          TEXT,
            generador_aviso       TEXT,
            esm                   TEXT,
            sede                  TEXT,
            descripcion           TEXT,
            estado                TEXT    DEFAULT 'En proceso'
                                          CHECK(estado IN ('En proceso','Acabado','Falta material')),
            coordinador_id        INTEGER REFERENCES users(id),
            enlace_drive          TEXT,
            material_necesario    TEXT,
            fecha_cierre          TEXT,
            created_at            TEXT    DEFAULT (datetime('now','localtime')),
            updated_at            TEXT    DEFAULT (datetime('now','localtime')),
            alerta_1mes_enviada   INTEGER DEFAULT 0,
            alerta_3meses_enviada INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS comentarios (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            aviso_id          INTEGER NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
            user_id           INTEGER NOT NULL REFERENCES users(id),
            texto             TEXT    NOT NULL,
            fecha_comentario  TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS notificaciones (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            aviso_id       INTEGER REFERENCES avisos(id),
            mensaje        TEXT    NOT NULL,
            tipo           TEXT,
            leida          INTEGER DEFAULT 0,
            fecha_creacion TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_avisos_estado     ON avisos(estado);
        CREATE INDEX IF NOT EXISTS idx_avisos_sede       ON avisos(sede);
        CREATE INDEX IF NOT EXISTS idx_avisos_coord      ON avisos(coordinador_id);
        CREATE INDEX IF NOT EXISTS idx_notif_user_leida  ON notificaciones(user_id, leida);
        CREATE INDEX IF NOT EXISTS idx_coment_aviso      ON comentarios(aviso_id);
    """)

    # Insertar usuarios predeterminados si la tabla está vacía
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        import bcrypt
        usuarios = [
            ("jaime",    "Jaime",     "jaime@justicia.es",       "supervisor",  "jaime1234"),
            ("luisreina","Luis Reina","luisreina@justicia.es",   "supervisor",  "luis1234"),
            ("gustavo",  "Gustavo",   "gustavo@justicia.es",     "supervisor",  "gustavo1234"),
            ("fran",     "Fran",      "fran@justicia.es",        "coordinador", "fran1234"),
            ("andres",   "Andrés",    "andres@justicia.es",      "coordinador", "andres1234"),
            ("jonatan",  "Jonatan",   "jonatan@justicia.es",     "coordinador", "jonatan1234"),
            ("laura",    "Laura",     "laura@justicia.es",       "coordinador", "laura1234"),
        ]
        for username, nombre, email, role, pwd in usuarios:
            hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
            c.execute(
                "INSERT INTO users (username, nombre, email, role, active) VALUES (?,?,?,?,1)",
                (username, nombre, email, role)
            )
        conn.commit()

        # Guardar contraseñas en config.yaml la primera vez
        _write_auth_config(conn)

    conn.commit()
    conn.close()


def _write_auth_config(conn):
    """Genera config.yaml para streamlit-authenticator con las contraseñas por defecto."""
    import bcrypt, yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        return

    c = conn.cursor()
    rows = c.execute("SELECT username, nombre, email FROM users").fetchall()

    defaults = {
        "jaime":    "jaime1234",
        "luisreina":"luis1234",
        "gustavo":  "gustavo1234",
        "fran":     "fran1234",
        "andres":   "andres1234",
        "jonatan":  "jonatan1234",
        "laura":    "laura1234",
    }

    credentials = {"usernames": {}}
    for row in rows:
        uname = row["username"]
        pwd = defaults.get(uname, "cambiar1234")
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        credentials["usernames"][uname] = {
            "name":     row["nombre"],
            "email":    row["email"],
            "password": hashed,
        }

    config = {
        "credentials": credentials,
        "cookie": {
            "expiry_days": 30,
            "key":         "mantenimiento_judicial_secret_key_2024",
            "name":        "mantenimiento_judicial_cookie",
        },
        "preauthorized": {"emails": []},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
