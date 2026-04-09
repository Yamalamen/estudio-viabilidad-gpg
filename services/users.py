"""
Consultas de usuarios.
"""
from database.db import get_connection


def get_all_users(role: str = None) -> list:
    conn = get_connection()
    sql = "SELECT * FROM users WHERE active=1"
    params = []
    if role:
        sql += " AND role=?"
        params.append(role)
    sql += " ORDER BY nombre"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_coordinadores() -> list:
    return get_all_users(role="coordinador")


def get_laura() -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username='laura' AND active=1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username: str, nombre: str, email: str, role: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (username, nombre, email, role) VALUES (?,?,?,?)",
        (username, nombre, email, role)
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def toggle_user_active(user_id: int, active: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()


def update_user_email(user_id: int, email: str):
    conn = get_connection()
    conn.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))
    conn.commit()
    conn.close()
