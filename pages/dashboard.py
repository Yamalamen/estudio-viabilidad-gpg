"""
Dashboard simplificado y robusto.
Lee directamente los avisos y los muestra sin depender de componentes
que puedan estar ocultando o filtrando registros.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from services.avisos import get_all_avisos, get_stats
from services.excel_sync import generate_excel


def _safe_text(v):
    if v is None:
        return ""
    return str(v)


def render(user: dict):
    st.markdown(
        "<h1 style='color:#1E3A5F;margin-bottom:0;'>⚙️ Gestión de Avisos de Mantenimiento</h1>"
        "<p style='color:#666;margin-top:4px;'>Sedes Judiciales — Provincia de Alicante</p>",
        unsafe_allow_html=True,
    )

    # ── Métricas ───────────────────────────────────────────────────────────────
    stats = get_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total avisos", stats["total"])
    c2.metric("🔵 En proceso", stats["en_proceso"])
    c3.metric("🟡 Falta material", stats["falta_material"])
    c4.metric("🟢 Acabados", stats["acabado"])
    c5.metric("🔴 Urgentes (+3 meses)", stats["urgentes"])

    st.markdown("---")

    # ── Descargar Excel ────────────────────────────────────────────────────────
    excel_bytes = generate_excel()
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        label="📥 Descargar Excel",
        data=excel_bytes,
        file_name=f"avisos_mantenimiento_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

    st.markdown("---")

    # ── Leer todos los avisos SIN filtros ocultos ─────────────────────────────
    avisos_todos = get_all_avisos(filters={})

    st.write(f"Total avisos recibidos por el dashboard: **{len(avisos_todos)}**")

    if not avisos_todos:
        st.warning("No hay avisos para mostrar.")
        return

    # ── Filtros simples y visibles ────────────────────────────────────────────
    colf1, colf2, colf3 = st.columns(3)

    with colf1:
        busqueda = st.text_input("Buscar por nº aviso, sede, E.S.M. o descripción")

    with colf2:
        estados_disponibles = sorted(
            list({(_safe_text(a.get("estado")) or "Pendiente") for a in avisos_todos})
        )
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos"] + estados_disponibles)

    with colf3:
        filtro_lista = st.selectbox("Mostrar", ["En curso", "Terminados", "Todos"], index=0)

    avisos_filtrados = avisos_todos[:]

    if filtro_estado != "Todos":
        avisos_filtrados = [
            a for a in avisos_filtrados
            if _safe_text(a.get("estado")) == filtro_estado
        ]

    if filtro_lista == "En curso":
        avisos_filtrados = [
            a for a in avisos_filtrados
            if _safe_text(a.get("estado")) != "Acabado"
        ]
    elif filtro_lista == "Terminados":
        avisos_filtrados = [
            a for a in avisos_filtrados
            if _safe_text(a.get("estado")) == "Acabado"
        ]

    if busqueda.strip():
        q = busqueda.strip().lower()
        avisos_filtrados = [
            a for a in avisos_filtrados
            if q in _safe_text(a.get("num_aviso")).lower()
            or q in _safe_text(a.get("numero_aviso")).lower()
            or q in _safe_text(a.get("sede")).lower()
            or q in _safe_text(a.get("esm")).lower()
            or q in _safe_text(a.get("descripcion")).lower()
            or q in _safe_text(a.get("descripcion_ot")).lower()
        ]

    st.write(f"Avisos visibles: **{len(avisos_filtrados)}**")

    if not avisos_filtrados:
        st.info("No hay avisos con los filtros actuales.")
        return

    # ── Preparar tabla visible ────────────────────────────────────────────────
    filas = []
    for a in avisos_filtrados:
        filas.append({
            "ID": a.get("id"),
            "Aviso": a.get("num_aviso") or a.get("numero_aviso"),
            "Fecha": a.get("fecha_solicitud"),
            "Sede": a.get("sede"),
            "Estado": a.get("estado"),
            "Coordinador": a.get("coordinador_nombre") or a.get("coordinador") or "",
            "E.S.M.": a.get("esm"),
            "Descripción": a.get("descripcion") or a.get("descripcion_ot") or "",
        })

    df = pd.DataFrame(filas)

    st.dataframe(df, use_container_width=True, height=500)

    # ── Selector de aviso ─────────────────────────────────────────────────────
    st.markdown("### Abrir aviso")

    opciones = []
    mapa = {}

    for a in avisos_filtrados:
        aviso_num = a.get("num_aviso") or a.get("numero_aviso") or ""
        sede = a.get("sede") or ""
        estado = a.get("estado") or ""
        texto = f"{aviso_num} | {sede} | {estado}"
        opciones.append(texto)
        mapa[texto] = a.get("id")

    seleccion = st.selectbox("Selecciona un aviso", options=opciones)

    if st.button("📂 Abrir aviso", type="primary"):
        aviso_id = mapa.get(seleccion)
        if aviso_id:
            st.session_state["aviso_seleccionado_id"] = aviso_id
            st.session_state["page"] = "detalle_aviso"
            st.rerun()