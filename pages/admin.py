"""
Página de Administración
- Importar Excel de avisos
- Exportar avisos a Excel
- Ver resumen rápido

Compatible con PostgreSQL/Supabase vía SQLAlchemy.
No usa conn.cursor().
"""

from __future__ import annotations

from io import BytesIO
from datetime import datetime, date
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import text, inspect, create_engine

# -----------------------------------------------------------------------------
# ENGINE
# -----------------------------------------------------------------------------

def _get_engine():
    """
    Intenta reutilizar el engine principal del proyecto.
    Si no puede, crea uno desde DATABASE_URL o SQLite local como último recurso.
    """
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

    database_url = st.secrets.get("DATABASE_URL", None)
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
    """
    Crea la tabla de avisos si no existe.
    No rompe si ya existe.
    """
    inspector = inspect(ENGINE)
    if inspector.has_table("avisos"):
        return

    ddl = """
    CREATE TABLE IF NOT EXISTS avisos (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        numero_aviso VARCHAR(100) UNIQUE NOT NULL,
        fecha_solicitud DATE NULL,
        generador_ot TEXT NULL,
        generador_aviso TEXT NULL,
        esm TEXT NULL,
        descripcion_ot TEXT NULL,
        sede TEXT NULL,
        estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
        coordinador VARCHAR(100) NULL,
        comentarios TEXT NULL,
        enlace_drive TEXT NULL,
        material_faltante TEXT NULL,
        fecha_cierre TIMESTAMP NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    with ENGINE.begin() as conn:
        conn.execute(text(ddl))


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def _clean_str(value) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_fecha(value) -> Optional[date]:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    try:
        parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _extraer_sede(esm: str) -> str:
    """
    Intenta sacar la sede desde el texto E.S.M.
    Si no puede, deja el mismo valor.
    """
    esm = _clean_str(esm)
    if not esm:
        return ""

    # Ejemplo habitual:
    # JUSTICIA.AL.AL03.860-GENERICO OBRA CIVIL AGUILERA 53
    if "-" in esm:
        parte = esm.split("-")[-1].strip()
        return parte

    return esm


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Acepta nombres variados y los traduce a columnas internas estándar.
    """
    mapping = {}

    for col in df.columns:
        c = str(col).strip().lower()

        if c in ["aviso", "nº aviso", "n° aviso", "numero aviso", "número aviso", "num aviso"]:
            mapping[col] = "numero_aviso"
        elif c in ["fecha de solicitud", "fecha solicitud", "fecha"]:
            mapping[col] = "fecha_solicitud"
        elif c in ["generador ot", "generador de ot"]:
            mapping[col] = "generador_ot"
        elif c in ["generador aviso", "generador de aviso"]:
            mapping[col] = "generador_aviso"
        elif c in ["e.s.m.", "esm", "e.s.m"]:
            mapping[col] = "esm"
        elif c in ["descripción de la ot", "descripcion de la ot", "descripcion ot", "descripción ot"]:
            mapping[col] = "descripcion_ot"

    df = df.rename(columns=mapping)

    # Si el Excel viene exactamente por posición y no por nombre, intenta rescatarlo
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
        raise ValueError(
            f"Faltan columnas obligatorias en el Excel: {', '.join(missing)}"
        )

    return df


def _table_has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(ENGINE)
    cols = inspector.get_columns(table_name)
    return any(c["name"] == column_name for c in cols)


# -----------------------------------------------------------------------------
# IMPORTACIÓN
# -----------------------------------------------------------------------------

def _importar_desde_buffer(uploaded_file) -> dict:
    """
    Importa avisos desde un Excel subido a Streamlit.
    No usa cursor(); trabaja con SQLAlchemy.
    """
    _ensure_schema()

    contenido = BytesIO(uploaded_file.getvalue())
    df = pd.read_excel(contenido)

    if df.empty:
        return {
            "insertados": 0,
            "actualizados": 0,
            "omitidos": 0,
            "errores": ["El Excel está vacío."],
        }

    df = _normalizar_columnas(df)
    df = df.dropna(how="all")

    insertados = 0
    actualizados = 0
    omitidos = 0
    errores: list[str] = []

    with ENGINE.begin() as conn:
        for idx, row in df.iterrows():
            try:
                numero_aviso = _clean_str(row.get("numero_aviso"))
                if not numero_aviso:
                    omitidos += 1
                    continue

                fecha_solicitud = _parse_fecha(row.get("fecha_solicitud"))
                generador_ot = _clean_str(row.get("generador_ot"))
                generador_aviso = _clean_str(row.get("generador_aviso"))
                esm = _clean_str(row.get("esm"))
                descripcion_ot = _clean_str(row.get("descripcion_ot"))
                sede = _extraer_sede(esm)

                existente = conn.execute(
                    text("SELECT id FROM avisos WHERE numero_aviso = :numero_aviso"),
                    {"numero_aviso": numero_aviso},
                ).fetchone()

                if existente:
                    conn.execute(
                        text("""
                            UPDATE avisos
                            SET
                                fecha_solicitud = :fecha_solicitud,
                                generador_ot = :generador_ot,
                                generador_aviso = :generador_aviso,
                                esm = :esm,
                                descripcion_ot = :descripcion_ot,
                                sede = :sede,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE numero_aviso = :numero_aviso
                        """),
                        {
                            "numero_aviso": numero_aviso,
                            "fecha_solicitud": fecha_solicitud,
                            "generador_ot": generador_ot,
                            "generador_aviso": generador_aviso,
                            "esm": esm,
                            "descripcion_ot": descripcion_ot,
                            "sede": sede,
                        },
                    )
                    actualizados += 1
                else:
                    conn.execute(
                        text("""
                            INSERT INTO avisos (
                                numero_aviso,
                                fecha_solicitud,
                                generador_ot,
                                generador_aviso,
                                esm,
                                descripcion_ot,
                                sede,
                                estado,
                                created_at,
                                updated_at
                            )
                            VALUES (
                                :numero_aviso,
                                :fecha_solicitud,
                                :generador_ot,
                                :generador_aviso,
                                :esm,
                                :descripcion_ot,
                                :sede,
                                'Pendiente',
                                CURRENT_TIMESTAMP,
                                CURRENT_TIMESTAMP
                            )
                        """),
                        {
                            "numero_aviso": numero_aviso,
                            "fecha_solicitud": fecha_solicitud,
                            "generador_ot": generador_ot,
                            "generador_aviso": generador_aviso,
                            "esm": esm,
                            "descripcion_ot": descripcion_ot,
                            "sede": sede,
                        },
                    )
                    insertados += 1

            except Exception as e:
                errores.append(f"Fila {idx + 2}: {str(e)}")

    return {
        "insertados": insertados,
        "actualizados": actualizados,
        "omitidos": omitidos,
        "errores": errores,
    }


# -----------------------------------------------------------------------------
# EXPORTACIÓN
# -----------------------------------------------------------------------------

def _leer_avisos_df() -> pd.DataFrame:
    _ensure_schema()

    query = """
        SELECT
            numero_aviso AS "Aviso",
            fecha_solicitud AS "Fecha de solicitud",
            generador_ot AS "Generador OT",
            generador_aviso AS "Generador Aviso",
            esm AS "E.S.M.",
            descripcion_ot AS "Descripción de la OT",
            sede AS "Sede",
            estado AS "Estado",
            coordinador AS "Coordinador",
            comentarios AS "Comentarios",
            enlace_drive AS "Enlace Drive",
            material_faltante AS "Material faltante",
            fecha_cierre AS "Fecha cierre",
            created_at AS "Creado",
            updated_at AS "Actualizado"
        FROM avisos
        ORDER BY
            CASE WHEN fecha_solicitud IS NULL THEN 1 ELSE 0 END,
            fecha_solicitud DESC,
            numero_aviso DESC
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
        st.subheader("Importar avisos desde Excel")
        st.write(
            "Sube el Excel original con las columnas del aviso. "
            "Si un aviso ya existe, se actualizan sus datos base sin borrar el resto del seguimiento."
        )

        uploaded = st.file_uploader(
            "Selecciona el Excel",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
            key="excel_import_admin",
        )

        if uploaded is not None:
            try:
                preview_df = pd.read_excel(BytesIO(uploaded.getvalue()))
                st.markdown("**Vista previa**")
                st.dataframe(preview_df.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"No se pudo leer el Excel: {e}")

        if uploaded is not None and st.button("✅ Importar todos los avisos", type="primary"):
            try:
                resultado = _importar_desde_buffer(uploaded)

                st.success(
                    f"Importación terminada. "
                    f"Insertados: {resultado['insertados']} | "
                    f"Actualizados: {resultado['actualizados']} | "
                    f"Omitidos: {resultado['omitidos']}"
                )

                if resultado["errores"]:
                    with st.expander(f"Ver errores ({len(resultado['errores'])})"):
                        for err in resultado["errores"]:
                            st.write(f"- {err}")

                st.rerun()

            except Exception as e:
                st.error(f"Error al importar: {e}")

    with tab2:
        st.subheader("Exportar avisos a Excel")

        try:
            df_export = _leer_avisos_df()
            st.dataframe(df_export.head(25), use_container_width=True)

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

            filtro_estado = st.selectbox(
                "Filtrar por estado",
                options=["Todos"] + sorted([x for x in df["Estado"].dropna().unique().tolist() if str(x).strip()]),
                index=0,
            )

            busqueda = st.text_input("Buscar por Nº de aviso, sede, E.S.M. o descripción")

            if filtro_estado != "Todos":
                df = df[df["Estado"] == filtro_estado]

            if busqueda.strip():
                q = busqueda.strip().lower()
                mask = (
                    df["Aviso"].astype(str).str.lower().str.contains(q, na=False)
                    | df["Sede"].astype(str).str.lower().str.contains(q, na=False)
                    | df["E.S.M."].astype(str).str.lower().str.contains(q, na=False)
                    | df["Descripción de la OT"].astype(str).str.lower().str.contains(q, na=False)
                )
                df = df[mask]

            st.dataframe(df, use_container_width=True, height=500)

        except Exception as e:
            st.error(f"No se pudo cargar la vista rápida: {e}")