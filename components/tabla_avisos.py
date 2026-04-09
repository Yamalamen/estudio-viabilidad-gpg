"""
Tabla de avisos con color coding usando st-aggrid.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False


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


def render_tabla(avisos: list) -> dict | None:
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
        "num_aviso":           "Aviso",
        "fecha_solicitud":     "Fecha solicitud",
        "sede":                "Sede",
        "generador_ot":        "Generador OT",
        "generador_aviso":     "Generador Aviso",
        "esm":                 "E.S.M.",
        "descripcion":         "Descripción",
        "estado":              "Estado",
        "coordinador_nombre":  "Coordinador",
        "enlace_drive":        "Drive",
        "fecha_cierre":        "Fecha cierre",
    }
    df_show.rename(columns=rename_map, inplace=True)

    # Días abierto
    df_show["Días"] = df["fecha_solicitud"].apply(_dias_abierto)

    # Color por fila
    df_show["_color"] = [_calcular_color_hex(av) for av in avisos]
    df_show["_id"]    = [av["id"] for av in avisos]

    if AGGRID_AVAILABLE:
        return _render_aggrid(df_show, avisos)
    else:
        return _render_fallback(df_show, avisos)


def _render_aggrid(df_show: pd.DataFrame, avisos: list) -> dict | None:
    gb = GridOptionsBuilder.from_dataframe(df_show.drop(columns=["_color", "_id"]))
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)
    gb.configure_column("Aviso",         width=90,  pinned="left")
    gb.configure_column("Fecha solicitud", width=130)
    gb.configure_column("Sede",          width=160)
    gb.configure_column("Estado",        width=150)
    gb.configure_column("Descripción",   width=320, wrapText=True, autoHeight=True)
    gb.configure_column("E.S.M.",        width=300)
    gb.configure_column("Coordinador",   width=140)
    gb.configure_column("Días",          width=70)
    gb.configure_column("Drive",         width=80)
    gb.configure_column("Fecha cierre",  width=120)
    gb.configure_grid_options(rowHeight=36)

    # Aplicar color de fondo a cada fila usando cellStyle
    color_js = JsCode("""
    function(params) {
        const colors = %s;
        const idx = params.rowIndex;
        if (colors[idx]) {
            return { 'background-color': colors[idx], 'color': '#1A1A2E' };
        }
        return {};
    }
    """ % str(df_show["_color"].tolist()))

    for col in df_show.columns:
        if col not in ("_color", "_id"):
            gb.configure_column(col, cellStyle=color_js)

    go = gb.build()
    result = AgGrid(
        df_show.drop(columns=["_color", "_id"]),
        gridOptions=go,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        height=520,
        use_container_width=True,
        theme="streamlit",
    )

    selected = result.get("selected_rows")
    if selected is not None and len(selected) > 0:
        sel_row = selected[0] if hasattr(selected, "__getitem__") else selected.iloc[0].to_dict()
        num = sel_row.get("Aviso")
        if num:
            for av in avisos:
                if av["num_aviso"] == num:
                    return av
    return None


def _render_fallback(df_show: pd.DataFrame, avisos: list) -> dict | None:
    """Tabla simple con color via Styler cuando AgGrid no está disponible."""

    def _style_row(row):
        color = df_show.loc[row.name, "_color"]
        return [f"background-color: {color}; color: #1A1A2E"] * len(row)

    styled = (
        df_show.drop(columns=["_color", "_id"])
        .style.apply(_style_row, axis=1)
    )
    st.dataframe(styled, use_container_width=True, height=500)

    # Selector manual
    num_aviso_sel = st.selectbox(
        "Selecciona un aviso para ver detalles:",
        options=[av["num_aviso"] for av in avisos],
        format_func=lambda n: f"#{n} — {next((a['sede'] for a in avisos if a['num_aviso']==n), '')}",
    )
    for av in avisos:
        if av["num_aviso"] == num_aviso_sel:
            return av
    return None
