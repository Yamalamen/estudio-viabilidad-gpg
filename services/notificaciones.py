"""
CRUD de notificaciones in-app.
"""
from database.db import get_connection


def get_notificaciones(user_id: int, solo_no_leidas: bool = False) -> list:
    conn = get_connection()
    sql = """
        SELECT n.*, a.num_aviso
        FROM notificaciones n
        LEFT JOIN avisos a ON n.aviso_id = a.id
        WHERE n.user_id = ?
    """
    params = [user_id]
    if solo_no_leidas:
        sql += " AND n.leida = 0"
    sql += " ORDER BY n.fecha_creacion DESC LIMIT 50"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_no_leidas(user_id: int) -> int:
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM notificaciones WHERE user_id=? AND leida=0",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return n


def crear_notificacion(user_id: int, mensaje: str, tipo: str, aviso_id: int = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO notificaciones (user_id, aviso_id, mensaje, tipo)
        VALUES (?, ?, ?, ?)
    """, (user_id, aviso_id, mensaje, tipo))
    conn.commit()
    conn.close()


def marcar_leida(notif_id: int):
    conn = get_connection()
    conn.execute("UPDATE notificaciones SET leida=1 WHERE id=?", (notif_id,))
    conn.commit()
    conn.close()


def marcar_todas_leidas(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE notificaciones SET leida=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
