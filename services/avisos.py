"""
CRUD y consultas de avisos — compatible SQLite y PostgreSQL.
"""
import re
from datetime import date, datetime
from sqlalchemy import text
from database.db import get_connection, _now


def _extract_sede(esm: str) -> str:
    if not esm:
        return ""
    m = re.search(r"OBRA CIVIL\s+(.+)$", esm.strip(), re.IGNORECASE)
    return m.group(1).strip() if m else esm.strip()


def _row(r) -> dict:
    return dict(r._mapping)


def get_all_avisos(filters: dict = None) -> list:
    with get_connection() as conn:
        sql = """
            SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
            FROM avisos a
            LEFT JOIN users u ON a.coordinador_id = u.id
            WHERE 1=1
        """
        params = {}

        if filters:
            if filters.get("num_aviso"):
                sql += " AND a.num_aviso = :num_aviso"
                params["num_aviso"] = int(filters["num_aviso"])
            if filters.get("sede"):
                sql += " AND a.sede = :sede"
                params["sede"] = filters["sede"]
            if filters.get("estado"):
                sql += " AND a.estado = :estado"
                params["estado"] = filters["estado"]
            if filters.get("coordinador_id"):
                sql += " AND a.coordinador_id = :coord_id"
                params["coord_id"] = filters["coordinador_id"]
            if filters.get("fecha_desde"):
                sql += " AND a.fecha_solicitud >= :f_desde"
                params["f_desde"] = str(filters["fecha_desde"])
            if filters.get("fecha_hasta"):
                sql += " AND a.fecha_solicitud <= :f_hasta"
                params["f_hasta"] = str(filters["fecha_hasta"])
            if filters.get("generador_ot"):
                sql += " AND a.generador_ot LIKE :gen_ot"
                params["gen_ot"] = f"%{filters['generador_ot']}%"
            if filters.get("generador_aviso"):
                sql += " AND a.generador_aviso LIKE :gen_av"
                params["gen_av"] = f"%{filters['generador_aviso']}%"
            if filters.get("esm"):
                sql += " AND a.esm LIKE :esm"
                params["esm"] = f"%{filters['esm']}%"
            if filters.get("descripcion"):
                sql += " AND a.descripcion LIKE :desc"
                params["desc"] = f"%{filters['descripcion']}%"

        sql += " ORDER BY a.fecha_solicitud DESC"
        rows = conn.execute(text(sql), params).fetchall()
        return [_row(r) for r in rows]


def get_aviso_by_id(aviso_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
            FROM avisos a LEFT JOIN users u ON a.coordinador_id = u.id
            WHERE a.id = :id
        """), {"id": aviso_id}).fetchone()
        return _row(row) if row else None


def create_aviso(data: dict) -> int:
    sede = _extract_sede(data.get("esm", ""))
    now  = _now()
    with get_connection() as conn:
        result = conn.execute(text("""
            INSERT INTO avisos (num_aviso, fecha_solicitud, generador_ot, generador_aviso,
                                esm, sede, descripcion, estado, coordinador_id, enlace_drive,
                                created_at, updated_at)
            VALUES (:num, :fecha, :gen_ot, :gen_av, :esm, :sede, :desc, :estado, :coord, :drive,
                    :now, :now)
        """), {
            "num":    data["num_aviso"],
            "fecha":  str(data["fecha_solicitud"]),
            "gen_ot": data.get("generador_ot", ""),
            "gen_av": data.get("generador_aviso", ""),
            "esm":    data.get("esm", ""),
            "sede":   sede,
            "desc":   data.get("descripcion", ""),
            "estado": data.get("estado", "En proceso"),
            "coord":  data.get("coordinador_id"),
            "drive":  data.get("enlace_drive", ""),
            "now":    now,
        })
        conn.commit()
        # Recuperar el id recién insertado
        new_id = conn.execute(text(
            "SELECT id FROM avisos WHERE num_aviso = :num"
        ), {"num": data["num_aviso"]}).scalar()
        return new_id


def update_aviso(aviso_id: int, data: dict) -> bool:
    if "esm" in data:
        data["sede"] = _extract_sede(data["esm"])

    allowed = [
        "fecha_solicitud", "generador_ot", "generador_aviso", "esm", "sede",
        "descripcion", "estado", "coordinador_id", "enlace_drive",
        "material_necesario", "fecha_cierre",
        "alerta_1mes_enviada", "alerta_3meses_enviada",
    ]
    fields  = [k for k in allowed if k in data]
    if not fields:
        return False

    params = {k: data[k] for k in fields}
    params["updated_at"] = _now()
    params["id"] = aviso_id

    set_clause = ", ".join(f"{k} = :{k}" for k in fields) + ", updated_at = :updated_at"

    with get_connection() as conn:
        conn.execute(text(f"UPDATE avisos SET {set_clause} WHERE id = :id"), params)
        conn.commit()
    return True


def get_sedes() -> list:
    with get_connection() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT sede FROM avisos WHERE sede IS NOT NULL AND sede != '' ORDER BY sede"
        )).fetchall()
        return [r._mapping["sede"] for r in rows]


def get_avisos_por_alertar(dias: int) -> list:
    """Avisos no cerrados con X+ días de antigüedad cuya alerta no se ha enviado."""
    field = "alerta_1mes_enviada" if dias <= 31 else "alerta_3meses_enviada"
    with get_connection() as conn:
        rows = conn.execute(text(f"""
            SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
            FROM avisos a
            LEFT JOIN users u ON a.coordinador_id = u.id
            WHERE a.estado != 'Acabado' AND a.{field} = 0
        """)).fetchall()

    resultado = []
    hoy = date.today()
    for r in rows:
        av = _row(r)
        try:
            fecha = datetime.strptime(av["fecha_solicitud"][:10], "%Y-%m-%d").date()
            if (hoy - fecha).days >= dias:
                resultado.append(av)
        except Exception:
            pass
    return resultado


def marcar_alerta_enviada(aviso_id: int, tipo: str):
    field = "alerta_1mes_enviada" if tipo == "1mes" else "alerta_3meses_enviada"
    with get_connection() as conn:
        conn.execute(text(f"UPDATE avisos SET {field} = 1 WHERE id = :id"), {"id": aviso_id})
        conn.commit()


def get_stats() -> dict:
    with get_connection() as conn:
        total      = conn.execute(text("SELECT COUNT(*) FROM avisos")).scalar()
        en_proceso = conn.execute(text("SELECT COUNT(*) FROM avisos WHERE estado='En proceso'")).scalar()
        acabado    = conn.execute(text("SELECT COUNT(*) FROM avisos WHERE estado='Acabado'")).scalar()
        falta_mat  = conn.execute(text("SELECT COUNT(*) FROM avisos WHERE estado='Falta material'")).scalar()

    # urgentes: no acabados con más de 90 días
    todos = get_all_avisos()
    hoy   = date.today()
    urgentes = 0
    for av in todos:
        if av["estado"] == "Acabado":
            continue
        try:
            fecha = datetime.strptime(av["fecha_solicitud"][:10], "%Y-%m-%d").date()
            if (hoy - fecha).days > 90:
                urgentes += 1
        except Exception:
            pass

    return {
        "total":          total or 0,
        "en_proceso":     en_proceso or 0,
        "acabado":        acabado or 0,
        "falta_material": falta_mat or 0,
        "urgentes":       urgentes,
    }
