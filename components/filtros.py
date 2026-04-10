"""
Panel de filtros en el sidebar — incluye filtro por color/urgencia.
"""
import streamlit as st
from datetime import date
from services.avisos import get_sedes
from services.users import get_coordinadores

_OPCIONES_COLOR = [
    "🔴 Rojo (más de 3 meses)",
    "🟠 Naranja (más de 2 meses)",
    "🔵 Azul (en plazo)",
    "🟢 Verde (acabado)",
]


def render_filtros(role: str = "supervisor") -> dict:
    filters = {}

    with st.sidebar:
        st.markdown("## 🔍 Filtros")

        # Búsqueda directa por Nº de aviso
        num = st.text_input("Nº Aviso (búsqueda directa)", placeholder="ej: 6291")
        if num.strip().isdigit():
            filters["num_aviso"] = int(num.strip())
            return filters  # búsqueda directa, ignorar resto

        # ── Filtro por color / urgencia ──────────────────────────────────────────
        colores_sel = st.multiselect(
            "Urgencia / color",
            options=_OPCIONES_COLOR,
            help="Filtra por antigüedad del aviso",
        )
        if colores_sel:
            filters["colores"] = colores_sel

        # Sede
        sedes = ["Todas"] + get_sedes()
        sede_sel = st.selectbox("Sede", sedes)
        if sede_sel != "Todas":
            filters["sede"] = sede_sel

        # Estado
        estados = ["Todos", "En proceso", "Acabado", "Falta material"]
        estado_sel = st.selectbox("Estado", estados)
        if estado_sel != "Todos":
            filters["estado"] = estado_sel

        # Coordinador (solo supervisores)
        if role == "supervisor":
            coords     = get_coordinadores()
            coord_opts = {"Todos": None}
            coord_opts.update({c["nombre"]: c["id"] for c in coords})
            coord_sel = st.selectbox("Coordinador asignado", list(coord_opts.keys()))
            if coord_sel != "Todos":
                filters["coordinador_id"] = coord_opts[coord_sel]

        # Rango de fechas
        st.markdown("**Rango de fechas**")
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date(2024, 1, 1), key="f_desde")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="f_hasta")
        if fecha_desde:
            filters["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filters["fecha_hasta"] = fecha_hasta

        # Generador OT
        gen_ot = st.text_input("Generador OT", placeholder="Nombre parcial...")
        if gen_ot.strip():
            filters["generador_ot"] = gen_ot.strip()

        # Generador Aviso
        gen_av = st.text_input("Generador Aviso", placeholder="Nombre parcial...")
        if gen_av.strip():
            filters["generador_aviso"] = gen_av.strip()

        # ESM
        esm_txt = st.text_input("E.S.M.", placeholder="Texto parcial del código E.S.M.")
        if esm_txt.strip():
            filters["esm"] = esm_txt.strip()

        # Descripción
        desc_txt = st.text_input("Descripción", placeholder="Texto en la descripción...")
        if desc_txt.strip():
            filters["descripcion"] = desc_txt.strip()

        if st.button("🗑️ Limpiar filtros", use_container_width=True):
            st.rerun()

    return filters
