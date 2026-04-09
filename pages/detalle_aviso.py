"""
Página de detalle de un aviso: edición, comentarios, asignación.
"""
import streamlit as st
from datetime import date, datetime
from services.avisos import get_aviso_by_id, update_aviso
from services.comentarios import get_comentarios, add_comentario
from services.notificaciones import crear_notificacion
from services.users import get_coordinadores, get_laura, get_user_by_id
from services.email_service import send_asignacion, send_falta_material
from services.excel_sync import generate_excel


def _color_badge(estado: str, dias: int) -> str:
    if estado == "Acabado":
        return "background:#C6EFCE;color:#1A6530;padding:4px 12px;border-radius:12px;font-weight:bold;"
    if dias > 90:
        return "background:#FFC7CE;color:#9C0006;padding:4px 12px;border-radius:12px;font-weight:bold;"
    if dias > 60:
        return "background:#FFD966;color:#7D4F00;padding:4px 12px;border-radius:12px;font-weight:bold;"
    return "background:#BDD7EE;color:#1F4E79;padding:4px 12px;border-radius:12px;font-weight:bold;"


def render(user: dict):
    aviso_id = st.session_state.get("aviso_seleccionado_id")
    if not aviso_id:
        st.error("No se ha seleccionado ningún aviso.")
        if st.button("⬅️ Volver al dashboard"):
            st.session_state["page"] = "dashboard"
            st.rerun()
        return

    aviso = get_aviso_by_id(aviso_id)
    if not aviso:
        st.error("Aviso no encontrado.")
        return

    # Calcular días abierto
    try:
        fecha = datetime.strptime(str(aviso["fecha_solicitud"])[:10], "%Y-%m-%d").date()
        dias  = (date.today() - fecha).days
    except Exception:
        dias = 0

    # ── Cabecera ─────────────────────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 9])
    with col_back:
        if st.button("⬅️ Volver"):
            st.session_state["page"] = "dashboard"
            st.rerun()
    with col_title:
        estado_badge = _color_badge(aviso["estado"], dias)
        st.markdown(
            f"<h2 style='color:#1E3A5F;'>Aviso <b>#{aviso['num_aviso']}</b> &nbsp;"
            f"<span style='{estado_badge}'>{aviso['estado']}</span> "
            f"&nbsp;<span style='font-size:14px;color:#888;'>{dias} días abierto</span></h2>",
            unsafe_allow_html=True,
        )
        if aviso.get("sede"):
            st.markdown(f"📍 **Sede:** {aviso['sede']}")

    st.divider()

    # ── Datos del aviso (dos columnas) ────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📋 Datos del aviso**")
        st.text_input("Nº Aviso",          value=str(aviso["num_aviso"]),     disabled=True)
        st.text_input("Fecha de solicitud", value=str(aviso["fecha_solicitud"]), disabled=True)
        st.text_input("Generador OT",      value=aviso["generador_ot"] or "", disabled=True)
        st.text_input("Generador Aviso",   value=aviso["generador_aviso"] or "", disabled=True)
        st.text_area("E.S.M.",             value=aviso["esm"] or "",          disabled=True, height=60)
    with col2:
        st.markdown("**📝 Descripción**")
        st.text_area("Descripción de la OT",
                     value=aviso["descripcion"] or "",
                     disabled=True, height=120)
        if aviso.get("fecha_cierre"):
            st.text_input("Fecha de cierre", value=str(aviso["fecha_cierre"]), disabled=True)

    st.divider()

    # ── Formulario de actualización ──────────────────────────────────────────────
    st.markdown("### ✏️ Actualizar aviso")
    with st.form("form_actualizar_aviso", clear_on_submit=False):
        # Estado
        estados    = ["En proceso", "Acabado", "Falta material"]
        idx_estado = estados.index(aviso["estado"]) if aviso["estado"] in estados else 0
        nuevo_estado = st.selectbox("Estado", estados, index=idx_estado)

        # Material necesario (solo cuando falta material)
        material_txt = ""
        if nuevo_estado == "Falta material":
            st.info("⚠️ Describe el material necesario. Se notificará automáticamente a Laura.")
            material_txt = st.text_area(
                "Material necesario",
                value=aviso.get("material_necesario") or "",
                placeholder="Describe el material que falta...",
                height=80,
            )

        # Asignación (solo supervisores)
        nuevo_coord_id = aviso.get("coordinador_id")
        if user["role"] == "supervisor":
            coords    = get_coordinadores()
            coord_map = {c["nombre"]: c["id"] for c in coords}
            coord_map_inv = {v: k for k, v in coord_map.items()}
            cur_nombre = coord_map_inv.get(aviso.get("coordinador_id"), "Sin asignar")
            opts       = ["Sin asignar"] + list(coord_map.keys())
            idx_coord  = opts.index(cur_nombre) if cur_nombre in opts else 0
            sel_coord  = st.selectbox("Asignar coordinador", opts, index=idx_coord)
            nuevo_coord_id = coord_map.get(sel_coord) if sel_coord != "Sin asignar" else None

        # Enlace Drive
        nuevo_drive = st.text_input(
            "🔗 Enlace Google Drive",
            value=aviso.get("enlace_drive") or "",
            placeholder="https://drive.google.com/...",
        )

        submitted = st.form_submit_button("💾 Guardar cambios", type="primary")

    if submitted:
        updates = {
            "estado":           nuevo_estado,
            "coordinador_id":   nuevo_coord_id,
            "enlace_drive":     nuevo_drive.strip(),
            "material_necesario": material_txt.strip() if nuevo_estado == "Falta material" else None,
        }

        # Fecha cierre al marcar Acabado
        if nuevo_estado == "Acabado" and aviso["estado"] != "Acabado":
            updates["fecha_cierre"] = str(date.today())

        update_aviso(aviso_id, updates)

        # Notificaciones por cambio de coordinador
        prev_coord = aviso.get("coordinador_id")
        if nuevo_coord_id and nuevo_coord_id != prev_coord:
            coord = get_user_by_id(nuevo_coord_id)
            if coord:
                crear_notificacion(
                    user_id=nuevo_coord_id,
                    mensaje=f"📋 Se te ha asignado el aviso #{aviso['num_aviso']} en {aviso['sede'] or 'desconocida'}.",
                    tipo="asignacion",
                    aviso_id=aviso_id,
                )
                send_asignacion(
                    coordinador_email=coord["email"],
                    coordinador_nombre=coord["nombre"],
                    num_aviso=aviso["num_aviso"],
                    sede=aviso["sede"] or "",
                    descripcion=aviso["descripcion"] or "",
                )

        # Notificación a Laura si falta material
        if nuevo_estado == "Falta material" and material_txt.strip():
            laura = get_laura()
            if laura:
                crear_notificacion(
                    user_id=laura["id"],
                    mensaje=(
                        f"⚠️ El coordinador {user['nombre']} indica que falta material "
                        f"para el aviso #{aviso['num_aviso']} ({aviso['sede'] or ''}):\n{material_txt[:200]}"
                    ),
                    tipo="falta_material",
                    aviso_id=aviso_id,
                )
                send_falta_material(
                    laura_email=laura["email"],
                    coordinador_nombre=user["nombre"],
                    num_aviso=aviso["num_aviso"],
                    sede=aviso["sede"] or "",
                    material=material_txt,
                )

        st.success("✅ Aviso actualizado correctamente.")
        st.rerun()

    st.divider()

    # ── Sección de comentarios ───────────────────────────────────────────────────
    st.markdown("### 💬 Comentarios y anotaciones")

    comentarios = get_comentarios(aviso_id)
    if comentarios:
        for c in comentarios:
            fecha_fmt = c["fecha_comentario"][:16] if c.get("fecha_comentario") else ""
            st.markdown(
                f"<div style='background:#F0F4F8;border-left:4px solid #1E3A5F;"
                f"padding:10px 14px;border-radius:4px;margin-bottom:8px;'>"
                f"<small style='color:#666;'>📅 {fecha_fmt} — "
                f"<strong>{c['autor_nombre']}</strong></small><br/>"
                f"{c['texto']}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Aún no hay comentarios.")

    with st.form("form_comentario", clear_on_submit=True):
        nuevo_comentario = st.text_area(
            "Añadir comentario / anotación",
            placeholder="Escribe tu comentario aquí...",
            height=80,
        )
        if st.form_submit_button("📝 Publicar comentario"):
            if nuevo_comentario.strip():
                add_comentario(aviso_id, user["id"], nuevo_comentario)
                st.success("Comentario añadido.")
                st.rerun()
            else:
                st.warning("El comentario no puede estar vacío.")

    # ── Descarga Excel actualizado ──────────────────────────────────────────────
    st.divider()
    with st.expander("📥 Descargar Excel actualizado"):
        excel_bytes = generate_excel()
        from datetime import datetime as dt
        ts = dt.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="Descargar Excel completo",
            data=excel_bytes,
            file_name=f"avisos_mantenimiento_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
