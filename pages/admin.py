"""
Página de Administración
- Importar Excel de avisos
- Exportar avisos a Excel
- Ver resumen rápido

Versión de IMPORTACIÓN TOTAL:
- Lee el Excel de forma robusta
- Permite vaciar la tabla y reimportar desde cero
- Inserta fila a fila
- Verifica cuántos registros quedan realmente en la BD
"""

from __future__ import annotations

from io import BytesIO
from datetime import datetime, date
from typing import Optional, List, Any

import pandas as pd
import streamlit as st
from sqlalchemy import text, inspect, create_engine


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

    database_url = None
    try:
        database_url = st.secrets.get("DATABASE_URL", None)
    except Exception:
        pass

    if not database_url:
        import os
        database_url = os.getenv("DATABASE_URL")

    if database_url:
        return create_engine(database_url, pool_pre_ping=True)

    return create_engine("sqlite:///data/avisos.db", pool_pre_ping=True)


ENGINE = _get_engine()


# -----------------------------------------------------------------------------
# SCHEMA
# -----------------------------------------------------------------------------

def _ensure_schema() -> None:
    inspector = inspect(ENGINE)
    if inspector.has_table("avisos"):
        return

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
    );
    """
    with ENGINE.begin() as conn:
        conn.execute(text(ddl))


def _count_avisos() -> int:
    _ensure_schema()
    with ENGINE.begin() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM avisos")).scalar() or 0)


def _vaciar_tabla_avisos() -> None:
    _ensure_schema()
    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM avisos"))


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def _clean_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _parse_fecha(value) -> Optional[date]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    s = str(value).strip()
    if not s:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _extraer_sede(esm: str) -> str:
    esm = _clean_str(esm)
    if not esm:
        return ""

    if "-" in esm:
        parte = esm.split("-")[-1].strip()
        if parte:
            return parte

    return esm


def _looks_like_header_row(values: List[Any]) -> bool:
    txt = " | ".join([_clean_str(v).lower() for v in values if _clean_str(v)])
    pistas = [
        "aviso",
        "fecha",
        "solicitud",
        "generador",
        "ot",
        "e.s.m",
        "esm",
        "descripción",
        "descripcion",
    ]
    hits = sum(1 for p in pistas if p in txt)
    return hits >= 3


def _find_header_row(df_raw: pd.DataFrame) -> int:
    max_scan = min(len(df_raw), 15)
    for i in range(max_scan):
        fila = df_raw.iloc[i].tolist()
        if _looks_like_header_row(fila):
            return i
    return 0


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}

    for col in df.columns:
        c = str(col).strip().lower()

        if c in ["aviso", "nº", "nº aviso", "n° aviso", "numero aviso", "número aviso", "num aviso"]:
            mapping[col] = "numero_aviso"
        elif c in ["fecha de solicitud", "fecha solicitud", "fecha"]:
            mapping[col] = "fecha_solicitud"
        elif c in ["generador ot", "generador de ot"]:
            mapping[col] = "generador_ot"
        elif c in ["generador aviso", "generador de aviso"]:
            mapping[col] = "generador_aviso"
        elif c in ["e.s.m.", "e.s.m", "esm"]:
            mapping[col] = "esm"
        elif c in ["descripción de la ot", "descripcion de la ot", "descripcion ot", "descripción ot"]:
            mapping[col] = "descripcion_ot"

    df = df.rename(columns=mapping)

    cols = list(df.columns)

    if "numero_aviso" not in df.columns and len(cols) >= 1:
        df = df.rename(columns={cols[0]: "numero_aviso"})
        cols = list(df.columns)
    if "fecha_solicitud" not in df.columns and len(cols) >= 2:
        df = df.rename(columns={cols[1]: "fecha_solicitud"})
        cols = list(df.columns)
    if "generador_ot" not in df.columns and len(cols) >= 3:
        df = df.rename(columns={cols[2]: "generador_ot"})
        cols = list(df.columns)
    if "generador_aviso" not in df.columns and len(cols) >= 4:
        df = df.rename(columns={cols[3]: "generador_aviso"})
        cols = list(df.columns)
    if "esm" not in df.columns and len(cols) >= 5:
        df = df.rename(columns={cols[4]: "esm"})
        cols = list(df.columns)
    if "descripcion_ot" not in df.columns and len(cols) >= 6:
        df = df.rename(columns={cols[5]: "descripcion_ot"})

    required = ["numero_aviso", "fecha_solicitud", "generador_ot", "generador_aviso", "esm", "descripcion_ot"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el Excel: {', '.join(missing)}")

    return df


def _leer_excel_robusto(uploaded_file) -> pd.DataFrame:
    contenido = BytesIO(uploaded_file.getvalue())

    df_raw = pd.read_excel(contenido, header=None)
    if df_raw.empty:
        return df_raw

    header_row = _find_header_row(df_raw)

    contenido.seek(0)
    df = pd.read_excel(contenido, header=header_row)

    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    if len(df) > 0:
        primera_col = str(df.columns[0]).strip().lower()
        mask_header_repeat = df.iloc[:, 0].astype(str).str.strip().str.lower() == primera_col
        df = df[~mask_header_repeat]

    df = _normalizar_columnas(df)

    df["numero_aviso"] = df["numero_aviso"].apply(_clean_str)
    df = df[df["numero_aviso"] != ""]
    df = df[df["numero_aviso"].str.lower() != "aviso"]

    df = df.drop_duplicates(subset=["numero_aviso"], keep="first")

    return df


# -----------------------------------------------------------------------------
# IMPORTACIÓN
# -----------------------------------------------------------------------------

def _insertar_fila(row) -> None:
    numero_aviso = _clean_str(row.get("numero_aviso"))
    if not numero_aviso:
        raise ValueError("Número de aviso vacío.")

    fecha_solicitud = _parse_fecha(row.get("fecha_solicitud"))
    generador_ot = _clean_str(row.get("generador_ot"))
    generador_aviso = _clean_str(row.get("generador_aviso"))
    esm = _clean_str(row.get("esm"))
    descripcion_ot = _clean_str(row.get("descripcion_ot"))
    sede = _extraer_sede(esm)

    with ENGINE.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO avisos (
                    numero_aviso,
                    num_aviso,
                    fecha_solicitud,
                    generador_ot,
                    generador_aviso,
                    esm,
                    descripcion_ot,
                    descripcion,
                    sede,
                    estado,
                    created_at,
                    updated_at
                )
                VALUES (
                    :numero_aviso,
                    :num_aviso,
                    :fecha_solicitud,
                    :generador_ot,
                    :generador_aviso,
                    :esm,
                    :descripcion_ot,
                    :descripcion,
                    :sede,
                    'Pendiente',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
            """),
            {
                "numero_aviso": numero_aviso,
                "num_aviso": numero_aviso,
                "fecha_solicitud": fecha_solicitud,
                "generador_ot": generador_ot,
                "generador_aviso": generador_aviso,
                "esm": esm,
                "descripcion_ot": descripcion_ot,
                "descripcion": descripcion_ot,
                "sede": sede,
            },
        )


def _reimportar_desde_cero(uploaded_file) -> dict:
    _ensure_schema()

    df = _leer_excel_robusto(uploaded_file)

    if df.empty:
        return {
            "leidos_excel": 0,
            "insertados": 0,
            "errores": ["El Excel está vacío o no se ha podido interpretar."],
            "total_bd": _count_avisos(),
        }

    _vaciar_tabla_avisos()

    insertados = 0
    errores = []

    for idx, row in df.iterrows():
        try:
            _insertar_fila(row)
            insertados += 1
        except Exception as e:
            errores.append(f"Fila {idx + 1} | Aviso {_clean_str(row.get('numero_aviso'))}: {str(e)}")

    total_bd = _count_avisos()

    return {
        "leidos_excel": len(df),
        "insertados": insertados,
        "errores": errores,
        "total_bd": total_bd,
    }


# -----------------------------------------------------------------------------
# EXPORTACIÓN / RESUMEN
# -----------------------------------------------------------------------------

def _leer_avisos_df() -> pd.DataFrame:
    _ensure_schema()

    query = """
        SELECT
            COALESCE(CAST(numero_aviso AS TEXT), CAST(num_aviso AS TEXT)) AS "Aviso",
            fecha_solicitud AS "Fecha de solicitud",
            generador_ot AS "Generador OT",
            generador_aviso AS "Generador Aviso",
            esm AS "E.S.M.",
            COALESCE(descripcion_ot, descripcion) AS "Descripción de la OT",
            sede AS "Sede",
            COALESCE(estado, 'Pendiente') AS "Estado",
            coordinador AS "Coordinador",
            comentarios AS "Comentarios",
            enlace_drive AS "Enlace Drive",
            COALESCE(material_faltante, material_necesario) AS "Material faltante",
            fecha_cierre AS "Fecha cierre",
            created_at AS "Creado",
            updated_at AS "Actualizado"
        FROM avisos
        ORDER BY
            fecha_solicitud DESC NULLS LAST,
            COALESCE(CAST(numero_aviso AS TEXT), CAST(num_aviso AS TEXT)) DESC
    """
    return pd.read_sql(text(query), ENGINE)


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Avisos")
    output.seek(0)
    return output.read()


def _resumen() -> dict:
    _ensure_schema()

    with ENGINE.begin() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM avisos")).scalar() or 0
        pendientes = conn.execute(
            text("SELECT COUNT(*) FROM avisos WHERE COALESCE(estado, 'Pendiente') <> 'Acabado'")
        ).scalar() or 0
        acabados = conn.execute(
            text("SELECT COUNT(*) FROM avisos WHERE estado = 'Acabado'")
        ).scalar() or 0
        falta_material = conn.execute(
            text("SELECT COUNT(*) FROM avisos WHERE estado = 'Falta material'")
        ).scalar() or 0

    return {
        "total": int(total),
        "pendientes": int(pendientes),
        "acabados": int(acabados),
        "falta_material": int(falta_material),
    }


# -----------------------------------------------------------------------------
# RENDER
# -----------------------------------------------------------------------------

def render(user: dict) -> None:
    if user.get("role") != "supervisor":
        st.error("No tienes permisos para acceder a Administración.")
        return

    _ensure_schema()

    st.title("⚙️ Administración")
    st.caption("Importación, exportación y control general de avisos.")

    resumen = _resumen()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total avisos", resumen["total"])
    c2.metric("Pendientes", resumen["pendientes"])
    c3.metric("Acabados", resumen["acabados"])
    c4.metric("Falta material", resumen["falta_material"])

    tab1, tab2, tab3 = st.tabs(["📥 Importar Excel", "📤 Exportar Excel", "🔎 Vista rápida"])

    with tab1:
        st.subheader("Reimportar Excel desde cero")
        st.warning("Esta acción vacía la tabla de avisos y vuelve a cargar todo el Excel desde cero.")

        uploaded = st.file_uploader(
            "Selecciona el Excel",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
            key="excel_import_admin_total",
        )

        if uploaded is not None:
            try:
                preview_df = _leer_excel_robusto(uploaded)
                st.write(f"Filas útiles detectadas en el Excel: **{len(preview_df)}**")
                st.dataframe(preview_df, use_container_width=True, height=500)
            except Exception as e:
                st.error(f"No se pudo interpretar el Excel: {e}")

        if uploaded is not None and st.button("🚨 VACIAR TABLA E IMPORTAR TODO", type="primary"):
            try:
                resultado = _reimportar_desde_cero(uploaded)

                st.success(
                    f"Reimportación terminada. "
                    f"Leídos en Excel: {resultado['leidos_excel']} | "
                    f"Insertados: {resultado['insertados']} | "
                    f"Total real en BD: {resultado['total_bd']}"
                )

                if resultado["errores"]:
                    with st.expander(f"Ver errores ({len(resultado['errores'])})", expanded=True):
                        for err in resultado["errores"]:
                            st.write(f"- {err}")

                st.rerun()

            except Exception as e:
                st.error(f"Error al reimportar: {e}")

    with tab2:
        st.subheader("Exportar avisos a Excel")
        try:
            df_export = _leer_avisos_df()
            st.write(f"Total avisos en base de datos: **{len(df_export)}**")
            st.dataframe(df_export, use_container_width=True, height=500)

            excel_bytes = _to_excel_bytes(df_export)
            st.download_button(
                "📤 Descargar Excel de avisos",
                data=excel_bytes,
                file_name=f"avisos_mantenimiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"No se pudo preparar la exportación: {e}")

    with tab3:
        st.subheader("Vista rápida")
        try:
            df = _leer_avisos_df()
            st.write(f"Total avisos visibles en administración: **{len(df)}**")
            st.dataframe(df, use_container_width=True, height=500)
        except Exception as e:
            st.error(f"No se pudo cargar la vista rápida: {e}")