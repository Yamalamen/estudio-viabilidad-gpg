"""
Dashboard de emergencia:
- Lee directamente la tabla avisos desde la base de datos
- No depende de services.avisos, render_filtros ni render_tabla
- Muestra los avisos importados y permite abrir uno
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


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
        database_url = os.getenv("DATABASE_URL")

    if database_url:
        return create_engine(database_url, pool_pre_ping=True)

    return create_engine("sqlite:///data/avisos.db", pool_pre_ping=True)


ENGINE = _get_engine()


def _safe(v):
    if v is None:
        return ""
    return str(v)


def _leer_avisos():
    query = """
        SELECT
            id,
            COALESCE(CAST(numero_aviso AS TEXT), CAST(num_aviso AS TEXT)) AS num_aviso,
            fecha_solicitud,
            generador_ot,
            generador_aviso,
            esm,
            COALESCE(descripcion_ot, descripcion) AS descripcion,
            sede,
            COALESCE(estado, 'Pendiente') AS estado,
            coordinador,
            coordinador_id,
            enlace_drive,
            COALESCE(material_faltante, material_necesario) AS material,
            fecha_cierre,
            created_at,
            updated_at
        FROM avisos
        ORDER BY
            fecha_solicitud DESC NULLS LAST,
            COALESCE(CAST(numero_aviso AS TEXT), CAST(num_aviso AS TEXT)) DESC
    """

    with ENGINE.begin() as conn:
        rows = conn.execute(text(query)).fetchall()

    data = []
    for r in rows:
        d = dict(r._mapping)
        data.append(d)
    return data


def _stats_desde_avisos(avisos: list[dict]) -> dict:
    total = len(avisos)
    en_proceso = len([a for a in avisos if _safe(a.get("estado")) in ["Pendiente", "En proceso"]])
    falta_material = len([a for a in avisos if _safe(a.get("estado")) == "Falta material"])
    acabado = len([a for a in avisos if _safe(a.get("estado")) == "Acabado"])

    urgentes = 0
    hoy = pd.Timestamp.today().date()
    for a in avisos:
        if _safe(a.get("estado")) == "Acabado":
            continue
        try:
            fecha = pd.to_datetime(a.get("fecha_solicitud"), errors="coerce")
            if pd.notna(fecha):
                dias = (hoy - fecha.date()).days
                if dias > 90:
                    urgentes += 1
        except Exception:
            pass

    return {
        "total": total,
        "en_proceso": en_proceso,
        "falta_material": falta_material,
        "acabado": acabado,
        "urgentes": urgentes,
    }


def render(user: dict):
    st.markdown(
        "<h1 style='color:#1E3A5F;margin-bottom:0;'>⚙️ Gestión de Avisos de Mantenimiento</h1>"
        "<p style='color:#666;margin-top:4px;'>Sedes Judiciales — Provincia de Alicante</p>",
        unsafe_allow_html=True,
    )

    try:
        avisos = _leer_avisos()
    except Exception as e:
        st.error(f"Error leyendo avisos desde base de datos: {e}")
        return

    stats = _stats_desde_avisos(avisos)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total avisos", stats["total"])
    c2.metric("🔵 En proceso", stats["en_proceso"])
    c3.metric("🟡 Falta material", stats["falta_material"])
    c4.metric("🟢 Acabados", stats["acabado"])
    c5.metric("🔴 Urgentes (+3 meses)", stats["urgentes"])

    st.markdown("---")
    st.write(f"Total avisos leídos directamente desde la base de datos: **{len(avisos)}**")

    if not avisos:
        st.warning("No hay avisos en la base de datos.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        busqueda = st.text_input("Buscar por nº aviso, sede, E.S.M. o descripción")

    with col2:
        estados = sorted(list({(_safe(a.get('estado')) or 'Pendiente') for a in avisos}))
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos"] + estados)

    with col3:
        filtro_lista = st.selectbox("Mostrar", ["En curso", "Terminados", "Todos"], index=2)

    filtrados = avisos[:]

    if filtro_estado != "Todos":
        filtrados = [a for a in filtrados if _safe(a.get("estado")) == filtro_estado]

    if filtro_lista == "En curso":
        filtrados = [a for a in filtrados if _safe(a.get("estado")) != "Acabado"]
    elif filtro_lista == "Terminados":
        filtrados = [a for a in filtrados if _safe(a.get("estado")) == "Acabado"]

    if busqueda.strip():
        q = busqueda.strip().lower()
        filtrados = [
            a for a in filtrados
            if q in _safe(a.get("num_aviso")).lower()
            or q in _safe(a.get("sede")).lower()
            or q in _safe(a.get("esm")).lower()
            or q in _safe(a.get("descripcion")).lower()
        ]

    st.write(f"Avisos visibles en dashboard: **{len(filtrados)}**")

    if not filtrados:
        st.info("No hay avisos con los filtros actuales.")
        return

    filas = []
    for a in filtrados:
        filas.append({
            "ID": a.get("id"),
            "Aviso": a.get("num_aviso"),
            "Fecha": a.get("fecha_solicitud"),
            "Sede": a.get("sede"),
            "Estado": a.get("estado"),
            "Generador OT": a.get("generador_ot"),
            "Generador Aviso": a.get("generador_aviso"),
            "E.S.M.": a.get("esm"),
            "Descripción": a.get("descripcion"),
            "Coordinador": a.get("coordinador"),
        })

    df = pd.DataFrame(filas)
    st.dataframe(df, use_container_width=True, height=550)

    st.markdown("### Abrir aviso")

    opciones = []
    mapa = {}

    for a in filtrados:
        texto = f"{_safe(a.get('num_aviso'))} | {_safe(a.get('sede'))} | {_safe(a.get('estado'))}"
        opciones.append(texto)
        mapa[texto] = a.get("id")

    seleccion = st.selectbox("Selecciona un aviso", options=opciones, key="selector_dashboard_directo")

    if st.button("📂 Abrir aviso", type="primary"):
        aviso_id = mapa.get(seleccion)
        if aviso_id:
            st.session_state["aviso_seleccionado_id"] = aviso_id
            st.session_state["page"] = "detalle_aviso"
            st.rerun()