"""
CRUD de comentarios/anotaciones de un aviso.
"""
from database.db import get_connection


def get_comentarios(aviso_id: int) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, u.nombre AS autor_nombre
        FROM comentarios c
        JOIN users u ON c.user_id = u.id
        WHERE c.aviso_id = ?
        ORDER BY c.fecha_comentario ASC
    """, (aviso_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_comentario(aviso_id: int, user_id: int, texto: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO comentarios (aviso_id, user_id, texto)
        VALUES (?, ?, ?)
    """, (aviso_id, user_id, texto.strip()))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id
