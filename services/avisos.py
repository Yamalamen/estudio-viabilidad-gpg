"""
CRUD y consultas de avisos.
Versión unificada y compatible con Supabase/PostgreSQL.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, inspect, text


# -----------------------------------------------------------------------------
# ENGINE
# -----------------------------------------------------------------------------

def _get_engine():
    try:
        from database import db as db_module

        if hasattr(db_module, "_engine") and db_module._engine is not None:
            return db_module._engine

        if hasattr(db_module, "engine") and db_module.engine is not None:
            return db_module.engine

        if hasattr(db_module, "get_engine"):
            eng = db_module.get_engine()
            if eng is not None:
                return eng
    except Exception:
        pass

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)

    return create_engine("sqlite:///data/avisos.db", pool_pre_ping=True)


ENGINE = _get_engine()


# -----------------------------------------------------------------------------
# HELPERS DE ESQUEMA
# -----------------------------------------------------------------------------

def _has_table(table_name: str) -> bool:
    inspector = inspect(ENGINE)
    return inspector.has_table(table_name)


def _get_columns(table_name: str) -> set[str]:
    inspector = inspect(ENGINE)
    if not inspector.has_table(table_name):
        return set()
    return {c["name"] for c in inspector.get_columns(table_name)}


def _has_col(table_name: str, column_name: str) -> bool:
    return column_name in _get_columns(table_name)


def _safe_add_column(table_name: str, column_name: str, column_sql: str) -> None:
    if _has_col(table_name, column_name):
        return
    with ENGINE.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def _ensure_schema() -> None:
    if not _has_table("avisos"):
        ddl = """
        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            numero_aviso VARCHAR(100) UNIQUE NOT NULL,
            num_aviso VARCHAR(100),
            fecha_solicitud DATE NULL,
            generador_ot TEXT NULL,
            generador_aviso TEXT NULL,
            esm TEXT NULL,
            descripcion_ot TEXT NULL,
            descripcion TEXT NULL,
            sede TEXT NULL,
            estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
            coordinador VARCHAR(100) NULL,
            coordinador_id INTEGER NULL,
            comentarios TEXT NULL,
            enlace_drive TEXT NULL,
            material_faltante TEXT NULL,
            material_necesario TEXT NULL,
            fecha_cierre TIMESTAMP NULL,
            alerta_1mes_enviada BOOLEAN NOT NULL DEFAULT FALSE,
            alerta_3meses_enviada BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        with ENGINE.begin() as conn:
            conn.execute(text(ddl))
        return

    _safe_add_column("avisos", "numero_aviso", "VARCHAR(100)")
    _safe_add_column("avisos", "num_aviso", "VARCHAR(100)")
    _safe_add_column("avisos", "descripcion_ot", "TEXT")
    _safe_add_column("avisos", "descripcion", "TEXT")
    _safe_add_column("avisos", "coordinador", "VARCHAR(100)")
    _safe_add_column("avisos", "coordinador_id", "INTEGER")
    _safe_add_column("avisos", "comentarios", "TEXT")
    _safe_add_column("avisos", "enlace_drive", "TEXT")
    _safe_add_column("avisos", "material_faltante", "TEXT")
    _safe_add_column("avisos", "material_necesario", "TEXT")
    _safe_add_column("avisos", "fecha_cierre", "TIMESTAMP")
    _safe_add_column("avisos", "alerta_1mes_enviada", "BOOLEAN DEFAULT FALSE")
    _safe_add_column("avisos", "alerta_3meses_enviada", "BOOLEAN DEFAULT FALSE")
    _safe_add_column("avisos", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column("avisos", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")


# -----------------------------------------------------------------------------
# HELPERS DE NEGOCIO
# -----------------------------------------------------------------------------

def _extract_sede(esm: str) -> str:
    if not esm:
        return ""
    m = re.search(r"OBRA CIVIL\s+(.+)$", str(esm).strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip()
    if "-" in str(esm):
        return str(esm).split("-")[-1].strip()
    return str(esm).strip()


def _col_num() -> str:
    cols = _get_columns("avisos")
    return "numero_aviso" if "numero_aviso" in cols else "num_aviso"


def _col_desc() -> str:
    cols = _get_columns("avisos")
    return "descripcion_ot" if "descripcion_ot" in cols else "descripcion"


def _col_material() -> str:
    cols = _get_columns("avisos")
    return "material_faltante" if "material_faltante" in cols else "material_necesario"


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)


def _row_to_aviso(row: Any) -> Dict[str, Any]:
    d = _row_to_dict(row)
    num_aviso = d.get("numero_aviso", d.get("num_aviso"))
    descripcion = d.get("descripcion_ot", d.get("descripcion"))
    material = d.get("material_faltante", d.get("material_necesario"))

    return {
        "id": d.get("id"),
        "num_aviso": num_aviso,
        "numero_aviso": num_aviso,
        "fecha_solicitud": d.get("fecha_solicitud"),
        "generador_ot": d.get("generador_ot"),
        "generador_aviso": d.get("generador_aviso"),
        "esm": d.get("esm"),
        "sede": d.get("sede"),
        "descripcion": descripcion,
        "descripcion_ot": descripcion,
        "estado": d.get("estado") or "Pendiente",
        "coordinador_id": d.get("coordinador_id"),
        "coordinador": d.get("coordinador"),
        "coordinador_nombre": d.get("coordinador_nombre"),
        "coordinador_email": d.get("coordinador_email"),
        "enlace_drive": d.get("enlace_drive"),
        "material_necesario": material,
        "material_faltante": material,
        "fecha_cierre": d.get("fecha_cierre"),
        "alerta_1mes_enviada": d.get("alerta_1mes_enviada", False),
        "alerta_3meses_enviada": d.get("alerta_3meses_enviada", False),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def _get_user_name_by_id(user_id: Optional[int]) -> Optional[str]:
    if not user_id or not _has_table("users"):
        return None
    with ENGINE.begin() as conn:
        row = conn.execute(
            text("SELECT nombre FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
    if not row:
        return None
    return _row_to_dict(row).get("nombre")


# -----------------------------------------------------------------------------
# CRUD Y CONSULTAS
# -----------------------------------------------------------------------------

def get_all_avisos(filters: dict | None = None) -> list:
    _ensure_schema()

    num_col = _col_num()
    desc_col = _col_desc()
    material_col = _col_material()
    has_users = _has_table("users") and _has_col("avisos", "coordinador_id")

    sql = f"""
        SELECT
            a.id,
            a.{num_col} AS numero_aviso,
            a.fecha_solicitud,
            a.generador_ot,
            a.generador_aviso,
            a.esm,
            a.sede,
            a.{desc_col} AS descripcion_ot,
            a.estado,
            a.coordinador_id,
            a.coordinador,
            a.enlace_drive,
            a.{material_col} AS material_faltante,
            a.fecha_cierre,
            a.alerta_1mes_enviada,
            a.alerta_3meses_enviada,
            a.created_at,
            a.updated_at
            {", u.nombre AS coordinador_nombre, u.email AS coordinador_email" if has_users else ""}
        FROM avisos a
        {"LEFT JOIN users u ON a.coordinador_id = u.id" if has_users else ""}
        WHERE 1=1
    """
    params: dict[str, Any] = {}

    if filters:
        if filters.get("num_aviso"):
            sql += f" AND CAST(a.{num_col} AS TEXT) = :num_aviso"
            params["num_aviso"] = str(filters["num_aviso"]).strip()

        if filters.get("sede"):
            sql += " AND a.sede = :sede"
            params["sede"] = filters["sede"]

        if filters.get("estado"):
            sql += " AND a.estado = :estado"
            params["estado"] = filters["estado"]

        if filters.get("coordinador_id") and _has_col("avisos", "coordinador_id"):
            sql += " AND a.coordinador_id = :coordinador_id"
            params["coordinador_id"] = filters["coordinador_id"]

        if filters.get("fecha_desde"):
            sql += " AND CAST(a.fecha_solicitud AS DATE) >= :fecha_desde"
            params["fecha_desde"] = str(filters["fecha_desde"])

        if filters.get("fecha_hasta"):
            sql += " AND CAST(a.fecha_solicitud AS DATE) <= :fecha_hasta"
            params["fecha_hasta"] = str(filters["fecha_hasta"])

        if filters.get("generador_ot"):
            sql += " AND LOWER(COALESCE(a.generador_ot,'')) LIKE :generador_ot"
            params["generador_ot"] = f"%{str(filters['generador_ot']).lower()}%"

        if filters.get("generador_aviso"):
            sql += " AND LOWER(COALESCE(a.generador_aviso,'')) LIKE :generador_aviso"
            params["generador_aviso"] = f"%{str(filters['generador_aviso']).lower()}%"

        if filters.get("esm"):
            sql += " AND LOWER(COALESCE(a.esm,'')) LIKE :esm"
            params["esm"] = f"%{str(filters['esm']).lower()}%"

        if filters.get("descripcion"):
            sql += f" AND LOWER(COALESCE(a.{desc_col},'')) LIKE :descripcion"
            params["descripcion"] = f"%{str(filters['descripcion']).lower()}%"

        if filters.get("color"):
            color = str(filters["color"]).lower()
            if color == "rojo":
                sql += """
                    AND COALESCE(a.estado, 'Pendiente') <> 'Acabado'
                    AND a.fecha_solicitud IS NOT NULL
                    AND (CURRENT_DATE - CAST(a.fecha_solicitud AS DATE)) > 90
                """
            elif color == "naranja":
                sql += """
                    AND COALESCE(a.estado, 'Pendiente') <> 'Acabado'
                    AND a.fecha_solicitud IS NOT NULL
                    AND (CURRENT_DATE - CAST(a.fecha_solicitud AS DATE)) > 60
                    AND (CURRENT_DATE - CAST(a.fecha_solicitud AS DATE)) <= 90
                """
            elif color == "azul":
                sql += """
                    AND COALESCE(a.estado, 'Pendiente') <> 'Acabado'
                    AND (
                        a.fecha_solicitud IS NULL
                        OR (CURRENT_DATE - CAST(a.fecha_solicitud AS DATE)) <= 60
                    )
                """
            elif color == "verde":
                sql += " AND a.estado = 'Acabado'"

    sql += f" ORDER BY CAST(a.fecha_solicitud AS DATE) DESC NULLS LAST, CAST(a.{num_col} AS TEXT) DESC"

    with ENGINE.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return [_row_to_aviso(r) for r in rows]


def get_aviso_by_id(aviso_id: int) -> dict | None:
    _ensure_schema()

    num_col = _col_num()
    desc_col = _col_desc()
    material_col = _col_material()
    has_users = _has_table("users") and _has_col("avisos", "coordinador_id")

    sql = f"""
        SELECT
            a.id,
            a.{num_col} AS numero_aviso,
            a.fecha_solicitud,
            a.generador_ot,
            a.generador_aviso,
            a.esm,
            a.sede,
            a.{desc_col} AS descripcion_ot,
            a.estado,
            a.coordinador_id,
            a.coordinador,
            a.enlace_drive,
            a.{material_col} AS material_faltante,
            a.fecha_cierre,
            a.alerta_1mes_enviada,
            a.alerta_3meses_enviada,
            a.created_at,
            a.updated_at
            {", u.nombre AS coordinador_nombre, u.email AS coordinador_email" if has_users else ""}
        FROM avisos a
        {"LEFT JOIN users u ON a.coordinador_id = u.id" if has_users else ""}
        WHERE a.id = :id
    """

    with ENGINE.begin() as conn:
        row = conn.execute(text(sql), {"id": aviso_id}).fetchone()

    return _row_to_aviso(row) if row else None


def create_aviso(data: dict) -> int:
    _ensure_schema()

    num_col = _col_num()
    desc_col = _col_desc()
    material_col = _col_material()

    sede = _extract_sede(data.get("esm", ""))
    coordinador_id = data.get("coordinador_id")
    coordinador_nombre = _get_user_name_by_id(coordinador_id)

    sql = f"""
        INSERT INTO avisos (
            {num_col},
            fecha_solicitud,
            generador_ot,
            generador_aviso,
            esm,
            sede,
            {desc_col},
            estado,
            coordinador_id,
            coordinador,
            enlace_drive,
            {material_col},
            created_at,
            updated_at
        )
        VALUES (
            :num_aviso,
            :fecha_solicitud,
            :generador_ot,
            :generador_aviso,
            :esm,
            :sede,
            :descripcion,
            :estado,
            :coordinador_id,
            :coordinador,
            :enlace_drive,
            :material,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING id
    """

    params = {
        "num_aviso": str(data.get("num_aviso") or data.get("numero_aviso") or "").strip(),
        "fecha_solicitud": str(data.get("fecha_solicitud")) if data.get("fecha_solicitud") else None,
        "generador_ot": data.get("generador_ot", ""),
        "generador_aviso": data.get("generador_aviso", ""),
        "esm": data.get("esm", ""),
        "sede": sede,
        "descripcion": data.get("descripcion") or data.get("descripcion_ot") or "",
        "estado": data.get("estado", "En proceso"),
        "coordinador_id": coordinador_id,
        "coordinador": coordinador_nombre,
        "enlace_drive": data.get("enlace_drive", ""),
        "material": data.get("material_necesario") or data.get("material_faltante") or "",
    }

    with ENGINE.begin() as conn:
        row = conn.execute(text(sql), params).fetchone()

    return int(_row_to_dict(row)["id"])


def update_aviso(aviso_id: int, data: dict) -> bool:
    _ensure_schema()

    num_col = _col_num()
    desc_col = _col_desc()
    material_col = _col_material()

    if "esm" in data:
        data["sede"] = _extract_sede(data["esm"])

    fields = []
    params: dict[str, Any] = {"id": aviso_id}

    mapping = {
        "fecha_solicitud": "fecha_solicitud",
        "generador_ot": "generador_ot",
        "generador_aviso": "generador_aviso",
        "esm": "esm",
        "sede": "sede",
        "descripcion": desc_col,
        "descripcion_ot": desc_col,
        "estado": "estado",
        "coordinador_id": "coordinador_id",
        "enlace_drive": "enlace_drive",
        "material_necesario": material_col,
        "material_faltante": material_col,
        "fecha_cierre": "fecha_cierre",
        "alerta_1mes_enviada": "alerta_1mes_enviada",
        "alerta_3meses_enviada": "alerta_3meses_enviada",
        "num_aviso": num_col,
        "numero_aviso": num_col,
    }

    for key, real_col in mapping.items():
        if key in data and _has_col("avisos", real_col):
            fields.append(f"{real_col} = :{key}")
            params[key] = data[key]

    if "coordinador_id" in data and _has_col("avisos", "coordinador"):
        coord_name = _get_user_name_by_id(data.get("coordinador_id"))
        fields.append("coordinador = :coordinador_nombre_sync")
        params["coordinador_nombre_sync"] = coord_name

    if not fields:
        return False

    if _has_col("avisos", "updated_at"):
        fields.append("updated_at = CURRENT_TIMESTAMP")

    sql = f"UPDATE avisos SET {', '.join(fields)} WHERE id = :id"

    with ENGINE.begin() as conn:
        conn.execute(text(sql), params)

    return True


def get_sedes() -> list:
    _ensure_schema()

    if not _has_col("avisos", "sede"):
        return []

    with ENGINE.begin() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT sede
            FROM avisos
            WHERE sede IS NOT NULL AND TRIM(CAST(sede AS TEXT)) <> ''
            ORDER BY sede
        """)).fetchall()

    return [_row_to_dict(r).get("sede") for r in rows if _row_to_dict(r).get("sede")]


def get_avisos_por_alertar(dias: int) -> list:
    _ensure_schema()

    field = "alerta_1mes_enviada" if dias <= 31 else "alerta_3meses_enviada"
    num_col = _col_num()
    desc_col = _col_desc()
    material_col = _col_material()
    has_users = _has_table("users") and _has_col("avisos", "coordinador_id")

    sql = f"""
        SELECT
            a.id,
            a.{num_col} AS numero_aviso,
            a.fecha_solicitud,
            a.generador_ot,
            a.generador_aviso,
            a.esm,
            a.sede,
            a.{desc_col} AS descripcion_ot,
            a.estado,
            a.coordinador_id,
            a.coordinador,
            a.enlace_drive,
            a.{material_col} AS material_faltante,
            a.fecha_cierre,
            a.alerta_1mes_enviada,
            a.alerta_3meses_enviada,
            a.created_at,
            a.updated_at
            {", u.nombre AS coordinador_nombre, u.email AS coordinador_email" if has_users else ""}
        FROM avisos a
        {"LEFT JOIN users u ON a.coordinador_id = u.id" if has_users else ""}
        WHERE COALESCE(a.estado, 'Pendiente') <> 'Acabado'
          AND COALESCE(a.{field}, FALSE) = FALSE
          AND a.fecha_solicitud IS NOT NULL
          AND (CURRENT_DATE - CAST(a.fecha_solicitud AS DATE)) >= :dias
    """

    with ENGINE.begin() as conn:
        rows = conn.execute(text(sql), {"dias": dias}).fetchall()

    return [_row_to_aviso(r) for r in rows]


def marcar_alerta_enviada(aviso_id: int, tipo: str):
    _ensure_schema()

    field = "alerta_1mes_enviada" if tipo == "1mes" else "alerta_3meses_enviada"
    if not _has_col("avisos", field):
        return

    with ENGINE.begin() as conn:
        conn.execute(
            text(f"UPDATE avisos SET {field} = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": aviso_id},
        )


def get_stats() -> dict:
    _ensure_schema()

    with ENGINE.begin() as conn:
        total = conn.execute(text("""
            SELECT COUNT(*) AS n
            FROM avisos
        """)).scalar() or 0

        en_proceso = conn.execute(text("""
            SELECT COUNT(*) AS n
            FROM avisos
            WHERE COALESCE(estado, 'Pendiente') IN ('En proceso', 'Pendiente')
        """)).scalar() or 0

        acabado = conn.execute(text("""
            SELECT COUNT(*) AS n
            FROM avisos
            WHERE estado = 'Acabado'
        """)).scalar() or 0

        falta_material = conn.execute(text("""
            SELECT COUNT(*) AS n
            FROM avisos
            WHERE estado = 'Falta material'
        """)).scalar() or 0

        urgentes = conn.execute(text("""
            SELECT COUNT(*) AS n
            FROM avisos
            WHERE COALESCE(estado, 'Pendiente') <> 'Acabado'
              AND fecha_solicitud IS NOT NULL
              AND (CURRENT_DATE - CAST(fecha_solicitud AS DATE)) > 90
        """)).scalar() or 0

    return {
        "total": int(total),
        "en_proceso": int(en_proceso),
        "acabado": int(acabado),
        "falta_material": int(falta_material),
        "urgentes": int(urgentes),
    }