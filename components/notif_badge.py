"""
Campana de notificaciones con badge de conteo.
"""
import streamlit as st
from services.notificaciones import (
    get_notificaciones, count_no_leidas,
    marcar_leida, marcar_todas_leidas,
)


def render_notif_badge(user_id: int):
    """Renderiza la campana de notificaciones en el sidebar."""
    no_leidas = count_no_leidas(user_id)

    with st.sidebar:
        st.divider()
        if no_leidas > 0:
            st.markdown(
                f"### 🔔 Notificaciones &nbsp;&nbsp;"
                f"<span style='background:#DC3545;color:white;border-radius:12px;"
                f"padding:2px 8px;font-size:14px;'>{no_leidas}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("### 🔔 Notificaciones")

        notifs = get_notificaciones(user_id, solo_no_leidas=False)

        if not notifs:
            st.caption("Sin notificaciones")
            return

        with st.expander(f"Ver todas ({len(notifs)})", expanded=(no_leidas > 0)):
            if no_leidas > 0:
                if st.button("✅ Marcar todas como leídas", key="mark_all_read"):
                    marcar_todas_leidas(user_id)
                    st.rerun()

            for n in notifs[:20]:
                icono  = "🔵" if not n["leida"] else "⚪"
                aviso_ref = f" (Aviso #{n['num_aviso']})" if n.get("num_aviso") else ""
                fecha  = n["fecha_creacion"][:16] if n.get("fecha_creacion") else ""

                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(
                        f"{icono} **{fecha}**{aviso_ref}  \n{n['mensaje']}",
                        help=n["tipo"] or "",
                    )
                with col2:
                    if not n["leida"]:
                        if st.button("✓", key=f"read_{n['id']}", help="Marcar como leída"):
                            marcar_leida(n["id"])
                            st.rerun()
                st.divider()
