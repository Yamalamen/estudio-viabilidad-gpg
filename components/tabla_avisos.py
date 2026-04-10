"""
Tabla de avisos con color coding usando pandas Styler (compatible con todos los navegadores).
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date


_ESTADO_ICONS = {
    "En proceso":     "🔵 En proceso",
    "Acabado":        "🟢 Acabado",
    "Falta material": "🟡 Falta material",
}


def _calcular_color_hex(aviso: dict) -> str:
    if aviso.get("estado") == "Acabado":
        return "#C6EFCE"   # verde
    try:
        fecha_str = str(aviso.get("fecha_solicitud", ""))[:10]
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        dias  = (date.today() - fecha).days
    except Exception:
        return "#BDD7EE"
    if dias > 90:
        return "#FFC7CE"   # rojo
    elif dias > 60:
        return "#FFD966"   # naranja
    return "#BDD7EE"       # azul


def _dias_abierto(fecha_str: str) -> int:
    try:
        return (date.today() - datetime.strptime(str(fecha_str)[:10], "%Y-%m-%d").date()).days
    except Exception:
        return 0


def render_tabla(avisos: list, key_suffix: str = "") -> dict | None:
    """
    Renderiza la tabla de avisos con color coding.
    Devuelve el aviso seleccionado o None.
    """
    if not avisos:
        st.info("No hay avisos que coincidan con los filtros seleccionados.")
        return None

    df = pd.DataFrame(avisos)

    # Columnas a mostrar
    cols_show = [
        "num_aviso", "fecha_solicitud", "sede", "generador_ot", "generador_aviso",
        "esm", "descripcion", "estado", "coordinador_nombre",
        "enlace_drive", "fecha_cierre",
    ]
    cols_show = [c for c in cols_show if c in df.columns]
    df_show   = df[cols_show].copy()

    # Renombrar columnas para UI
    rename_map = {
        "num_aviso":          "Aviso",
        "fecha_solicitud":    "Fecha",
        "sede":               "Sede",
        "generador_ot":       "Generador OT",
        "generador_aviso":    "Generador Aviso",
        "esm":                "E.S.M.",
        "descripcion":        "Descripción",
        "estado":             "Estado",
        "coordinador_nombre": "Coordinador",
        "enlace_drive":       "Drive",
        "fecha_cierre":       "Fecha cierre",
    }
    df_show.rename(columns=rename_map, inplace=True)
    df_show["Días"] = df["fecha_solicitud"].apply(_dias_abierto)

    # Colores por fila
    colors = [_calcular_color_hex(av) for av in avisos]

    def _style_row(row):
        color = colors[row.name]
        return [f"background-color: {color}; color: #1A1A2E"] * len(row)

    styled = df_show.style.apply(_style_row, axis=1)

    st.dataframe(
        styled,
        use_container_width=True,
        height=550,
        hide_index=True,
    )

    # Selector para abrir el detalle
    st.markdown("**Selecciona un aviso para ver detalles o cambiar su estado:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        opciones = [
            f"#{av['num_aviso']} — {av.get('sede','?')} — {av.get('estado','?')} — {_dias_abierto(av.get('fecha_solicitud',''))} días"
            for av in avisos
        ]
        seleccion = st.selectbox(
            "Aviso",
            ["— elige uno —"] + opciones,
            label_visibility="collapsed",
            key=f"sel_aviso_{key_suffix}",
        )
    with col2:
        abrir = st.button("📂 Abrir", type="primary", use_container_width=True, key=f"btn_abrir_{key_suffix}")

    if abrir and seleccion != "— elige uno —":
        idx = opciones.index(seleccion)
        return avisos[idx]

    return None
