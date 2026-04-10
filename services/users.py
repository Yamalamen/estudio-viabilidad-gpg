"""
Consultas de usuarios — compatible SQLite y PostgreSQL.
"""
from sqlalchemy import text
from database.db import get_connection


def _row(r) -> dict:
    return dict(r._mapping)


def get_all_users(role: str = None) -> list:
    sql = "SELECT * FROM users WHERE active=1"
    params = {}
    if role:
        sql += " AND role=:role"
        params["role"] = role
    sql += " ORDER BY nombre"
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        return [_row(r) for r in rows]


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(text(
            "SELECT * FROM users WHERE username=:u"
        ), {"u": username}).fetchone()
        return _row(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(text(
            "SELECT * FROM users WHERE id=:id"
        ), {"id": user_id}).fetchone()
        return _row(row) if row else None


def get_coordinadores() -> list:
    return get_all_users(role="coordinador")


def get_laura() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(text(
            "SELECT * FROM users WHERE username='laura' AND active=1"
        )).fetchone()
        return _row(row) if row else None


def create_user(username: str, nombre: str, email: str, role: str) -> int:
    with get_connection() as conn:
        conn.execute(text(
            "INSERT INTO users (username, nombre, email, role) VALUES (:u,:n,:e,:r)"
        ), {"u": username, "n": nombre, "e": email, "r": role})
        conn.commit()
        row = conn.execute(text(
            "SELECT id FROM users WHERE username=:u"
        ), {"u": username}).fetchone()
        return row._mapping["id"]


def toggle_user_active(user_id: int, active: bool):
    with get_connection() as conn:
        conn.execute(text(
            "UPDATE users SET active=:a WHERE id=:id"
        ), {"a": 1 if active else 0, "id": user_id})
        conn.commit()


def update_user_email(user_id: int, email: str):
    with get_connection() as conn:
        conn.execute(text(
            "UPDATE users SET email=:e WHERE id=:id"
        ), {"e": email, "id": user_id})
        conn.commit()
