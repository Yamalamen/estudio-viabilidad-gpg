"""
App de Gestión de Avisos de Mantenimiento
Sedes Judiciales — Provincia de Alicante

Punto de entrada principal con autenticación y routing de páginas.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from pathlib import Path

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Avisos Mantenimiento — Sedes Judiciales Alicante",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inicializar DB y arrancar scheduler ─────────────────────────────────────
from database.db import init_db
init_db()

from scheduler.tasks import start_scheduler
start_scheduler()

# ── Autenticación ────────────────────────────────────────────────────────────
import yaml
import streamlit_authenticator as stauth
from services.users import get_user_by_username

CONFIG_PATH = Path(__file__).parent / "config.yaml"

if not CONFIG_PATH.exists():
    st.error(
        "No se encontró el fichero config.yaml. "
        "Reinicia la aplicación para generarlo automáticamente."
    )
    st.stop()

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# ── Login ─────────────────────────────────────────────────────────────────────
name, authentication_status, username = authenticator.login(
    location="main",
    fields={
        "Form name": "🔐 Acceso — Mantenimiento Sedes Judiciales",
        "Username":  "Usuario",
        "Password":  "Contraseña",
        "Login":     "Entrar",
    },
)

if authentication_status is False:
    st.error("Usuario o contraseña incorrectos.")
    st.stop()

if authentication_status is None:
    st.markdown(
        "<div style='text-align:center;padding:40px 0;'>"
        "<h2 style='color:#1E3A5F;'>⚙️ Mantenimiento Sedes Judiciales</h2>"
        "<p style='color:#666;'>Provincia de Alicante — Departamento de Mantenimiento</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Usuario autenticado ───────────────────────────────────────────────────────
user_db = get_user_by_username(username)
if not user_db:
    st.error("Usuario no encontrado en la base de datos. Contacta con el administrador.")
    st.stop()

user = {
    "id":       user_db["id"],
    "username": username,
    "nombre":   name,
    "role":     user_db["role"],
    "email":    user_db["email"],
}

# ── Sidebar: info de usuario + logout ────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"<div style='background:#1E3A5F;color:white;padding:12px 16px;border-radius:8px;"
        f"margin-bottom:8px;'>"
        f"<b>👤 {user['nombre']}</b><br/>"
        f"<small style='color:#A0C4FF;'>{'🔑 Supervisor' if user['role']=='supervisor' else '📋 Coordinador'}</small>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Navegación
    st.markdown("### Navegación")
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state["page"] = "dashboard"
        st.rerun()

    if user["role"] == "supervisor":
        if st.button("➕ Nuevo aviso", use_container_width=True):
            st.session_state["page"] = "crear_aviso"
            st.rerun()
        if st.button("⚙️ Administración", use_container_width=True):
            st.session_state["page"] = "admin"
            st.rerun()

    authenticator.logout("🚪 Cerrar sesión", "sidebar")

# ── Routing de páginas ────────────────────────────────────────────────────────
page = st.session_state.get("page", "dashboard")

if page == "dashboard":
    from pages.dashboard import render
    render(user)

elif page == "detalle_aviso":
    from pages.detalle_aviso import render
    render(user)

elif page == "crear_aviso":
    if user["role"] == "supervisor":
        from pages.crear_aviso import render
        render(user)
    else:
        st.error("Sin permisos.")
        st.session_state["page"] = "dashboard"
        st.rerun()

elif page == "admin":
    if user["role"] == "supervisor":
        from pages.admin import render
        render(user)
    else:
        st.error("Sin permisos.")
        st.session_state["page"] = "dashboard"
        st.rerun()

else:
    st.session_state["page"] = "dashboard"
    st.rerun()
