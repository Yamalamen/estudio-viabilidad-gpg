"""
Formulario para crear un nuevo aviso (solo supervisores).
"""
import streamlit as st
from datetime import date
from services.avisos import create_aviso, get_all_avisos
import re


def _extract_sede(esm: str) -> str:
    m = re.search(r"OBRA CIVIL\s+(.+)$", esm.strip(), re.IGNORECASE)
    return m.group(1).strip() if m else ""


def render(user: dict):
    if user["role"] != "supervisor":
        st.error("No tienes permisos para crear avisos.")
        return

    col_back, col_title = st.columns([1, 9])
    with col_back:
        if st.button("⬅️ Volver"):
            st.session_state["page"] = "dashboard"
            st.rerun()
    with col_title:
        st.markdown("<h2 style='color:#1E3A5F;'>➕ Nuevo Aviso</h2>", unsafe_allow_html=True)

    st.divider()

    # Sugerir el siguiente número de aviso
    todos = get_all_avisos()
    max_num = max((a["num_aviso"] for a in todos), default=0) + 1

    with st.form("form_crear_aviso", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            num_aviso = st.number_input(
                "Nº Aviso *",
                min_value=1,
                value=max_num,
                help="Número único del aviso (según numeración del sistema JUSTICIA)",
            )
            fecha_solicitud = st.date_input("Fecha de solicitud *", value=date.today())
            generador_ot    = st.text_input("Generador OT", placeholder="Nombre del generador OT")
            generador_aviso = st.text_input("Generador Aviso", placeholder="Nombre del generador del aviso")

        with col2:
            esm = st.text_input(
                "E.S.M. *",
                placeholder="JUSTICIA.AL.AL30.860-GENERICO OBRA CIVIL ELCHE",
                help="Código del servicio de mantenimiento. La sede se extrae automáticamente.",
            )
            if esm:
                sede_preview = _extract_sede(esm)
                if sede_preview:
                    st.success(f"📍 Sede detectada: **{sede_preview}**")
            enlace_drive = st.text_input("🔗 Enlace Google Drive", placeholder="https://drive.google.com/...")

        descripcion = st.text_area(
            "Descripción de la OT *",
            placeholder="AVISO XXXX -> O.T. XXXX: Descripción detallada del trabajo...",
            height=120,
        )

        st.divider()
        submitted = st.form_submit_button("✅ Crear aviso", type="primary")

    if submitted:
        errores = []
        if not num_aviso:
            errores.append("El número de aviso es obligatorio.")
        if not esm.strip():
            errores.append("El campo E.S.M. es obligatorio.")
        if not descripcion.strip():
            errores.append("La descripción es obligatoria.")

        # Verificar duplicado
        existing = [a for a in todos if a["num_aviso"] == num_aviso]
        if existing:
            errores.append(f"Ya existe un aviso con el número {num_aviso}.")

        if errores:
            for e in errores:
                st.error(e)
        else:
            new_id = create_aviso({
                "num_aviso":       int(num_aviso),
                "fecha_solicitud": str(fecha_solicitud),
                "generador_ot":    generador_ot.strip(),
                "generador_aviso": generador_aviso.strip(),
                "esm":             esm.strip(),
                "descripcion":     descripcion.strip(),
                "enlace_drive":    enlace_drive.strip(),
                "estado":          "En proceso",
            })
            st.success(f"✅ Aviso #{num_aviso} creado correctamente.")
            st.session_state["aviso_seleccionado_id"] = new_id
            st.session_state["page"] = "detalle_aviso"
            st.rerun()
