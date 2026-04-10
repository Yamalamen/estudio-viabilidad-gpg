"""
Página principal: Dashboard con métricas, filtros y tabla de avisos.
Dos pestañas: En curso / Terminados.
"""
import streamlit as st
from services.avisos import get_all_avisos, get_stats
from services.excel_sync import generate_excel
from components.filtros import render_filtros
from components.tabla_avisos import render_tabla
from components.notif_badge import render_notif_badge
from datetime import datetime


def render(user: dict):
    st.markdown(
        "<h1 style='color:#1E3A5F;margin-bottom:0;'>⚙️ Gestión de Avisos de Mantenimiento</h1>"
        "<p style='color:#666;margin-top:4px;'>Sedes Judiciales — Provincia de Alicante</p>",
        unsafe_allow_html=True,
    )

    # ── Métricas ─────────────────────────────────────────────────────────────────
    stats = get_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total avisos",        stats["total"])
    c2.metric("🔵 En proceso",           stats["en_proceso"])
    c3.metric("🟡 Falta material",       stats["falta_material"])
    c4.metric("🟢 Acabados",             stats["acabado"])
    c5.metric("🔴 Urgentes (+3 meses)",  stats["urgentes"])

    st.markdown("---")

    # ── Leyenda de colores ────────────────────────────────────────────────────────
    with st.expander("🎨 Leyenda de colores", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(
            "<div style='background:#FFC7CE;padding:8px;border-radius:4px;text-align:center;'>"
            "<b>🔴 Rojo</b><br>Más de 3 meses</div>", unsafe_allow_html=True)
        col2.markdown(
            "<div style='background:#FFD966;padding:8px;border-radius:4px;text-align:center;'>"
            "<b>🟠 Naranja</b><br>Más de 2 meses</div>", unsafe_allow_html=True)
        col3.markdown(
            "<div style='background:#BDD7EE;padding:8px;border-radius:4px;text-align:center;'>"
            "<b>🔵 Azul</b><br>Dentro del plazo</div>", unsafe_allow_html=True)
        col4.markdown(
            "<div style='background:#C6EFCE;padding:8px;border-radius:4px;text-align:center;'>"
            "<b>🟢 Verde</b><br>Acabado/Cerrado</div>", unsafe_allow_html=True)

    # ── Sidebar: notificaciones + filtros + acciones ──────────────────────────────
    render_notif_badge(user["id"])
    filters = render_filtros(role=user["role"])

    with st.sidebar:
        st.divider()
        if user["role"] == "supervisor":
            if st.button("➕ Nuevo aviso", use_container_width=True, type="primary"):
                st.session_state["page"] = "crear_aviso"
                st.rerun()

        excel_bytes = generate_excel()
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="📥 Descargar Excel",
            data=excel_bytes,
            file_name=f"avisos_mantenimiento_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Obtener avisos y separar ──────────────────────────────────────────────────
    avisos_todos = get_all_avisos(filters=filters)
    en_curso     = [a for a in avisos_todos if a["estado"] != "Acabado"]
    terminados   = [a for a in avisos_todos if a["estado"] == "Acabado"]

    # ── Pestañas ──────────────────────────────────────────────────────────────────
    tab_curso, tab_term = st.tabs([
        f"📋 En curso  ({len(en_curso)})",
        f"✅ Terminados  ({len(terminados)})",
    ])

    with tab_curso:
        if en_curso:
            st.caption("Haz clic en un aviso del desplegable y pulsa 'Abrir aviso' para cambiar su estado.")
        selected = render_tabla(en_curso, key_suffix="curso")
        if selected:
            st.session_state["aviso_seleccionado_id"] = selected["id"]
            st.session_state["page"] = "detalle_aviso"
            st.rerun()

    with tab_term:
        if terminados:
            st.caption("Avisos marcados como Acabado/Cerrado.")
        selected = render_tabla(terminados, key_suffix="term")
        if selected:
            st.session_state["aviso_seleccionado_id"] = selected["id"]
            st.session_state["page"] = "detalle_aviso"
            st.rerun()
