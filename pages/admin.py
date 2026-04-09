"""
Panel de administración (solo supervisores).
"""
import streamlit as st
from database.db import get_connection
from services.users import get_all_users, toggle_user_active, update_user_email, create_user
from services.notificaciones import get_notificaciones
import yaml
import bcrypt
from pathlib import Path


def render(user: dict):
    if user["role"] != "supervisor":
        st.error("Acceso restringido a supervisores.")
        return

    col_back, col_title = st.columns([1, 9])
    with col_back:
        if st.button("⬅️ Volver"):
            st.session_state["page"] = "dashboard"
            st.rerun()
    with col_title:
        st.markdown("<h2 style='color:#1E3A5F;'>⚙️ Administración</h2>", unsafe_allow_html=True)

    tabs = st.tabs(["👥 Usuarios", "📧 Configuración Email", "📋 Log de notificaciones"])

    # ── TAB 1: Usuarios ──────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### Gestión de usuarios")
        users = get_all_users()

        for u in users:
            with st.expander(f"{'🟢' if u['active'] else '🔴'} {u['nombre']} ({u['role']}) — @{u['username']}"):
                col1, col2, col3 = st.columns([3, 3, 2])
                with col1:
                    new_email = st.text_input(
                        "Email", value=u["email"], key=f"email_{u['id']}"
                    )
                    if st.button("💾 Guardar email", key=f"save_email_{u['id']}"):
                        update_user_email(u["id"], new_email.strip())
                        st.success("Email actualizado.")
                        st.rerun()
                with col2:
                    st.text_input("Rol", value=u["role"], disabled=True, key=f"rol_{u['id']}")
                with col3:
                    label = "🔴 Desactivar" if u["active"] else "🟢 Activar"
                    if st.button(label, key=f"toggle_{u['id']}"):
                        toggle_user_active(u["id"], not u["active"])
                        st.rerun()

        st.divider()
        st.markdown("### ➕ Añadir nuevo usuario")
        with st.form("form_nuevo_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Usuario (sin espacios)")
                new_nombre   = st.text_input("Nombre completo")
            with c2:
                new_email_u  = st.text_input("Email")
                new_role     = st.selectbox("Rol", ["coordinador", "supervisor"])
            new_pwd = st.text_input("Contraseña inicial", type="password")

            if st.form_submit_button("Crear usuario"):
                if not all([new_username, new_nombre, new_email_u, new_pwd]):
                    st.error("Todos los campos son obligatorios.")
                else:
                    try:
                        uid = create_user(new_username.strip(), new_nombre.strip(),
                                          new_email_u.strip(), new_role)
                        # Actualizar config.yaml
                        _add_user_to_config(new_username.strip(), new_nombre.strip(),
                                            new_email_u.strip(), new_pwd)
                        st.success(f"Usuario '{new_username}' creado. Reinicia la app para que el login surta efecto.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── TAB 2: Configuración email ───────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### Configuración SMTP (Microsoft 365)")
        config_email_path = Path(__file__).parent.parent / "config_email.py"
        st.info(
            "Edita el fichero `config_email.py` en la raíz del proyecto con tus credenciales "
            "de Microsoft 365 / Outlook. El fichero está excluido del control de versiones."
        )

        template = """# config_email.py  — NO subir a git
SMTP_SERVER   = "smtp.office365.com"
SMTP_PORT     = 587
EMAIL_USER    = "tu_cuenta@dominio.es"
EMAIL_PASSWORD = "tu_contraseña_de_aplicacion"
FROM_NAME     = "Mantenimiento Sedes Judiciales Alicante"
"""
        if not config_email_path.exists():
            if st.button("📄 Crear config_email.py con plantilla"):
                config_email_path.write_text(template, encoding="utf-8")
                st.success("Fichero creado. Edítalo con tus credenciales reales.")
        else:
            st.success("✅ config_email.py existe.")
            with st.expander("Ver / editar contenido"):
                current = config_email_path.read_text(encoding="utf-8")
                edited  = st.text_area("config_email.py", value=current, height=200)
                if st.button("💾 Guardar"):
                    config_email_path.write_text(edited, encoding="utf-8")
                    st.success("Guardado. Reinicia la app para aplicar los cambios.")

    # ── TAB 3: Log de notificaciones ─────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### Log de todas las notificaciones")
        conn = get_connection()
        rows = conn.execute("""
            SELECT n.*, u.nombre AS usuario_nombre, a.num_aviso
            FROM notificaciones n
            JOIN users u ON n.user_id = u.id
            LEFT JOIN avisos a ON n.aviso_id = a.id
            ORDER BY n.fecha_creacion DESC
            LIMIT 200
        """).fetchall()
        conn.close()

        if rows:
            import pandas as pd
            df = pd.DataFrame([dict(r) for r in rows])
            st.dataframe(
                df[["fecha_creacion", "usuario_nombre", "num_aviso", "tipo", "mensaje", "leida"]],
                use_container_width=True,
                height=500,
            )
        else:
            st.info("Sin notificaciones registradas.")


def _add_user_to_config(username: str, nombre: str, email: str, password: str):
    """Añade el usuario al config.yaml de streamlit-authenticator."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        return
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    config["credentials"]["usernames"][username] = {
        "name":     nombre,
        "email":    email,
        "password": hashed,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
