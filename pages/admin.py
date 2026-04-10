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

    tabs = st.tabs(["👥 Usuarios", "📧 Configuración Email", "📋 Log de notificaciones", "📥 Importar Excel"])

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
        from sqlalchemy import text as _text
        with get_connection() as _conn:
            rows = _conn.execute(_text("""
                SELECT n.*, u.nombre AS usuario_nombre, a.num_aviso
                FROM notificaciones n
                JOIN users u ON n.user_id = u.id
                LEFT JOIN avisos a ON n.aviso_id = a.id
                ORDER BY n.fecha_creacion DESC
                LIMIT 200
            """)).fetchall()

        if rows:
            import pandas as pd
            df = pd.DataFrame([dict(r._mapping) for r in rows])
            st.dataframe(
                df[["fecha_creacion", "usuario_nombre", "num_aviso", "tipo", "mensaje", "leida"]],
                use_container_width=True,
                height=500,
            )
        else:
            st.info("Sin notificaciones registradas.")


    # ── TAB 4: Importar Excel ────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📥 Importar avisos desde Excel")
        st.info(
            "Sube tu fichero Excel con las columnas en este orden:\n\n"
            "**A:** Aviso (Nº) · **B:** Fecha de solicitud · **C:** Generador OT · "
            "**D:** Generador Aviso · **E:** E.S.M. · **F:** Descripción de la OT\n\n"
            "Los avisos que ya existan en la app se omitirán automáticamente (sin duplicados)."
        )

        uploaded = st.file_uploader(
            "Selecciona el fichero Excel",
            type=["xlsx", "xls"],
            help="Formato .xlsx o .xls — máximo 10 MB",
        )

        if uploaded:
            import pandas as pd
            try:
                df_preview = pd.read_excel(uploaded, nrows=5)
                st.markdown("**Vista previa (primeras 5 filas):**")
                st.dataframe(df_preview, use_container_width=True)
                uploaded.seek(0)  # reset buffer after preview read
            except Exception as e:
                st.error(f"No se pudo leer el fichero: {e}")
                df_preview = None

            if df_preview is not None:
                if st.button("✅ Importar todos los avisos", type="primary"):
                    with st.spinner("Importando avisos..."):
                        resultado = _importar_desde_buffer(uploaded)
                    st.success(
                        f"✅ Importación completada — "
                        f"**Importados:** {resultado['importados']} · "
                        f"**Ya existían (omitidos):** {resultado['omitidos']} · "
                        f"**Errores:** {resultado['errores']}"
                    )
                    if resultado["errores"] > 0 and resultado["detalle_errores"]:
                        with st.expander("Ver errores"):
                            for err in resultado["detalle_errores"]:
                                st.warning(err)
                    if resultado["importados"] > 0:
                        st.info("Vuelve al Dashboard para ver los avisos importados.")


def _importar_desde_buffer(file_buffer) -> dict:
    """Importa avisos desde un buffer de fichero Excel (BytesIO de Streamlit)."""
    import io
    import re
    import pandas as pd
    from datetime import datetime
    from database.db import get_connection

    def _extract_sede(esm: str) -> str:
        if not esm or pd.isna(esm):
            return ""
        m = re.search(r"OBRA CIVIL\s+(.+)$", str(esm).strip(), re.IGNORECASE)
        return m.group(1).strip() if m else str(esm).strip()

    def _parse_fecha(val) -> str:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return str(datetime.today().date())
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d")
        s = str(val).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return s

    file_buffer.seek(0)
    df = pd.read_excel(file_buffer, header=0)

    conn = get_connection()
    c    = conn.cursor()

    importados      = 0
    omitidos        = 0
    errores         = 0
    detalle_errores = []

    for idx, row in df.iterrows():
        try:
            vals = row.tolist()
            num_aviso       = vals[0] if len(vals) > 0 else None
            fecha_str       = vals[1] if len(vals) > 1 else None
            generador_ot    = str(vals[2]).strip() if len(vals) > 2 and not pd.isna(vals[2]) else ""
            generador_aviso = str(vals[3]).strip() if len(vals) > 3 and not pd.isna(vals[3]) else ""
            esm             = str(vals[4]).strip() if len(vals) > 4 and not pd.isna(vals[4]) else ""
            descripcion     = str(vals[5]).strip() if len(vals) > 5 and not pd.isna(vals[5]) else ""
            estado          = str(vals[6]).strip() if len(vals) > 6 and not pd.isna(vals[6]) else "En proceso"
            enlace_drive    = str(vals[8]).strip() if len(vals) > 8 and not pd.isna(vals[8]) else ""
            material        = str(vals[9]).strip() if len(vals) > 9 and not pd.isna(vals[9]) else ""
            fecha_cierre    = _parse_fecha(vals[10]) if len(vals) > 10 and not pd.isna(vals[10]) else None

            if pd.isna(num_aviso) or str(num_aviso).strip() in ("", "nan", "Aviso"):
                omitidos += 1
                continue

            num_aviso_int = int(float(str(num_aviso)))
            fecha         = _parse_fecha(fecha_str)
            sede          = _extract_sede(esm)

            if estado not in ("En proceso", "Acabado", "Falta material"):
                estado = "En proceso"

            existing = c.execute(
                "SELECT id FROM avisos WHERE num_aviso=?", (num_aviso_int,)
            ).fetchone()
            if existing:
                omitidos += 1
                continue

            c.execute("""
                INSERT INTO avisos
                    (num_aviso, fecha_solicitud, generador_ot, generador_aviso,
                     esm, sede, descripcion, estado, enlace_drive,
                     material_necesario, fecha_cierre)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                num_aviso_int, fecha, generador_ot, generador_aviso,
                esm, sede, descripcion, estado, enlace_drive,
                material or None, fecha_cierre,
            ))
            importados += 1

        except Exception as e:
            errores += 1
            detalle_errores.append(f"Fila {idx + 2}: {e}")

    conn.commit()
    conn.close()
    return {"importados": importados, "omitidos": omitidos, "errores": errores, "detalle_errores": detalle_errores}


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
