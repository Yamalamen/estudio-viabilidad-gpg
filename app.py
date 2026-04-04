# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import zipfile
from typing import Dict, List

import pandas as pd
import streamlit as st

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False


st.set_page_config(page_title="Estudio Viabilidad Proyecto by GPG", page_icon="🏗️", layout="wide")


def safe_float(v, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def safe_int(v, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(round(float(v)))
    except Exception:
        return default


def eur(v: float) -> str:
    return f"{safe_float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    return f"{safe_float(v) * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def eur_m2(v: float) -> str:
    return f"{safe_float(v):,.2f} €/m²".replace(",", "X").replace(".", ",").replace("X", ".")


def ratio(v: float) -> str:
    return f"{safe_float(v):,.2f}x".replace(",", "X").replace(".", ",").replace("X", ".")


def display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].fillna("").astype(str)
    return out


def to_excel_bytes(dfs: Dict[str, pd.DataFrame]):
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for name, df in dfs.items():
                df.to_excel(writer, index=False, sheet_name=name[:31])
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "estudio_viabilidad.xlsx"
    except Exception:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, df in dfs.items():
                zf.writestr(f"{name[:31]}.csv", df.to_csv(index=False).encode("utf-8-sig"))
        return buffer.getvalue(), "application/zip", "estudio_viabilidad.zip"


def build_pdf_bytes(resumen_df: pd.DataFrame):
    if not REPORTLAB_OK:
        return None
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Estudio de Viabilidad - Resumen")
    y -= 25
    c.setFont("Helvetica", 10)
    for _, row in resumen_df.iterrows():
        line = f"{row['Campo']}: {row['Valor']}"
        c.drawString(40, y, line[:110])
        y -= 14
        if y < 40:
            c.showPage()
            y = h - 40
            c.setFont("Helvetica", 10)
    c.save()
    return buffer.getvalue()


DEFAULT_INPUTS = {
    "activo": "C/ Los Cincuenta 3, Alicante",
    "referencia_catastral": "7653302YH1475D0001AL",
    "parcela_m2": 311.0,
    "sup_construida_sr_m2": 1000.0,
    "sup_construida_br_m2": 260.0,
    "sup_vendible_m2": 1000.0,
    "coste_construccion_sr_m2": 1175.79,
    "coste_construccion_br_m2": 850.0,
    "precio_suelo": 315000.0,
    "iva_compra_suelo_pct": 0.21,
    "ajd_pct": 0.015,
    "num_viviendas": 11,
    "precio_vivienda": 260000.0,
    "num_garajes": 10,
    "precio_garaje": 25000.0,
    "num_trasteros": 10,
    "precio_trastero": 3500.0,
    "mes_compra": 0,
    "mes_licencia": 6,
    "mes_inicio_obra": 7,
    "mes_comercializacion": 10,
    "mes_entrega": 22,
    "sobrecoste_pct": 0.00,
    "caida_precios_pct": 0.00,
    "interes_anual_pct": 0.06,
    "pct_circulacion_br": 0.30,
    "m2_por_plaza": 28.0,
    "m2_por_trastero": 6.0,
    "ratio_trasteros_plaza": 1.0,
}

BASE_COST_ITEMS = [
    ["Due diligence", "Antes de firmar", "Abogado inmobiliario + mercantil", 5000.0, ""],
    ["Due diligence", "Antes de firmar", "Topográfico", 1300.0, ""],
    ["Due diligence", "Antes de firmar", "Geotécnico", 4000.0, ""],
    ["Compra suelo", "Firma", "Precio suelo", 0.0, "Auto"],
    ["Compra suelo", "Firma", "IVA compra suelo", 0.0, "Auto"],
    ["Compra suelo", "Firma", "AJD compra suelo", 0.0, "Auto"],
    ["Proyecto", "Tras compra", "Proyecto básico", 23000.0, ""],
    ["Proyecto", "Tras compra", "Proyecto ejecución", 28000.0, ""],
    ["Proyecto", "Tras compra", "Dirección de obra + DEO + CSS", 33500.0, ""],
    ["Licencia", "Solicitud", "ICIO", 0.0, "Auto"],
    ["Preobra", "Antes obra", "Demolición + residuos", 39000.0, ""],
    ["Obra", "Inicio", "Construcción sobre rasante", 0.0, "Auto"],
    ["Obra", "Inicio", "Construcción bajo rasante", 0.0, "Auto"],
    ["Obra", "Durante", "Ascensor", 35000.0, ""],
    ["Obra", "Durante", "Acometidas definitivas", 25000.0, ""],
    ["Obra", "Durante", "Urbanización interior / remates", 32500.0, ""],
    ["Obra", "Durante", "Medios auxiliares / grúa / casetas", 30000.0, ""],
    ["Obra", "Durante", "Seguridad y salud ejecución", 14000.0, ""],
    ["Obra", "Durante", "Imprevistos / modificados", 0.0, "Auto"],
    ["Financiación", "Durante", "Intereses", 0.0, "Auto"],
    ["Comercialización", "Ventas", "Marketing y publicidad", 15000.0, ""],
    ["Comercialización", "Ventas", "Comisión agencia venta", 0.0, ""],
    ["Cierre", "Final", "Seguro decenal", 12000.0, ""],
    ["Cierre", "Final", "Obra nueva y división horizontal", 10000.0, ""],
]

DEFAULT_RISK = pd.DataFrame([
    {"Categoría": "Fiscalidad compra", "Estado": "Pendiente validación escrita", "Puntos": 3, "Comentario": "Confirmar IVA compra suelo"},
    {"Categoría": "Geotécnico", "Estado": "Pendiente", "Puntos": 3, "Comentario": "Impacta sótano y cimentación"},
    {"Categoría": "Financiación", "Estado": "Sin term sheet bancario", "Puntos": 2, "Comentario": "Validar préstamo promotor"},
    {"Categoría": "Comercialización", "Estado": "Sin preventas", "Puntos": 2, "Comentario": "Contrastar velocidad de ventas"},
])

DEFAULT_MIX = pd.DataFrame([
    {"Tipología": "Vivienda tipo", "Unidades": DEFAULT_INPUTS["num_viviendas"], "Precio unitario (€)": DEFAULT_INPUTS["precio_vivienda"], "m² vendibles por unidad": DEFAULT_INPUTS["sup_vendible_m2"] / DEFAULT_INPUTS["num_viviendas"], "Observaciones": ""}
])


def init_state():
    if "risk_df" not in st.session_state:
        st.session_state["risk_df"] = DEFAULT_RISK.copy()
    if "mix_df" not in st.session_state:
        st.session_state["mix_df"] = DEFAULT_MIX.copy()
    if "costs_df_user" not in st.session_state:
        st.session_state["costs_df_user"] = pd.DataFrame(BASE_COST_ITEMS, columns=["Fase", "Hito", "Concepto", "Coste base (€)", "Auto"])
    if "contabilidad_df" not in st.session_state:
        st.session_state["contabilidad_df"] = pd.DataFrame(columns=["Fecha", "Concepto", "Importe (€)", "Observaciones"])


init_state()


def build_inputs() -> dict:
    st.sidebar.header("Inputs maestros")

    activo = st.sidebar.text_input("Activo", DEFAULT_INPUTS["activo"])
    rc = st.sidebar.text_input("Referencia catastral", DEFAULT_INPUTS["referencia_catastral"])
    parcela_m2 = st.sidebar.number_input("Parcela catastral (m²)", min_value=0.0, value=DEFAULT_INPUTS["parcela_m2"], step=1.0)

    st.sidebar.subheader("Superficies")
    sup_sr = st.sidebar.number_input("m² construidos sobre rasante", min_value=0.0, value=DEFAULT_INPUTS["sup_construida_sr_m2"], step=10.0)
    sup_br = st.sidebar.number_input("m² construidos bajo rasante", min_value=0.0, value=DEFAULT_INPUTS["sup_construida_br_m2"], step=10.0)
    sup_vendible = st.sidebar.number_input("m² vendibles", min_value=0.0, value=DEFAULT_INPUTS["sup_vendible_m2"], step=10.0)

    st.sidebar.subheader("Costes construcción")
    coste_sr_m2 = st.sidebar.number_input("Coste construcción sobre rasante (€/m²)", min_value=0.0, value=DEFAULT_INPUTS["coste_construccion_sr_m2"], step=10.0)
    coste_br_m2 = st.sidebar.number_input("Coste construcción bajo rasante (€/m²)", min_value=0.0, value=DEFAULT_INPUTS["coste_construccion_br_m2"], step=10.0)

    pem_sr = sup_sr * coste_sr_m2
    pem_br = sup_br * coste_br_m2
    pem = pem_sr + pem_br
    st.sidebar.metric("PEM sobre rasante", eur(pem_sr))
    st.sidebar.metric("PEM bajo rasante", eur(pem_br))
    st.sidebar.metric("PEM total", eur(pem))

    st.sidebar.subheader("Suelo y fiscalidad")
    precio_suelo = st.sidebar.number_input("Precio suelo (€)", min_value=0.0, value=DEFAULT_INPUTS["precio_suelo"], step=5000.0)
    iva_compra = st.sidebar.number_input("IVA compra suelo (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["iva_compra_suelo_pct"] * 100, step=0.5) / 100
    ajd = st.sidebar.number_input("AJD (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["ajd_pct"] * 100, step=0.1) / 100

    st.sidebar.subheader("Programa comercial")
    num_viviendas = st.sidebar.number_input("Nº viviendas", min_value=0, value=DEFAULT_INPUTS["num_viviendas"], step=1)
    precio_vivienda = st.sidebar.number_input("Precio medio vivienda (€)", min_value=0.0, value=DEFAULT_INPUTS["precio_vivienda"], step=5000.0)
    num_garajes = st.sidebar.number_input("Nº garajes", min_value=0, value=DEFAULT_INPUTS["num_garajes"], step=1)
    precio_garaje = st.sidebar.number_input("Precio garaje (€)", min_value=0.0, value=DEFAULT_INPUTS["precio_garaje"], step=1000.0)
    num_trasteros = st.sidebar.number_input("Nº trasteros", min_value=0, value=DEFAULT_INPUTS["num_trasteros"], step=1)
    precio_trastero = st.sidebar.number_input("Precio trastero (€)", min_value=0.0, value=DEFAULT_INPUTS["precio_trastero"], step=500.0)

    st.sidebar.subheader("Bajo rasante")
    pct_circulacion = st.sidebar.number_input("% circulación / maniobra", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["pct_circulacion_br"] * 100, step=1.0) / 100
    m2_por_plaza = st.sidebar.number_input("m² por plaza", min_value=1.0, value=DEFAULT_INPUTS["m2_por_plaza"], step=1.0)
    m2_por_trastero = st.sidebar.number_input("m² por trastero", min_value=1.0, value=DEFAULT_INPUTS["m2_por_trastero"], step=1.0)
    ratio_trasteros_plaza = st.sidebar.number_input("Ratio trasteros/plaza", min_value=0.0, value=DEFAULT_INPUTS["ratio_trasteros_plaza"], step=0.1)

    st.sidebar.subheader("Calendario")
    mes_compra = st.sidebar.number_input("Mes compra", min_value=0, value=DEFAULT_INPUTS["mes_compra"], step=1)
    mes_licencia = st.sidebar.number_input("Mes licencia", min_value=0, value=DEFAULT_INPUTS["mes_licencia"], step=1)
    mes_inicio_obra = st.sidebar.number_input("Mes inicio obra", min_value=0, value=DEFAULT_INPUTS["mes_inicio_obra"], step=1)
    mes_comercial = st.sidebar.number_input("Mes inicio comercialización", min_value=0, value=DEFAULT_INPUTS["mes_comercializacion"], step=1)
    mes_entrega = st.sidebar.number_input("Mes entrega / escrituras", min_value=1, value=DEFAULT_INPUTS["mes_entrega"], step=1)

    st.sidebar.subheader("Sensibilidades")
    sobrecoste_pct = st.sidebar.number_input("Sobrecoste obra (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["sobrecoste_pct"] * 100, step=0.5) / 100
    caida_precios_pct = st.sidebar.number_input("Caída precios venta (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["caida_precios_pct"] * 100, step=0.5) / 100
    interes_anual_pct = st.sidebar.number_input("Interés anual (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["interes_anual_pct"] * 100, step=0.25) / 100

    return {
        "activo": activo,
        "referencia_catastral": rc,
        "parcela_m2": parcela_m2,
        "sup_construida_sr_m2": sup_sr,
        "sup_construida_br_m2": sup_br,
        "sup_construida_total_m2": sup_sr + sup_br,
        "sup_vendible_m2": sup_vendible,
        "coste_construccion_sr_m2": coste_sr_m2,
        "coste_construccion_br_m2": coste_br_m2,
        "pem_sr": pem_sr,
        "pem_br": pem_br,
        "pem": pem,
        "precio_suelo": precio_suelo,
        "iva_compra_suelo_pct": iva_compra,
        "ajd_pct": ajd,
        "num_viviendas": safe_int(num_viviendas),
        "precio_vivienda": precio_vivienda,
        "num_garajes": safe_int(num_garajes),
        "precio_garaje": precio_garaje,
        "num_trasteros": safe_int(num_trasteros),
        "precio_trastero": precio_trastero,
        "pct_circulacion_br": pct_circulacion,
        "m2_por_plaza": m2_por_plaza,
        "m2_por_trastero": m2_por_trastero,
        "ratio_trasteros_plaza": ratio_trasteros_plaza,
        "mes_compra": safe_int(mes_compra),
        "mes_licencia": safe_int(mes_licencia),
        "mes_inicio_obra": safe_int(mes_inicio_obra),
        "mes_comercializacion": safe_int(mes_comercial),
        "mes_entrega": safe_int(mes_entrega),
        "sobrecoste_pct": sobrecoste_pct,
        "caida_precios_pct": caida_precios_pct,
        "interes_anual_pct": interes_anual_pct,
    }


inputs = build_inputs()


def ensure_mix_df(df: pd.DataFrame, inputs: dict) -> pd.DataFrame:
    out = df.copy()
    cols = ["Tipología", "Unidades", "Precio unitario (€)", "m² vendibles por unidad", "Observaciones"]
    for col in cols:
        if col not in out.columns:
            out[col] = 0 if col in ["Unidades", "Precio unitario (€)", "m² vendibles por unidad"] else ""
    out["Tipología"] = out["Tipología"].fillna("").astype(str)
    out["Unidades"] = pd.to_numeric(out["Unidades"], errors="coerce").fillna(0).astype(int)
    out["Precio unitario (€)"] = pd.to_numeric(out["Precio unitario (€)"], errors="coerce").fillna(0.0)
    out["m² vendibles por unidad"] = pd.to_numeric(out["m² vendibles por unidad"], errors="coerce").fillna(0.0)
    out["Observaciones"] = out["Observaciones"].fillna("").astype(str)
    if out.empty:
        out = pd.DataFrame([{
            "Tipología": "Vivienda tipo",
            "Unidades": inputs["num_viviendas"],
            "Precio unitario (€)": inputs["precio_vivienda"],
            "m² vendibles por unidad": inputs["sup_vendible_m2"] / inputs["num_viviendas"] if inputs["num_viviendas"] else 0.0,
            "Observaciones": "",
        }])
    return out[cols]


def ensure_risk_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = ["Categoría", "Estado", "Puntos", "Comentario"]
    for col in cols:
        if col not in out.columns:
            out[col] = 0 if col == "Puntos" else ""
    out["Categoría"] = out["Categoría"].fillna("").astype(str)
    out["Estado"] = out["Estado"].fillna("").astype(str)
    out["Puntos"] = pd.to_numeric(out["Puntos"], errors="coerce").fillna(0).astype(int)
    out["Comentario"] = out["Comentario"].fillna("").astype(str)
    return out[cols]


def ensure_costs_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = ["Fase", "Hito", "Concepto", "Coste base (€)", "Auto"]
    for col in cols:
        if col not in out.columns:
            out[col] = ""
    out["Fase"] = out["Fase"].fillna("").astype(str)
    out["Hito"] = out["Hito"].fillna("").astype(str)
    out["Concepto"] = out["Concepto"].fillna("").astype(str)
    out["Coste base (€)"] = pd.to_numeric(out["Coste base (€)"], errors="coerce").fillna(0.0)
    out["Auto"] = out["Auto"].fillna("").astype(str)
    return out[cols]


tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Dashboard", "Mix comercial", "Costes", "Cash-flow", "Riesgo", "Ratios", "Resumen", "Exportación"
])

with tab1:
    st.subheader("Mix comercial editable")
    st.caption("Todos los datos que influyen en cálculos son modificables.")
    mix_df = st.data_editor(
        ensure_mix_df(st.session_state["mix_df"], inputs),
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="mix_editor",
    )
    st.session_state["mix_df"] = ensure_mix_df(mix_df, inputs)

with tab2:
    st.subheader("Costes editables")
    costs_df = st.data_editor(
        ensure_costs_df(st.session_state["costs_df_user"]),
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="costs_editor",
    )
    st.session_state["costs_df_user"] = ensure_costs_df(costs_df)

with tab4:
    st.subheader("Matriz de riesgo editable")
    risk_df = st.data_editor(
        ensure_risk_df(st.session_state["risk_df"]),
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="risk_editor",
    )
    st.session_state["risk_df"] = ensure_risk_df(risk_df)

with tab6:
    st.subheader("Contabilidad adicional")
    contab_df = st.data_editor(
        st.session_state["contabilidad_df"],
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="contab_editor",
    )
    st.session_state["contabilidad_df"] = contab_df.copy()

mix_df = ensure_mix_df(st.session_state["mix_df"], inputs)
mix_df["Ingresos netos línea (€)"] = mix_df["Unidades"] * mix_df["Precio unitario (€)"] * (1 - inputs["caida_precios_pct"])
mix_df["m² vendibles línea"] = mix_df["Unidades"] * mix_df["m² vendibles por unidad"]

sup_util_br = inputs["sup_construida_br_m2"] * (1 - inputs["pct_circulacion_br"])
garajes_estimados = safe_int(sup_util_br / inputs["m2_por_plaza"]) if inputs["m2_por_plaza"] else 0
trasteros_estimados = safe_int(garajes_estimados * inputs["ratio_trasteros_plaza"])

ingresos_viviendas = mix_df["Ingresos netos línea (€)"].sum()
ingresos_garajes = inputs["num_garajes"] * inputs["precio_garaje"]
ingresos_trasteros = inputs["num_trasteros"] * inputs["precio_trastero"]
ingresos_totales = ingresos_viviendas + ingresos_garajes + ingresos_trasteros

costs_df = ensure_costs_df(st.session_state["costs_df_user"]).copy()
auto_values = {
    "Precio suelo": inputs["precio_suelo"],
    "IVA compra suelo": inputs["precio_suelo"] * inputs["iva_compra_suelo_pct"],
    "AJD compra suelo": inputs["precio_suelo"] * inputs["ajd_pct"],
    "ICIO": inputs["pem"] * 0.04,
    "Construcción sobre rasante": inputs["pem_sr"] * (1 + inputs["sobrecoste_pct"]),
    "Construcción bajo rasante": inputs["pem_br"] * (1 + inputs["sobrecoste_pct"]),
    "Imprevistos / modificados": inputs["pem"] * 0.03,
    "Intereses": (inputs["pem"] + inputs["precio_suelo"]) * inputs["interes_anual_pct"] * max(inputs["mes_entrega"], 1) / 24,
}
for idx in costs_df.index:
    concepto = costs_df.at[idx, "Concepto"]
    if concepto in auto_values:
        costs_df.at[idx, "Coste base (€)"] = auto_values[concepto]

costs_df["Coste (€)"] = pd.to_numeric(costs_df["Coste base (€)"], errors="coerce").fillna(0.0)
costs_df["% PEM"] = costs_df["Coste (€)"] / inputs["pem"] if inputs["pem"] else 0.0

contab_df = st.session_state["contabilidad_df"].copy()
if not contab_df.empty:
    if "Importe (€)" not in contab_df.columns:
        contab_df["Importe (€)"] = 0.0
    contab_df["Importe (€)"] = pd.to_numeric(contab_df["Importe (€)"], errors="coerce").fillna(0.0)
    coste_contabilidad_adicional = contab_df["Importe (€)"].sum()
else:
    coste_contabilidad_adicional = 0.0

coste_total_sin_iva_compra = costs_df["Coste (€)"].sum() + coste_contabilidad_adicional
coste_total_con_iva = coste_total_sin_iva_compra
margen_bruto = ingresos_totales - coste_total_sin_iva_compra
margen_sobre_ventas = margen_bruto / ingresos_totales if ingresos_totales else 0.0

precio_m2_construccion_sr = inputs["pem_sr"] / inputs["sup_construida_sr_m2"] if inputs["sup_construida_sr_m2"] else 0.0
precio_m2_construccion_br = inputs["pem_br"] / inputs["sup_construida_br_m2"] if inputs["sup_construida_br_m2"] else 0.0
precio_m2_construccion_total = inputs["pem"] / inputs["sup_construida_total_m2"] if inputs["sup_construida_total_m2"] else 0.0
precio_m2_coste_total_vendible = coste_total_sin_iva_compra / inputs["sup_vendible_m2"] if inputs["sup_vendible_m2"] else 0.0
precio_m2_venta_vendible = ingresos_totales / inputs["sup_vendible_m2"] if inputs["sup_vendible_m2"] else 0.0
margen_m2_vendible = margen_bruto / inputs["sup_vendible_m2"] if inputs["sup_vendible_m2"] else 0.0
repercusion_suelo_m2_vendible = inputs["precio_suelo"] / inputs["sup_vendible_m2"] if inputs["sup_vendible_m2"] else 0.0
repercusion_suelo_m2_sr = inputs["precio_suelo"] / inputs["sup_construida_sr_m2"] if inputs["sup_construida_sr_m2"] else 0.0

risk_df = ensure_risk_df(st.session_state["risk_df"])
risk_points = int(risk_df["Puntos"].sum())
global_risk = "Alto" if risk_points >= 8 else "Medio" if risk_points >= 4 else "Bajo"

alertas: List[str] = []
if mix_df["Unidades"].sum() != inputs["num_viviendas"]:
    alertas.append("El mix comercial no suma el número total de viviendas.")
if abs(mix_df["m² vendibles línea"].sum() - inputs["sup_vendible_m2"]) > 0.5:
    alertas.append("El mix comercial no cuadra con los m² vendibles.")
if margen_sobre_ventas < 0.15:
    alertas.append("Margen sobre ventas inferior al 15%.")
if inputs["num_garajes"] > garajes_estimados and inputs["sup_construida_br_m2"] > 0:
    alertas.append("Las plazas manuales superan la capacidad estimada del bajo rasante.")
if inputs["num_trasteros"] > safe_int(sup_util_br / inputs["m2_por_trastero"]) and inputs["sup_construida_br_m2"] > 0:
    alertas.append("Los trasteros manuales superan la capacidad estimada por superficie.")


def build_cashflow(costes_df: pd.DataFrame, ingresos_totales: float, inputs: dict) -> pd.DataFrame:
    last_month = max(inputs["mes_entrega"], inputs["mes_inicio_obra"] + 12, 12)
    months = list(range(last_month + 1))
    cf = pd.DataFrame({"Mes": months})
    cf["Entradas clientes (€)"] = 0.0
    cf["Entradas préstamo (€)"] = 0.0
    cf["Salidas (€)"] = 0.0

    reserva = inputs["mes_comercializacion"]
    contrato = min(inputs["mes_entrega"] - 3, max(reserva + 1, reserva))
    escritura = inputs["mes_entrega"]
    for mes, p_in in [(reserva, 0.10), (contrato, 0.20), (escritura, 0.70)]:
        if mes in cf["Mes"].values:
            cf.loc[cf["Mes"] == mes, "Entradas clientes (€)"] += ingresos_totales * p_in

    def add_outflow(month_from: int, month_to: int, total: float):
        month_from = int(max(month_from, 0))
        month_to = int(max(month_to, month_from))
        n = month_to - month_from + 1
        if n <= 0:
            return
        per = total / n
        cf.loc[(cf["Mes"] >= month_from) & (cf["Mes"] <= month_to), "Salidas (€)"] += per

    for _, row in costes_df.iterrows():
        cost = safe_float(row["Coste (€)"])
        fase = row["Fase"]
        if fase == "Compra suelo":
            add_outflow(inputs["mes_compra"], inputs["mes_compra"], cost)
        elif fase in ["Due diligence", "Proyecto", "Licencia"]:
            add_outflow(inputs["mes_compra"], inputs["mes_inicio_obra"], cost)
        elif fase == "Preobra":
            add_outflow(max(inputs["mes_inicio_obra"] - 1, 0), inputs["mes_inicio_obra"], cost)
        elif fase in ["Obra", "Financiación"]:
            add_outflow(inputs["mes_inicio_obra"], inputs["mes_entrega"], cost)
        elif fase == "Comercialización":
            add_outflow(inputs["mes_comercializacion"], inputs["mes_entrega"], cost)
        else:
            add_outflow(inputs["mes_entrega"], inputs["mes_entrega"], cost)

    deficit = 0.0
    loan_entries = []
    for _, row in cf.iterrows():
        neto_sin_prestamo = row["Entradas clientes (€)"] - row["Salidas (€)"]
        deficit += -neto_sin_prestamo
        if deficit < 0:
            deficit = 0.0
        loan_entries.append(max(0.0, deficit))
    prev = 0.0
    real_draws = []
    for val in loan_entries:
        draw = max(0.0, val - prev)
        real_draws.append(draw)
        prev = val
    cf["Entradas préstamo (€)"] = real_draws
    cf["Entradas (€)"] = cf["Entradas clientes (€)"] + cf["Entradas préstamo (€)"]
    cf["Flujo neto (€)"] = cf["Entradas (€)"] - cf["Salidas (€)"]
    cf["Flujo acumulado (€)"] = cf["Flujo neto (€)"].cumsum()
    return cf


cashflow_df = build_cashflow(costs_df, ingresos_totales, inputs)
cover_ratio = ingresos_totales / coste_total_sin_iva_compra if coste_total_sin_iva_compra else 0.0
if margen_sobre_ventas >= 0.18 and global_risk != "Alto" and cover_ratio >= 1.20:
    dictamen_titulo, dictamen_texto = "Viable", "Promoción defendible con margen sólido y estructura razonable."
elif margen_sobre_ventas >= 0.15 and cover_ratio >= 1.10:
    dictamen_titulo, dictamen_texto = "Viable con control estricto", "La promoción puede defenderse, pero exige disciplina total."
else:
    dictamen_titulo, dictamen_texto = "No recomendable", "El margen es frágil o la estructura de costes no es suficientemente robusta."

model = {
    "sales_mix_df": mix_df.copy(),
    "costes_df": costs_df.copy(),
    "ingresos_viviendas": ingresos_viviendas,
    "ingresos_garajes": ingresos_garajes,
    "ingresos_trasteros": ingresos_trasteros,
    "ingresos_totales": ingresos_totales,
    "coste_contabilidad_adicional": coste_contabilidad_adicional,
    "coste_total_sin_iva_compra": coste_total_sin_iva_compra,
    "coste_total_con_iva": coste_total_con_iva,
    "margen_bruto": margen_bruto,
    "margen_sobre_ventas": margen_sobre_ventas,
    "garajes_estimados": garajes_estimados,
    "trasteros_estimados": trasteros_estimados,
    "precio_m2_construccion_sr": precio_m2_construccion_sr,
    "precio_m2_construccion_br": precio_m2_construccion_br,
    "precio_m2_construccion_total": precio_m2_construccion_total,
    "precio_m2_coste_total_vendible": precio_m2_coste_total_vendible,
    "precio_m2_venta_vendible": precio_m2_venta_vendible,
    "margen_m2_vendible": margen_m2_vendible,
    "repercusion_suelo_m2_vendible": repercusion_suelo_m2_vendible,
    "repercusion_suelo_m2_sr": repercusion_suelo_m2_sr,
    "ratios": {"cover_ratio": cover_ratio},
}

with tab0:
    st.title("Estudio de viabilidad promotor")
    row1 = st.columns(5)
    row1[0].metric("Ingresos totales", eur(model["ingresos_totales"]))
    row1[1].metric("Coste total", eur(model["coste_total_sin_iva_compra"]))
    row1[2].metric("Margen bruto", eur(model["margen_bruto"]))
    row1[3].metric("Margen sobre ventas", pct(model["margen_sobre_ventas"]))
    row1[4].metric("Cobertura ventas/coste", ratio(model["ratios"]["cover_ratio"]))

    row2 = st.columns(5)
    row2[0].metric("Garajes estimados por superficie", str(model["garajes_estimados"]))
    row2[1].metric("Trasteros estimados por ratio", str(model["trasteros_estimados"]))
    row2[2].metric("Riesgo global", global_risk)
    row2[3].metric("PEM total", eur(inputs["pem"]))
    row2[4].metric("m² vendibles", f"{inputs['sup_vendible_m2']:,.0f}".replace(",", "."))

    ficha = pd.DataFrame([
        ["Activo", inputs["activo"]],
        ["Referencia catastral", inputs["referencia_catastral"]],
        ["Nº viviendas", str(inputs["num_viviendas"])],
        ["Nº garajes", str(inputs["num_garajes"])],
        ["Nº trasteros", str(inputs["num_trasteros"])],
        ["PEM", eur(inputs["pem"])],
        ["Mes licencia", str(inputs["mes_licencia"])],
        ["Mes inicio obra", str(inputs["mes_inicio_obra"])],
        ["Mes entrega", str(inputs["mes_entrega"])],
    ], columns=["Campo", "Valor"])
    st.dataframe(display_df(ficha), width="stretch", hide_index=True)

    st.subheader("Dictamen automático")
    if dictamen_titulo == "Viable":
        st.success(f"{dictamen_titulo}: {dictamen_texto}")
    elif dictamen_titulo == "Viable con control estricto":
        st.warning(f"{dictamen_titulo}: {dictamen_texto}")
    else:
        st.error(f"{dictamen_titulo}: {dictamen_texto}")

    if alertas:
        st.markdown("**Alertas críticas**")
        for alerta in alertas:
            st.write(f"- {alerta}")

with tab1:
    mix_resumen = model["sales_mix_df"][["Tipología", "Unidades", "Precio unitario (€)", "Ingresos netos línea (€)", "m² vendibles línea"]].copy()
    mix_resumen["Precio unitario (€)"] = mix_resumen["Precio unitario (€)"].map(eur)
    mix_resumen["Ingresos netos línea (€)"] = mix_resumen["Ingresos netos línea (€)"].map(eur)
    mix_resumen["m² vendibles línea"] = mix_resumen["m² vendibles línea"].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.subheader("Resumen del mix")
    st.dataframe(display_df(mix_resumen), width="stretch", hide_index=True)

with tab2:
    show_costs = model["costes_df"][["Fase", "Hito", "Concepto", "Coste (€)", "% PEM"]].copy()
    show_costs["Coste (€)"] = show_costs["Coste (€)"].map(eur)
    show_costs["% PEM"] = show_costs["% PEM"].map(pct)
    st.dataframe(display_df(show_costs), width="stretch", hide_index=True)

with tab3:
    cf_show = cashflow_df.copy()
    for col in ["Entradas clientes (€)", "Entradas préstamo (€)", "Entradas (€)", "Salidas (€)", "Flujo neto (€)", "Flujo acumulado (€)"]:
        cf_show[col] = cf_show[col].map(eur)
    st.dataframe(display_df(cf_show), width="stretch", hide_index=True)
    st.line_chart(cashflow_df.set_index("Mes")[["Entradas (€)", "Salidas (€)", "Flujo acumulado (€)"]])

with tab4:
    st.dataframe(display_df(risk_df), width="stretch", hide_index=True)

with tab5:
    ratios_df = pd.DataFrame([
        ["m² construidos sobre rasante", f"{inputs['sup_construida_sr_m2']:,.0f} m²".replace(",", ".")],
        ["m² construidos bajo rasante", f"{inputs['sup_construida_br_m2']:,.0f} m²".replace(",", ".")],
        ["m² construidos totales", f"{inputs['sup_construida_total_m2']:,.0f} m²".replace(",", ".")],
        ["m² vendibles", f"{inputs['sup_vendible_m2']:,.0f} m²".replace(",", ".")],
        ["Coste construcción sobre rasante", eur_m2(model["precio_m2_construccion_sr"])],
        ["Coste construcción bajo rasante", eur_m2(model["precio_m2_construccion_br"])],
        ["Coste construcción total", eur_m2(model["precio_m2_construccion_total"])],
        ["Coste total vendible", eur_m2(model["precio_m2_coste_total_vendible"])],
        ["Venta vendible", eur_m2(model["precio_m2_venta_vendible"])],
        ["Margen vendible", eur_m2(model["margen_m2_vendible"])],
        ["Repercusión suelo vendible", eur_m2(model["repercusion_suelo_m2_vendible"])],
        ["Repercusión suelo SR", eur_m2(model["repercusion_suelo_m2_sr"])],
    ], columns=["Concepto", "Valor"])
    st.dataframe(display_df(ratios_df), width="stretch", hide_index=True)

with tab6:
    resumen_df = pd.DataFrame([
        ["Activo", inputs["activo"]],
        ["Referencia catastral", inputs["referencia_catastral"]],
        ["PEM", eur(inputs["pem"])],
        ["Ingresos totales", eur(model["ingresos_totales"])],
        ["Coste total", eur(model["coste_total_sin_iva_compra"])],
        ["Contabilidad adicional", eur(model["coste_contabilidad_adicional"])],
        ["Margen bruto", eur(model["margen_bruto"])],
        ["Margen sobre ventas", pct(model["margen_sobre_ventas"])],
        ["Cobertura ventas/coste", ratio(model["ratios"]["cover_ratio"])],
        ["Riesgo global", global_risk],
        ["Puntos de riesgo", str(risk_points)],
    ], columns=["Campo", "Valor"])
    st.dataframe(display_df(resumen_df), width="stretch", hide_index=True)

with tab7:
    export_costs = model["costes_df"].copy()
    export_mix = model["sales_mix_df"].copy()
    export_risk = risk_df.copy()
    export_summary = pd.DataFrame([
        {"Campo": "Activo", "Valor": inputs["activo"]},
        {"Campo": "Referencia catastral", "Valor": inputs["referencia_catastral"]},
        {"Campo": "PEM", "Valor": inputs["pem"]},
        {"Campo": "Ingresos totales", "Valor": model["ingresos_totales"]},
        {"Campo": "Coste total", "Valor": model["coste_total_sin_iva_compra"]},
        {"Campo": "Margen bruto", "Valor": model["margen_bruto"]},
        {"Campo": "Margen sobre ventas", "Valor": model["margen_sobre_ventas"]},
        {"Campo": "Riesgo global", "Valor": global_risk},
    ])
    content, mime, filename = to_excel_bytes({
        "Resumen": export_summary,
        "Mix comercial": export_mix,
        "Costes": export_costs,
        "Cashflow": cashflow_df,
        "Riesgo": export_risk,
    })
    st.download_button("Descargar Excel / ZIP", data=content, file_name=filename, mime=mime, use_container_width=True)

    pdf_bytes = build_pdf_bytes(export_summary)
    if pdf_bytes:
        st.download_button("Descargar PDF resumen", data=pdf_bytes, file_name="resumen_viabilidad.pdf", mime="application/pdf", use_container_width=True)
