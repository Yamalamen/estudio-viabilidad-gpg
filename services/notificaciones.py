"""
CRUD de notificaciones in-app — compatible SQLite y PostgreSQL.
"""
from sqlalchemy import text
from database.db import get_connection, _now


def get_notificaciones(user_id: int, solo_no_leidas: bool = False) -> list:
    sql = """
        SELECT n.*, a.num_aviso
        FROM notificaciones n
        LEFT JOIN avisos a ON n.aviso_id = a.id
        WHERE n.user_id = :user_id
    """
    params = {"user_id": user_id}
    if solo_no_leidas:
        sql += " AND n.leida = 0"
    sql += " ORDER BY n.fecha_creacion DESC LIMIT 50"
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]


def count_no_leidas(user_id: int) -> int:
    with get_connection() as conn:
        return conn.execute(text(
            "SELECT COUNT(*) FROM notificaciones WHERE user_id=:uid AND leida=0"
        ), {"uid": user_id}).scalar() or 0


def crear_notificacion(user_id: int, mensaje: str, tipo: str, aviso_id: int = None):
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO notificaciones (user_id, aviso_id, mensaje, tipo, fecha_creacion)
            VALUES (:uid, :aid, :msg, :tipo, :fecha)
        """), {"uid": user_id, "aid": aviso_id, "msg": mensaje,
               "tipo": tipo, "fecha": _now()})
        conn.commit()


def marcar_leida(notif_id: int):
    with get_connection() as conn:
        conn.execute(text("UPDATE notificaciones SET leida=1 WHERE id=:id"), {"id": notif_id})
        conn.commit()


def marcar_todas_leidas(user_id: int):
    with get_connection() as conn:
        conn.execute(text("UPDATE notificaciones SET leida=1 WHERE user_id=:uid"), {"uid": user_id})
        conn.commit()
