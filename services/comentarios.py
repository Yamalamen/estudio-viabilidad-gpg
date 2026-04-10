"""
CRUD de comentarios/anotaciones — compatible SQLite y PostgreSQL.
"""
from sqlalchemy import text
from database.db import get_connection, _now


def get_comentarios(aviso_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT c.*, u.nombre AS autor_nombre
            FROM comentarios c
            JOIN users u ON c.user_id = u.id
            WHERE c.aviso_id = :aviso_id
            ORDER BY c.fecha_comentario ASC
        """), {"aviso_id": aviso_id}).fetchall()
        return [dict(r._mapping) for r in rows]


def add_comentario(aviso_id: int, user_id: int, texto: str) -> int:
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO comentarios (aviso_id, user_id, texto, fecha_comentario)
            VALUES (:aviso_id, :user_id, :texto, :fecha)
        """), {"aviso_id": aviso_id, "user_id": user_id,
               "texto": texto.strip(), "fecha": _now()})
        conn.commit()
        row = conn.execute(text(
            "SELECT id FROM comentarios WHERE aviso_id=:a AND user_id=:u ORDER BY fecha_comentario DESC LIMIT 1"
        ), {"a": aviso_id, "u": user_id}).fetchone()
        return row._mapping["id"] if row else 0
