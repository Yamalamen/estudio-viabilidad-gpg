"""
CRUD y consultas de avisos.
"""
import re
from datetime import date, datetime
from database.db import get_connection


def _extract_sede(esm: str) -> str:
    """Extrae la sede del código ESM. Ej: 'JUSTICIA.AL.AL30.860-GENERICO OBRA CIVIL ELCHE' → 'ELCHE'"""
    if not esm:
        return ""
    m = re.search(r"OBRA CIVIL\s+(.+)$", esm.strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return esm.strip()


def get_all_avisos(filters: dict = None) -> list:
    """Devuelve todos los avisos con datos del coordinador. Acepta filtros opcionales."""
    conn = get_connection()
    c = conn.cursor()
    sql = """
        SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
        FROM avisos a
        LEFT JOIN users u ON a.coordinador_id = u.id
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get("num_aviso"):
            sql += " AND a.num_aviso = ?"
            params.append(int(filters["num_aviso"]))
        if filters.get("sede"):
            sql += " AND a.sede = ?"
            params.append(filters["sede"])
        if filters.get("estado"):
            sql += " AND a.estado = ?"
            params.append(filters["estado"])
        if filters.get("coordinador_id"):
            sql += " AND a.coordinador_id = ?"
            params.append(filters["coordinador_id"])
        if filters.get("fecha_desde"):
            sql += " AND a.fecha_solicitud >= ?"
            params.append(str(filters["fecha_desde"]))
        if filters.get("fecha_hasta"):
            sql += " AND a.fecha_solicitud <= ?"
            params.append(str(filters["fecha_hasta"]))
        if filters.get("generador_ot"):
            sql += " AND a.generador_ot LIKE ?"
            params.append(f"%{filters['generador_ot']}%")
        if filters.get("generador_aviso"):
            sql += " AND a.generador_aviso LIKE ?"
            params.append(f"%{filters['generador_aviso']}%")
        if filters.get("esm"):
            sql += " AND a.esm LIKE ?"
            params.append(f"%{filters['esm']}%")
        if filters.get("descripcion"):
            sql += " AND a.descripcion LIKE ?"
            params.append(f"%{filters['descripcion']}%")

    sql += " ORDER BY a.fecha_solicitud DESC"
    rows = c.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_aviso_by_id(aviso_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
           FROM avisos a LEFT JOIN users u ON a.coordinador_id = u.id
           WHERE a.id = ?""",
        (aviso_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_aviso(data: dict) -> int:
    conn = get_connection()
    sede = _extract_sede(data.get("esm", ""))
    c = conn.cursor()
    c.execute("""
        INSERT INTO avisos (num_aviso, fecha_solicitud, generador_ot, generador_aviso,
                            esm, sede, descripcion, estado, coordinador_id, enlace_drive)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        data["num_aviso"],
        str(data["fecha_solicitud"]),
        data.get("generador_ot", ""),
        data.get("generador_aviso", ""),
        data.get("esm", ""),
        sede,
        data.get("descripcion", ""),
        data.get("estado", "En proceso"),
        data.get("coordinador_id"),
        data.get("enlace_drive", ""),
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_aviso(aviso_id: int, data: dict) -> bool:
    conn = get_connection()
    if "esm" in data:
        data["sede"] = _extract_sede(data["esm"])

    fields = []
    params = []
    allowed = [
        "fecha_solicitud", "generador_ot", "generador_aviso", "esm", "sede",
        "descripcion", "estado", "coordinador_id", "enlace_drive",
        "material_necesario", "fecha_cierre",
        "alerta_1mes_enviada", "alerta_3meses_enviada"
    ]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            params.append(data[key])

    if not fields:
        conn.close()
        return False

    fields.append("updated_at = datetime('now','localtime')")
    params.append(aviso_id)
    conn.execute(f"UPDATE avisos SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


def get_sedes() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT sede FROM avisos WHERE sede IS NOT NULL AND sede != '' ORDER BY sede"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_avisos_por_alertar(dias: int) -> list:
    """Avisos no cerrados con X+ días de antigüedad cuya alerta no se ha enviado."""
    field = "alerta_1mes_enviada" if dias <= 31 else "alerta_3meses_enviada"
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT a.*, u.nombre AS coordinador_nombre, u.email AS coordinador_email
        FROM avisos a
        LEFT JOIN users u ON a.coordinador_id = u.id
        WHERE a.estado != 'Acabado'
          AND a.{field} = 0
          AND julianday('now') - julianday(a.fecha_solicitud) >= ?
    """, (dias,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def marcar_alerta_enviada(aviso_id: int, tipo: str):
    field = "alerta_1mes_enviada" if tipo == "1mes" else "alerta_3meses_enviada"
    conn = get_connection()
    conn.execute(f"UPDATE avisos SET {field} = 1 WHERE id = ?", (aviso_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()
    total      = c.execute("SELECT COUNT(*) FROM avisos").fetchone()[0]
    en_proceso = c.execute("SELECT COUNT(*) FROM avisos WHERE estado='En proceso'").fetchone()[0]
    acabado    = c.execute("SELECT COUNT(*) FROM avisos WHERE estado='Acabado'").fetchone()[0]
    falta_mat  = c.execute("SELECT COUNT(*) FROM avisos WHERE estado='Falta material'").fetchone()[0]
    urgentes   = c.execute(
        "SELECT COUNT(*) FROM avisos WHERE estado!='Acabado' AND julianday('now')-julianday(fecha_solicitud)>90"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "en_proceso": en_proceso,
        "acabado": acabado,
        "falta_material": falta_mat,
        "urgentes": urgentes,
    }
