# -*- coding: utf-8 -*-
import io
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Estudio Viabilidad Proyecto by Gpg",
    page_icon="🏗️",
    layout="wide",
)

st.markdown("""
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1480px;}
h1, h2, h3 {letter-spacing: -0.02em;}
[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(18,25,40,0.96), rgba(10,14,24,0.96));
    border: 1px solid rgba(255,255,255,0.08);
    padding: 18px 18px 14px 18px;
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
div[data-testid="stMetricLabel"] {font-weight: 600;}
div[data-testid="stMetricValue"] {font-size: 1.75rem;}
.stTabs [data-baseweb="tab-list"] {gap: 8px;}
.stTabs [data-baseweb="tab"] {border-radius: 12px 12px 0 0; padding-left: 18px; padding-right: 18px;}
.gpg-card {
    background: linear-gradient(180deg, rgba(17,24,39,0.97), rgba(8,12,20,0.97));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.16);
}
.gpg-kicker {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.72;
    margin-bottom: 6px;
}
.gpg-big {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.05;
}
.gpg-sub {
    opacity: 0.84;
    margin-top: 8px;
    font-size: 0.97rem;
}
.small-note {
    opacity: 0.78;
    font-size: 0.90rem;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_INPUTS = {
    "activo": "C/ Los Cincuenta 3, Alicante",
    "referencia_catastral": "7653302YH1475D0001AL",
    "parcela_m2": 311.0,
    "sup_construida_sr_m2": 1210.0,     # sobre rasante
    "sup_construida_br_m2": 260.0,      # bajo rasante
    "sup_vendible_m2": 1210.0,          # útil comercial / vendible asumida
    "pem": 1_475_000.0,
    "precio_suelo": 315_000.0,
    "iva_compra_suelo_pct": 0.21,
    "ajd_pct": 0.015,
    "precio_vivienda": 245_000.0,
    "num_viviendas": 11,
    "precio_garaje": 25_000.0,
    "num_garajes": 10,
    "precio_trastero": 3_500.0,
    "num_trasteros": 10,
}
BASE_PEM = DEFAULT_INPUTS["pem"]

SCENARIOS = {
    "Base": {
        "mes_compra": 0,
        "mes_licencia": 6,
        "mes_inicio_obra": 7,
        "mes_venta_4v": 10,
        "mes_entrega": 22,
        "sobrecoste_pct": 0.00,
        "caida_precios_pct": 0.00,
        "interes_anual_pct": 0.06,
    },
    "Adverso": {
        "mes_compra": 0,
        "mes_licencia": 8,
        "mes_inicio_obra": 9,
        "mes_venta_4v": 12,
        "mes_entrega": 26,
        "sobrecoste_pct": 0.08,
        "caida_precios_pct": 0.03,
        "interes_anual_pct": 0.075,
    },
}

PROGRAM_PRESETS = {
    "10 viviendas": {
        "num_viviendas": 10,
        "num_garajes": 10,
        "num_trasteros": 10,
        "precio_vivienda": 245_000.0,
        "precio_garaje": 25_000.0,
        "precio_trastero": 3_500.0,
        "sup_construida_sr_m2": 1160.0,
        "sup_construida_br_m2": 260.0,
        "sup_vendible_m2": 1160.0,
    },
    "11 viviendas": {
        "num_viviendas": 11,
        "num_garajes": 10,
        "num_trasteros": 10,
        "precio_vivienda": 245_000.0,
        "precio_garaje": 25_000.0,
        "precio_trastero": 3_500.0,
        "sup_construida_sr_m2": 1210.0,
        "sup_construida_br_m2": 260.0,
        "sup_vendible_m2": 1210.0,
    },
}

COST_ITEMS = [
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Abogado inmobiliario + mercantil", "minimo": 3000.0, "maximo": 7000.0, "base": 5000.0, "obs": "Revisión contractual compra aplazada"},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Revisión fiscal/notarial compra", "minimo": 800.0, "maximo": 2000.0, "base": 1400.0, "obs": "Validar IVA/AJD y escritura"},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Nota simple / cargas / contraste registral", "minimo": 300.0, "maximo": 1000.0, "base": 650.0, "obs": ""},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Anteproyecto de encaje", "minimo": 4000.0, "maximo": 10000.0, "base": 7000.0, "obs": ""},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Topográfico", "minimo": 800.0, "maximo": 1800.0, "base": 1300.0, "obs": "Pendiente"},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Geotécnico", "minimo": 2500.0, "maximo": 5500.0, "base": 4000.0, "obs": "Pendiente"},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Primer pago suelo", "minimo": 100000.0, "maximo": 100000.0, "base": 100000.0, "obs": "Parte del precio aplazado"},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "IVA compra suelo", "minimo": None, "maximo": None, "base": 0.0, "obs": "Calculado sobre precio suelo"},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "AJD compra suelo", "minimo": None, "maximo": None, "base": 0.0, "obs": "Calculado sobre precio suelo"},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Notaría compraventa", "minimo": 1200.0, "maximo": 2500.0, "base": 1850.0, "obs": ""},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Registro Propiedad", "minimo": 800.0, "maximo": 1800.0, "base": 1300.0, "obs": ""},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Gestoría compraventa", "minimo": 300.0, "maximo": 700.0, "base": 500.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Proyecto básico", "minimo": 18000.0, "maximo": 28000.0, "base": 23000.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Proyecto ejecución", "minimo": 22000.0, "maximo": 34000.0, "base": 28000.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Dirección de obra", "minimo": 12000.0, "maximo": 18000.0, "base": 15000.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Dirección de ejecución", "minimo": 10000.0, "maximo": 16000.0, "base": 13000.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "CSS", "minimo": 4000.0, "maximo": 7000.0, "base": 5500.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Estudios técnicos complementarios", "minimo": 4000.0, "maximo": 9000.0, "base": 6500.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Laboratorio / control calidad", "minimo": 5000.0, "maximo": 10000.0, "base": 7500.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "OCT", "minimo": 4000.0, "maximo": 9000.0, "base": 6500.0, "obs": "Si banco/seguro lo exige"},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Solicitud licencia", "concepto": "Tasas licencia / expedientes", "minimo": 1500.0, "maximo": 3500.0, "base": 2500.0, "obs": ""},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Solicitud licencia", "concepto": "ICIO", "minimo": 54000.0, "maximo": 64000.0, "base": 59000.0, "obs": "Base PEM prudente; impuesto fuera del PEM"},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Concesión licencia", "concepto": "Pago aplazado suelo", "minimo": 50000.0, "maximo": 50000.0, "base": 50000.0, "obs": "Parte del precio"},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "A 6 meses si no licencia", "concepto": "Pago adicional obligado", "minimo": 50000.0, "maximo": 50000.0, "base": 50000.0, "obs": "Parte del precio"},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Proyecto / trámite demolición", "minimo": 1500.0, "maximo": 4000.0, "base": 2750.0, "obs": ""},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Demolición", "minimo": 20000.0, "maximo": 40000.0, "base": 30000.0, "obs": ""},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Residuos demolición", "minimo": 6000.0, "maximo": 12000.0, "base": 9000.0, "obs": ""},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Contingencia amianto", "minimo": 0.0, "maximo": 20000.0, "base": 10000.0, "obs": "Si aparece"},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Vallado / limpieza / implantación", "minimo": 4000.0, "maximo": 8000.0, "base": 6000.0, "obs": ""},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Apeos / protección medianeras", "minimo": 5000.0, "maximo": 15000.0, "base": 10000.0, "obs": ""},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Tasación ECO", "minimo": 2000.0, "maximo": 4000.0, "base": 3000.0, "obs": ""},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Comisión apertura / estudio", "minimo": 8000.0, "maximo": 18000.0, "base": 13000.0, "obs": ""},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Monitoring técnico banco", "minimo": 5000.0, "maximo": 12000.0, "base": 8500.0, "obs": ""},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Notaría / registro préstamo", "minimo": 2000.0, "maximo": 5000.0, "base": 3500.0, "obs": ""},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Durante obra", "concepto": "Intereses", "minimo": 95000.0, "maximo": 180000.0, "base": 137500.0, "obs": "Muy sensible al banco/plazo"},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Durante obra", "concepto": "Otras comisiones bancarias", "minimo": 2000.0, "maximo": 8000.0, "base": 5000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "Construcción sobre rasante", "minimo": 1120000.0, "maximo": 1300000.0, "base": 1210000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "1 sótano (10 plazas + 10 trasteros)", "minimo": 220000.0, "maximo": 300000.0, "base": 260000.0, "obs": "Opción base recomendada"},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "Ascensor", "minimo": 28000.0, "maximo": 42000.0, "base": 35000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Acometidas definitivas", "minimo": 15000.0, "maximo": 35000.0, "base": 25000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Urbanización interior / remates", "minimo": 20000.0, "maximo": 45000.0, "base": 32500.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Medios auxiliares / grúa / casetas", "minimo": 20000.0, "maximo": 40000.0, "base": 30000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Seguridad y salud ejecución", "minimo": 10000.0, "maximo": 18000.0, "base": 14000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Residuos de obra", "minimo": 12000.0, "maximo": 22000.0, "base": 17000.0, "obs": ""},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Imprevistos / modificados", "minimo": 90000.0, "maximo": 150000.0, "base": 120000.0, "obs": ""},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Al vender 4 viviendas", "concepto": "Pago aplazado suelo", "minimo": 50000.0, "maximo": 50000.0, "base": 50000.0, "obs": "Parte del precio"},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Marketing / renders / dossier", "minimo": 6000.0, "maximo": 15000.0, "base": 10500.0, "obs": ""},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Contratos privados / jurídico comercial", "minimo": 3000.0, "maximo": 7000.0, "base": 5000.0, "obs": ""},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Avales cantidades anticipadas", "minimo": 4000.0, "maximo": 12000.0, "base": 8000.0, "obs": ""},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Fin promoción", "concepto": "Resto precio suelo", "minimo": 65000.0, "maximo": 65000.0, "base": 65000.0, "obs": "Parte del precio"},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Primera ocupación / cierre admin.", "minimo": 500.0, "maximo": 1500.0, "base": 1000.0, "obs": ""},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Seguro decenal", "minimo": 8000.0, "maximo": 16000.0, "base": 12000.0, "obs": ""},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Obra nueva y división horizontal", "minimo": 6000.0, "maximo": 14000.0, "base": 10000.0, "obs": ""},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Cancelaciones / novaciones / entrega", "minimo": 2000.0, "maximo": 7000.0, "base": 4500.0, "obs": ""},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Postentrega", "concepto": "Repasos / postventa inicial", "minimo": 6000.0, "maximo": 18000.0, "base": 12000.0, "obs": ""},
]

RISK_ITEMS = [
    {"categoria": "Fiscalidad compra", "estado": "Pendiente validación escrita", "puntos": 3, "comentario": "IVA 21% vs 10% debe quedar por escrito"},
    {"categoria": "Contrato suelo", "estado": "Cláusula pérdida de cantidades", "puntos": 3, "comentario": "Penalización dura"},
    {"categoria": "Topográfico", "estado": "No disponible", "puntos": 2, "comentario": "Pendiente"},
    {"categoria": "Geotécnico", "estado": "No disponible", "puntos": 3, "comentario": "Clave por sótano"},
    {"categoria": "Sótano", "estado": "Encaje pendiente de layout", "puntos": 2, "comentario": "Conviene validar 10+10"},
    {"categoria": "Comercialización", "estado": "Precios fijados", "puntos": 1, "comentario": "Demanda razonable pero no cerrada"},
    {"categoria": "Financiación", "estado": "Sin term sheet bancario", "puntos": 2, "comentario": "Depende de licencia y preventas"},
]

PHASE_ALLOCATION = {
    "Fase 0 · Due Diligence y viabilidad previa": "due_diligence",
    "Fase 1 · Adquisición del suelo": "compra",
    "Fase 2 · Proyecto, licencias y tramitación técnica": "proyecto_licencia",
    "Fase 3 · Preparación del solar y preobra": "pre_obra",
    "Fase 4 · Financiación de la promoción": "financiacion",
    "Fase 5 · Ejecución de obra": "obra",
    "Fase 6 · Comercialización y ventas": "comercializacion",
    "Fase 7 · Entrega, cierre y postventa": "cierre",
}


def eur(v: float) -> str:
    return f"€{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    return f"{v * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def eur_m2(v: float) -> str:
    return f"€{v:,.0f}/m²".replace(",", "X").replace(".", ",").replace("X", ".")


def ratio(v: float) -> str:
    return f"{v:,.2f}x".replace(",", "X").replace(".", ",").replace("X", ".")


def display_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve una copia segura para Streamlit/Arrow, convirtiendo columnas problemáticas
    a texto sin tocar los dataframes numéricos usados para gráficos o cálculos.
    """
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].fillna("").astype(str)
    return out


def riesgo_label(puntos: int) -> str:
    if puntos >= 3:
        return "Alto"
    if puntos == 2:
        return "Medio"
    return "Bajo"


def init_state() -> None:
    if "program_preset" not in st.session_state:
        st.session_state["program_preset"] = "11 viviendas"
    if "editable_costs_store" not in st.session_state:
        st.session_state["editable_costs_store"] = build_base_cost_df("Base")
    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0


def build_base_cost_df(escenario: str) -> pd.DataFrame:
    rows = []
    for item in COST_ITEMS:
        coste = item["base"] if escenario == "Base" else (item["maximo"] if item["maximo"] is not None else item["base"])
        rows.append(
            {
                "Fase": item["fase"],
                "Hito": item["hito"],
                "Concepto": item["concepto"],
                "Coste editable (€)": float(coste),
                "Observaciones": item["obs"],
                "Bucket": PHASE_ALLOCATION.get(item["fase"], "otros"),
                "Auto": item["concepto"] in {"IVA compra suelo", "AJD compra suelo"},
            }
        )
    return pd.DataFrame(rows)


def apply_program_preset(preset_name: str) -> None:
    preset = PROGRAM_PRESETS[preset_name]
    st.session_state["program_preset"] = preset_name
    for k, v in preset.items():
        st.session_state[k] = v


def pem_scaled_cost(concepto: str, coste_base: float, inputs: dict) -> float:
    if BASE_PEM <= 0:
        return coste_base
    factor_pem = inputs["pem"] / BASE_PEM
    conceptos_sensibles_pem = {
        "ICIO",
        "Construcción sobre rasante",
        "1 sótano (10 plazas + 10 trasteros)",
        "Ascensor",
        "Acometidas definitivas",
        "Urbanización interior / remates",
        "Medios auxiliares / grúa / casetas",
        "Seguridad y salud ejecución",
        "Residuos de obra",
        "Imprevistos / modificados",
        "Proyecto básico",
        "Proyecto ejecución",
        "Dirección de obra",
        "Dirección de ejecución",
        "CSS",
        "Estudios técnicos complementarios",
        "Laboratorio / control calidad",
        "OCT",
    }
    if concepto in conceptos_sensibles_pem:
        return coste_base * factor_pem
    return coste_base


def build_inputs() -> dict:
    st.sidebar.header("Control del modelo")

    escenario = st.sidebar.selectbox("Escenario", list(SCENARIOS.keys()), index=0)
    active = SCENARIOS[escenario]

    st.sidebar.subheader("Preset de programa")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button("Preset 10 viviendas", use_container_width=True):
            apply_program_preset("10 viviendas")
    with c2:
        if st.button("Preset 11 viviendas", use_container_width=True):
            apply_program_preset("11 viviendas")

    st.sidebar.caption(f"Preset activo: **{st.session_state.get('program_preset', '11 viviendas')}**")

    st.sidebar.subheader("Activo")
    activo = st.sidebar.text_input("Activo", DEFAULT_INPUTS["activo"])
    rc = st.sidebar.text_input("Referencia catastral", DEFAULT_INPUTS["referencia_catastral"])
    parcela_m2 = st.sidebar.number_input("Parcela catastral (m²)", min_value=0.0, value=float(DEFAULT_INPUTS["parcela_m2"]), step=1.0)

    st.sidebar.subheader("Superficies reales del modelo")
    sup_construida_sr_m2 = st.sidebar.number_input(
        "m² construidos sobre rasante",
        min_value=0.0,
        value=float(st.session_state.get("sup_construida_sr_m2", DEFAULT_INPUTS["sup_construida_sr_m2"])),
        step=10.0,
    )
    sup_construida_br_m2 = st.sidebar.number_input(
        "m² construidos bajo rasante",
        min_value=0.0,
        value=float(st.session_state.get("sup_construida_br_m2", DEFAULT_INPUTS["sup_construida_br_m2"])),
        step=10.0,
    )
    sup_vendible_m2 = st.sidebar.number_input(
        "m² vendibles",
        min_value=0.0,
        value=float(st.session_state.get("sup_vendible_m2", DEFAULT_INPUTS["sup_vendible_m2"])),
        step=10.0,
        help="Introduce la superficie comercializable real. Así el modelo deja de mezclar parcela con construcción.",
    )

    st.sidebar.subheader("Inputs económicos")
    pem = st.sidebar.number_input("PEM referencia (€)", min_value=0.0, value=float(DEFAULT_INPUTS["pem"]), step=25_000.0)
    precio_suelo = st.sidebar.number_input("Precio suelo (€)", min_value=0.0, value=float(DEFAULT_INPUTS["precio_suelo"]), step=5_000.0)
    iva_compra = st.sidebar.number_input("IVA compra suelo (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["iva_compra_suelo_pct"] * 100, step=0.5) / 100
    ajd = st.sidebar.number_input("AJD compra (%)", min_value=0.0, max_value=100.0, value=DEFAULT_INPUTS["ajd_pct"] * 100, step=0.1) / 100

    st.sidebar.subheader("Programa de ventas")
    num_viviendas = st.sidebar.number_input("Nº viviendas", min_value=0, value=int(st.session_state.get("num_viviendas", DEFAULT_INPUTS["num_viviendas"])), step=1)
    num_garajes = st.sidebar.number_input("Nº garajes", min_value=0, value=int(st.session_state.get("num_garajes", DEFAULT_INPUTS["num_garajes"])), step=1)
    num_trasteros = st.sidebar.number_input("Nº trasteros", min_value=0, value=int(st.session_state.get("num_trasteros", DEFAULT_INPUTS["num_trasteros"])), step=1)
    precio_vivienda = st.sidebar.number_input("Precio vivienda (€ / ud)", min_value=0.0, value=float(st.session_state.get("precio_vivienda", DEFAULT_INPUTS["precio_vivienda"])), step=5_000.0)
    precio_garaje = st.sidebar.number_input("Precio garaje (€ / ud)", min_value=0.0, value=float(st.session_state.get("precio_garaje", DEFAULT_INPUTS["precio_garaje"])), step=1_000.0)
    precio_trastero = st.sidebar.number_input("Precio trastero (€ / ud)", min_value=0.0, value=float(st.session_state.get("precio_trastero", DEFAULT_INPUTS["precio_trastero"])), step=500.0)

    st.sidebar.subheader("Calendario y sensibilidad")
    mes_licencia = st.sidebar.number_input("Mes licencia", min_value=0, value=int(active["mes_licencia"]), step=1)
    mes_inicio_obra = st.sidebar.number_input("Mes inicio obra", min_value=0, value=int(active["mes_inicio_obra"]), step=1)
    mes_venta_4v = st.sidebar.number_input("Mes venta 4 viviendas", min_value=0, value=int(active["mes_venta_4v"]), step=1)
    mes_entrega = st.sidebar.number_input("Mes entrega / escrituras", min_value=1, value=int(active["mes_entrega"]), step=1)
    sobrecoste_pct = st.sidebar.number_input("Sobrecoste costes obra (%)", min_value=0.0, max_value=100.0, value=active["sobrecoste_pct"] * 100, step=0.5) / 100
    caida_precios_pct = st.sidebar.number_input("Caída precio ventas (%)", min_value=0.0, max_value=100.0, value=active["caida_precios_pct"] * 100, step=0.5) / 100
    interes_anual_pct = st.sidebar.number_input("Interés anual préstamo (%)", min_value=0.0, max_value=100.0, value=active["interes_anual_pct"] * 100, step=0.25) / 100

    return {
        "escenario": escenario,
        "activo": activo,
        "referencia_catastral": rc,
        "parcela_m2": parcela_m2,
        "sup_construida_sr_m2": sup_construida_sr_m2,
        "sup_construida_br_m2": sup_construida_br_m2,
        "sup_construida_total_m2": sup_construida_sr_m2 + sup_construida_br_m2,
        "sup_vendible_m2": sup_vendible_m2,
        "pem": pem,
        "precio_suelo": precio_suelo,
        "iva_compra": iva_compra,
        "ajd": ajd,
        "num_viviendas": num_viviendas,
        "num_garajes": num_garajes,
        "num_trasteros": num_trasteros,
        "precio_vivienda": precio_vivienda,
        "precio_garaje": precio_garaje,
        "precio_trastero": precio_trastero,
        "mes_compra": active["mes_compra"],
        "mes_licencia": mes_licencia,
        "mes_inicio_obra": mes_inicio_obra,
        "mes_venta_4v": mes_venta_4v,
        "mes_entrega": mes_entrega,
        "sobrecoste_pct": sobrecoste_pct,
        "caida_precios_pct": caida_precios_pct,
        "interes_anual_pct": interes_anual_pct,
    }


def build_cost_df(inputs: dict, edited_df: pd.DataFrame) -> pd.DataFrame:
    df = edited_df.copy()
    if "Auto" not in df.columns:
        df["Auto"] = False
    if "Bucket" not in df.columns:
        df["Bucket"] = df["Fase"].map(PHASE_ALLOCATION).fillna("otros")

    df["Coste (€)"] = df["Coste editable (€)"]
    df["Coste (€)"] = df.apply(lambda row: pem_scaled_cost(row["Concepto"], row["Coste (€)"], inputs), axis=1)

    obra_variable = df["Fase"].isin(["Fase 2 · Proyecto, licencias y tramitación técnica", "Fase 4 · Financiación de la promoción", "Fase 5 · Ejecución de obra"])
    df.loc[obra_variable, "Coste (€)"] = df.loc[obra_variable, "Coste (€)"] * (1 + inputs["sobrecoste_pct"])

    iva_compra_suelo = inputs["precio_suelo"] * inputs["iva_compra"]
    ajd_compra_suelo = inputs["precio_suelo"] * inputs["ajd"]

    def override(concepto: str, valor: float) -> None:
        mask = df["Concepto"].eq(concepto)
        if mask.any():
            df.loc[mask, "Coste (€)"] = valor
            df.loc[mask, "Coste editable (€)"] = valor

    override("IVA compra suelo", iva_compra_suelo)
    override("AJD compra suelo", ajd_compra_suelo)

    pagos_suelo = ["Primer pago suelo", "Pago aplazado suelo", "Pago adicional obligado", "Resto precio suelo"]
    suelo_actual = df.loc[df["Concepto"].isin(pagos_suelo), "Coste (€)"].sum()
    ajuste_suelo = inputs["precio_suelo"] - suelo_actual
    idx = df.index[df["Concepto"].eq("Resto precio suelo")]
    if len(idx):
        df.loc[idx[0], "Coste (€)"] = df.loc[idx[0], "Coste (€)"] + ajuste_suelo
        df.loc[idx[0], "Coste editable (€)"] = df.loc[idx[0], "Coste (€)"]

    df["% PEM"] = df["Coste (€)"] / inputs["pem"] if inputs["pem"] else 0.0
    return df


def compute_model(inputs: dict, edited_df: pd.DataFrame) -> dict:
    ingresos_viviendas = inputs["precio_vivienda"] * inputs["num_viviendas"] * (1 - inputs["caida_precios_pct"])
    ingresos_garajes = inputs["precio_garaje"] * inputs["num_garajes"] * (1 - inputs["caida_precios_pct"])
    ingresos_trasteros = inputs["precio_trastero"] * inputs["num_trasteros"] * (1 - inputs["caida_precios_pct"])
    ingresos_totales = ingresos_viviendas + ingresos_garajes + ingresos_trasteros

    costes_df = build_cost_df(inputs, edited_df)
    iva_compra_suelo = inputs["precio_suelo"] * inputs["iva_compra"]
    ajd_compra_suelo = inputs["precio_suelo"] * inputs["ajd"]

    coste_total_con_iva = float(costes_df["Coste (€)"].sum())
    coste_total_sin_iva_compra = coste_total_con_iva - iva_compra_suelo
    margen_bruto = ingresos_totales - coste_total_sin_iva_compra
    margen_sobre_ventas = margen_bruto / ingresos_totales if ingresos_totales else 0.0

    coste_construccion_sr = float(costes_df.loc[costes_df["Concepto"] == "Construcción sobre rasante", "Coste (€)"].sum())
    coste_construccion_br = float(costes_df.loc[costes_df["Concepto"] == "1 sótano (10 plazas + 10 trasteros)", "Coste (€)"].sum())
    coste_construccion_total = coste_construccion_sr + coste_construccion_br
    coste_financiacion = float(costes_df.loc[costes_df["Fase"] == "Fase 4 · Financiación de la promoción", "Coste (€)"].sum())

    m2_sr = inputs["sup_construida_sr_m2"]
    m2_br = inputs["sup_construida_br_m2"]
    m2_total = inputs["sup_construida_total_m2"]
    m2_vendible = inputs["sup_vendible_m2"]

    precio_m2_construccion_sr = coste_construccion_sr / m2_sr if m2_sr else 0.0
    precio_m2_construccion_br = coste_construccion_br / m2_br if m2_br else 0.0
    precio_m2_construccion_total = coste_construccion_total / m2_total if m2_total else 0.0
    precio_m2_coste_total_vendible = coste_total_sin_iva_compra / m2_vendible if m2_vendible else 0.0
    precio_m2_venta_vendible = ingresos_totales / m2_vendible if m2_vendible else 0.0
    margen_m2_vendible = margen_bruto / m2_vendible if m2_vendible else 0.0
    repercusion_suelo_m2_vendible = inputs["precio_suelo"] / m2_vendible if m2_vendible else 0.0
    repercusion_suelo_m2_sr = inputs["precio_suelo"] / m2_sr if m2_sr else 0.0
    cover_ratio = ingresos_totales / coste_total_sin_iva_compra if coste_total_sin_iva_compra else 0.0

    ratios = {
        "suelo_sobre_pem": inputs["precio_suelo"] / inputs["pem"] if inputs["pem"] else 0.0,
        "coste_obra_sobre_pem": coste_construccion_total / inputs["pem"] if inputs["pem"] else 0.0,
        "financiacion_sobre_pem": coste_financiacion / inputs["pem"] if inputs["pem"] else 0.0,
        "margen_comodo": margen_sobre_ventas >= 0.15,
        "cover_ratio": cover_ratio,
    }

    return {
        "ingresos_viviendas": ingresos_viviendas,
        "ingresos_garajes": ingresos_garajes,
        "ingresos_trasteros": ingresos_trasteros,
        "ingresos_totales": ingresos_totales,
        "iva_compra_suelo": iva_compra_suelo,
        "ajd_compra_suelo": ajd_compra_suelo,
        "costes_df": costes_df,
        "coste_total_con_iva": coste_total_con_iva,
        "coste_total_sin_iva_compra": coste_total_sin_iva_compra,
        "coste_construccion_sr": coste_construccion_sr,
        "coste_construccion_br": coste_construccion_br,
        "coste_construccion_total": coste_construccion_total,
        "coste_financiacion": coste_financiacion,
        "precio_m2_construccion_sr": precio_m2_construccion_sr,
        "precio_m2_construccion_br": precio_m2_construccion_br,
        "precio_m2_construccion_total": precio_m2_construccion_total,
        "precio_m2_coste_total_vendible": precio_m2_coste_total_vendible,
        "precio_m2_venta_vendible": precio_m2_venta_vendible,
        "margen_m2_vendible": margen_m2_vendible,
        "repercusion_suelo_m2_vendible": repercusion_suelo_m2_vendible,
        "repercusion_suelo_m2_sr": repercusion_suelo_m2_sr,
        "margen_bruto": margen_bruto,
        "margen_sobre_ventas": margen_sobre_ventas,
        "ratios": ratios,
    }


def allocate_even(series: list[float], start: int, end: int, total: float) -> None:
    if total == 0:
        return
    start = max(start, 0)
    end = max(end, start)
    periods = max(end - start + 1, 1)
    for i in range(start, min(end, len(series) - 1) + 1):
        series[i] += total / periods


def build_cashflow(inputs: dict, model: dict) -> pd.DataFrame:
    horizon = max(inputs["mes_entrega"], inputs["mes_venta_4v"]) + 1
    meses = list(range(horizon + 1))
    entradas = [0.0 for _ in meses]
    salidas = [0.0 for _ in meses]

    allocate_even(entradas, inputs["mes_venta_4v"], inputs["mes_entrega"], model["ingresos_totales"])

    buckets = model["costes_df"].groupby("Bucket")["Coste (€)"].sum().to_dict()
    salidas[inputs["mes_compra"]] += buckets.get("compra", 0.0) + buckets.get("due_diligence", 0.0)
    allocate_even(salidas, 1, max(inputs["mes_licencia"], 1), buckets.get("proyecto_licencia", 0.0))
    allocate_even(salidas, inputs["mes_inicio_obra"] - 1, inputs["mes_inicio_obra"] + 1, buckets.get("pre_obra", 0.0))
    allocate_even(salidas, inputs["mes_inicio_obra"], max(inputs["mes_entrega"] - 1, inputs["mes_inicio_obra"]), buckets.get("obra", 0.0))
    allocate_even(salidas, inputs["mes_licencia"], max(inputs["mes_entrega"] - 1, inputs["mes_licencia"]), buckets.get("financiacion", 0.0))
    allocate_even(salidas, inputs["mes_venta_4v"], inputs["mes_entrega"], buckets.get("comercializacion", 0.0))
    salidas[inputs["mes_entrega"]] += buckets.get("cierre", 0.0)

    neto = [e - s for e, s in zip(entradas, salidas)]
    acumulado = []
    running = 0.0
    for v in neto:
        running += v
        acumulado.append(running)

    return pd.DataFrame(
        {
            "Mes": meses,
            "Entradas (€)": entradas,
            "Salidas (€)": salidas,
            "Flujo neto (€)": neto,
            "Flujo acumulado (€)": acumulado,
        }
    )


def build_risk_df():
    df = pd.DataFrame(RISK_ITEMS)
    df["Semáforo"] = df["puntos"].apply(riesgo_label)
    total = int(df["puntos"].sum())
    if total >= 14:
        global_risk = "Alto"
    elif total >= 9:
        global_risk = "Medio"
    else:
        global_risk = "Bajo"
    return df, total, global_risk


def build_dictamen(model: dict, global_risk: str) -> tuple[str, str]:
    margen = model["margen_sobre_ventas"]
    cover = model["ratios"]["cover_ratio"]

    if margen >= 0.18 and global_risk != "Alto" and cover >= 1.20:
        return (
            "Dictamen favorable",
            "La promoción ya entra en rango serio de promotor: margen robusto, cobertura suficiente y estructura de costes razonablemente defendible.",
        )
    if margen >= 0.15 and cover >= 1.15:
        return (
            "Dictamen viable con control",
            "La operación es defendible, pero exige disciplina total en coste, financiación y cierre jurídico-fiscal.",
        )
    if margen >= 0.10 and cover >= 1.08:
        return (
            "Dictamen ajustado",
            "La promoción funciona, pero está en zona frágil. Un pequeño sobrecoste o descuento comercial puede erosionar gran parte del beneficio.",
        )
    return (
        "Dictamen desfavorable",
        "La rentabilidad es insuficiente para una promoción prudente. Antes de seguir conviene renegociar suelo, mix de producto o estructura de costes.",
    )


def dataframe_to_excel_bytes(dfs: dict[str, pd.DataFrame]) -> tuple[bytes, str]:
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        return buffer.getvalue(), "xlsx"
    except Exception:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for sheet_name, df in dfs.items():
                    df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            return buffer.getvalue(), "xlsx"
        except Exception:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for sheet_name, df in dfs.items():
                    zf.writestr(f"{sheet_name}.csv", df.to_csv(index=False).encode("utf-8-sig"))
            return zip_buffer.getvalue(), "zip"


def build_summary_df(inputs: dict, model: dict, risk_points: int, global_risk: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Activo", inputs["activo"]],
            ["Referencia catastral", inputs["referencia_catastral"]],
            ["Escenario", inputs["escenario"]],
            ["Parcela (m²)", inputs["parcela_m2"]],
            ["m² construidos sobre rasante", inputs["sup_construida_sr_m2"]],
            ["m² construidos bajo rasante", inputs["sup_construida_br_m2"]],
            ["m² construidos totales", inputs["sup_construida_total_m2"]],
            ["m² vendibles", inputs["sup_vendible_m2"]],
            ["Nº viviendas", inputs["num_viviendas"]],
            ["Nº garajes", inputs["num_garajes"]],
            ["Nº trasteros", inputs["num_trasteros"]],
            ["PEM", inputs["pem"]],
            ["Precio suelo", inputs["precio_suelo"]],
            ["Ingresos totales", model["ingresos_totales"]],
            ["Coste total ex IVA compra", model["coste_total_sin_iva_compra"]],
            ["Caja total incl. IVA compra", model["coste_total_con_iva"]],
            ["Precio m² construcción sobre rasante", model["precio_m2_construccion_sr"]],
            ["Precio m² construcción bajo rasante", model["precio_m2_construccion_br"]],
            ["Precio m² construcción total", model["precio_m2_construccion_total"]],
            ["Precio m² coste total vendible", model["precio_m2_coste_total_vendible"]],
            ["Precio venta m² vendible", model["precio_m2_venta_vendible"]],
            ["Repercusión suelo m² vendible", model["repercusion_suelo_m2_vendible"]],
            ["Repercusión suelo m² sobre rasante", model["repercusion_suelo_m2_sr"]],
            ["Margen bruto", model["margen_bruto"]],
            ["Margen sobre ventas", model["margen_sobre_ventas"]],
            ["Margen m² vendible", model["margen_m2_vendible"]],
            ["Riesgo global", global_risk],
            ["Puntos de riesgo", risk_points],
        ],
        columns=["Campo", "Valor"],
    )


init_state()
inputs = build_inputs()

header_left, header_right = st.columns([0.72, 0.28])
with header_left:
    st.title("Estudio Viabilidad Proyecto by Gpg")
    st.caption("Versión definitiva: superficies separadas, repercusión de suelo, costes €/m² reales, lectura económica por m² vendible y tablas estabilizadas para despliegue.")
with header_right:
    st.info(
        f"Escenario activo: **{inputs['escenario']}**\n\n"
        f"PEM: **{eur(inputs['pem'])}**\n\n"
        f"m² vendibles: **{inputs['sup_vendible_m2']:.0f}**"
    )

tabs = st.tabs(["Dashboard", "Costes editables", "Ratios serios €/m²", "Resumen", "Cash-flow", "Riesgo", "Exportar"])
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs

with tab2:
    st.subheader("Costes editables")
    c1, c2 = st.columns([0.22, 0.78])
    with c1:
        if st.button("Resetear tabla al escenario", use_container_width=True):
            st.session_state["editable_costs_store"] = build_base_cost_df(inputs["escenario"])
            st.session_state["reset_counter"] += 1
            st.rerun()
    with c2:
        st.caption("Edita la columna **Coste editable (€)**. IVA y AJD son automáticos. Fases 2, 4 y 5 absorben el sobrecoste activo.")
    editor_df = st.data_editor(
        st.session_state["editable_costs_store"].copy(),
        key=f"editable_costs_editor_{st.session_state['reset_counter']}",
        hide_index=True,
        width="stretch",
        disabled=["Fase", "Hito", "Concepto", "Observaciones", "Bucket", "Auto"],
        column_config={
            "Coste editable (€)": st.column_config.NumberColumn("Coste editable (€)", min_value=0.0, step=500.0, format="%.2f"),
            "Auto": st.column_config.CheckboxColumn("Auto"),
        },
    )
    st.session_state["editable_costs_store"] = editor_df

model = compute_model(inputs, st.session_state["editable_costs_store"])
cashflow_df = build_cashflow(inputs, model)
risk_df, risk_points, global_risk = build_risk_df()
dictamen_titulo, dictamen_texto = build_dictamen(model, global_risk)

with tab1:
    st.markdown(
        f"""
        <div class="gpg-card">
            <div class="gpg-kicker">Análisis promotor profesional</div>
            <div class="gpg-big">Estudio Viabilidad Proyecto by Gpg</div>
            <div class="gpg-sub">
                Activo: <strong>{inputs["activo"]}</strong> · Escenario: <strong>{inputs["escenario"]}</strong> ·
                Parcela: <strong>{inputs["parcela_m2"]:.0f} m²</strong> ·
                m² sobre rasante: <strong>{inputs["sup_construida_sr_m2"]:.0f}</strong> ·
                m² vendibles: <strong>{inputs["sup_vendible_m2"]:.0f}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(5)
    row1[0].metric("Ingresos brutos", eur(model["ingresos_totales"]))
    row1[1].metric("Coste total ex IVA compra", eur(model["coste_total_sin_iva_compra"]))
    row1[2].metric("Margen bruto", eur(model["margen_bruto"]))
    row1[3].metric("Margen sobre ventas", pct(model["margen_sobre_ventas"]))
    row1[4].metric("Cobertura ventas/coste", ratio(model["ratios"]["cover_ratio"]))

    row2 = st.columns(5)
    row2[0].metric("€ / m² construcción total", eur_m2(model["precio_m2_construccion_total"]))
    row2[1].metric("€ / m² coste total vendible", eur_m2(model["precio_m2_coste_total_vendible"]))
    row2[2].metric("€ / m² venta vendible", eur_m2(model["precio_m2_venta_vendible"]))
    row2[3].metric("€ / m² margen vendible", eur_m2(model["margen_m2_vendible"]))
    row2[4].metric("Riesgo global", global_risk)

    st.divider()

    d1, d2 = st.columns([0.56, 0.44])
    with d1:
        st.subheader("Ficha de control")
        ficha = pd.DataFrame(
            [
                ["Activo", str(inputs["activo"])],
                ["Referencia catastral", str(inputs["referencia_catastral"])],
                ["Parcela (m²)", f'{inputs["parcela_m2"]:,.0f} m²'.replace(",", ".")],
                ["m² construidos sobre rasante", f'{inputs["sup_construida_sr_m2"]:,.0f} m²'.replace(",", ".")],
                ["m² construidos bajo rasante", f'{inputs["sup_construida_br_m2"]:,.0f} m²'.replace(",", ".")],
                ["m² construidos totales", f'{inputs["sup_construida_total_m2"]:,.0f} m²'.replace(",", ".")],
                ["m² vendibles", f'{inputs["sup_vendible_m2"]:,.0f} m²'.replace(",", ".")],
                ["PEM referencia", eur(inputs["pem"])],
                ["Precio suelo", eur(inputs["precio_suelo"])],
                ["Repercusión suelo / m² vendible", eur_m2(model["repercusion_suelo_m2_vendible"])],
                ["Repercusión suelo / m² sobre rasante", eur_m2(model["repercusion_suelo_m2_sr"])],
                ["Mes licencia", str(int(inputs["mes_licencia"]))],
                ["Mes inicio obra", str(int(inputs["mes_inicio_obra"]))],
                ["Mes venta 4 viviendas", str(int(inputs["mes_venta_4v"]))],
                ["Mes entrega / escrituras", str(int(inputs["mes_entrega"]))],
            ],
            columns=["Campo", "Valor"],
        )
        ficha["Valor"] = ficha["Valor"].astype(str)
        st.dataframe(display_df(ficha), width="stretch", hide_index=True)

    with d2:
        st.subheader(dictamen_titulo)
        if "favorable" in dictamen_titulo.lower():
            st.success(dictamen_texto)
        elif "viable" in dictamen_titulo.lower():
            st.warning(dictamen_texto)
        elif "ajustado" in dictamen_titulo.lower():
            st.warning(dictamen_texto)
        else:
            st.error(dictamen_texto)

        st.markdown("**Lectura rápida de promotor**")
        lectura = pd.DataFrame(
            [
                ["Suelo / PEM", pct(model["ratios"]["suelo_sobre_pem"])],
                ["Coste obra / PEM", pct(model["ratios"]["coste_obra_sobre_pem"])],
                ["Financiación / PEM", pct(model["ratios"]["financiacion_sobre_pem"])],
                ["Margen cómodo ≥ 15%", "Sí" if model["ratios"]["margen_comodo"] else "No"],
                ["Cobertura ventas/coste", ratio(model["ratios"]["cover_ratio"])],
                ["Puntos de riesgo", str(risk_points)],
            ],
            columns=["Indicador", "Valor"],
        )
        st.dataframe(display_df(lectura), width="stretch", hide_index=True)

with tab3:
    st.subheader("Ratios serios por m²")
    ratios_m2 = pd.DataFrame(
        [
            ["m² construidos sobre rasante", inputs["sup_construida_sr_m2"]],
            ["m² construidos bajo rasante", inputs["sup_construida_br_m2"]],
            ["m² construidos totales", inputs["sup_construida_total_m2"]],
            ["m² vendibles", inputs["sup_vendible_m2"]],
            ["Coste construcción sobre rasante", model["coste_construccion_sr"]],
            ["Coste construcción bajo rasante", model["coste_construccion_br"]],
            ["Coste construcción total", model["coste_construccion_total"]],
            ["Coste total ex IVA compra", model["coste_total_sin_iva_compra"]],
            ["Precio m² construcción sobre rasante", model["precio_m2_construccion_sr"]],
            ["Precio m² construcción bajo rasante", model["precio_m2_construccion_br"]],
            ["Precio m² construcción total", model["precio_m2_construccion_total"]],
            ["Precio m² coste total vendible", model["precio_m2_coste_total_vendible"]],
            ["Precio venta m² vendible", model["precio_m2_venta_vendible"]],
            ["Margen m² vendible", model["margen_m2_vendible"]],
            ["Repercusión suelo m² vendible", model["repercusion_suelo_m2_vendible"]],
            ["Repercusión suelo m² sobre rasante", model["repercusion_suelo_m2_sr"]],
        ],
        columns=["Concepto", "Valor"],
    )

    def render_valor(row):
        if "m² " in row["Concepto"] and "Precio" not in row["Concepto"] and "Repercusión" not in row["Concepto"] and "Margen" not in row["Concepto"] and "Coste" not in row["Concepto"]:
            return f"{row['Valor']:,.0f} m²".replace(",", ".")
        if "Coste" in row["Concepto"] and "m²" not in row["Concepto"]:
            return eur(row["Valor"])
        return eur_m2(row["Valor"])

    ratios_m2["Valor visible"] = ratios_m2.apply(render_valor, axis=1)
    st.dataframe(display_df(ratios_m2[["Concepto", "Valor visible"]]), width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        comp_df = pd.DataFrame(
            {
                "Indicador": ["Construcción SR", "Construcción BR", "Construcción total", "Coste total vendible"],
                "Valor": [
                    model["precio_m2_construccion_sr"],
                    model["precio_m2_construccion_br"],
                    model["precio_m2_construccion_total"],
                    model["precio_m2_coste_total_vendible"],
                ],
            }
        ).set_index("Indicador")
        st.bar_chart(comp_df["Valor"])
    with c2:
        venta_df = pd.DataFrame(
            {
                "Indicador": ["Venta m² vendible", "Margen m² vendible", "Suelo m² vendible"],
                "Valor": [
                    model["precio_m2_venta_vendible"],
                    model["margen_m2_vendible"],
                    model["repercusion_suelo_m2_vendible"],
                ],
            }
        ).set_index("Indicador")
        st.bar_chart(venta_df["Valor"])

with tab4:
    st.subheader("Resumen económico")
    ingresos_df = pd.DataFrame(
        [
            ["Viviendas", model["ingresos_viviendas"], model["ingresos_viviendas"] / inputs["pem"] if inputs["pem"] else 0],
            ["Garajes", model["ingresos_garajes"], model["ingresos_garajes"] / inputs["pem"] if inputs["pem"] else 0],
            ["Trasteros", model["ingresos_trasteros"], model["ingresos_trasteros"] / inputs["pem"] if inputs["pem"] else 0],
            ["Ingresos brutos totales", model["ingresos_totales"], model["ingresos_totales"] / inputs["pem"] if inputs["pem"] else 0],
        ],
        columns=["Concepto", "Importe (€)", "% PEM"],
    )
    ingresos_show = ingresos_df.copy()
    ingresos_show["Importe (€)"] = ingresos_show["Importe (€)"].map(eur)
    ingresos_show["% PEM"] = ingresos_show["% PEM"].map(pct)
    st.dataframe(display_df(ingresos_show), width="stretch", hide_index=True)

    st.subheader("Costes por fase")
    fases = model["costes_df"].groupby("Fase", as_index=False)["Coste (€)"].sum()
    fases_show = fases.copy()
    fases_show["% PEM"] = fases_show["Coste (€)"] / inputs["pem"] if inputs["pem"] else 0.0
    fases_show["Coste visible"] = fases_show["Coste (€)"].map(eur)
    fases_show["% PEM visible"] = fases_show["% PEM"].map(pct)
    st.dataframe(display_df(fases_show[["Fase", "Coste visible", "% PEM visible"]]), width="stretch", hide_index=True)
    st.bar_chart(fases.set_index("Fase")["Coste (€)"])

with tab5:
    st.subheader("Cash-flow mensual")
    cf_show = cashflow_df.copy()
    for col in ["Entradas (€)", "Salidas (€)", "Flujo neto (€)", "Flujo acumulado (€)"]:
        cf_show[col] = cf_show[col].map(eur)
    st.dataframe(display_df(cf_show), width="stretch", hide_index=True)
    st.line_chart(cashflow_df.set_index("Mes")[["Entradas (€)", "Salidas (€)", "Flujo neto (€)", "Flujo acumulado (€)"]])

with tab6:
    st.subheader("Semáforo automático de riesgo")
    risk_show = risk_df.rename(
        columns={"categoria": "Categoría", "estado": "Estado", "puntos": "Puntos", "comentario": "Comentario"}
    )
    st.dataframe(display_df(risk_show), width="stretch", hide_index=True)
    if global_risk == "Alto":
        st.error(f"Riesgo global {global_risk} · {risk_points} puntos")
    elif global_risk == "Medio":
        st.warning(f"Riesgo global {global_risk} · {risk_points} puntos")
    else:
        st.success(f"Riesgo global {global_risk} · {risk_points} puntos")

    alertas = []
    if risk_points >= 14:
        alertas.append("riesgo global alto")
    if inputs["iva_compra"] >= 0.21:
        alertas.append("fiscalidad de compra sensible; exige validación escrita")
    if model["margen_sobre_ventas"] < 0.15:
        alertas.append("margen por debajo del 15% orientativo")
    if model["precio_m2_coste_total_vendible"] >= model["precio_m2_venta_vendible"]:
        alertas.append("el coste total por m² vendible iguala o supera el precio de venta por m²")
    if not alertas:
        st.success("sin alertas críticas en este escenario")
    else:
        for alerta in alertas:
            st.write(f"- {alerta}")

with tab7:
    st.subheader("Exportación")
    summary_df = build_summary_df(inputs, model, risk_points, global_risk)
    export_dfs = {
        "resumen": summary_df,
        "costes_detallados": model["costes_df"],
        "cashflow": cashflow_df,
        "riesgo": risk_df,
    }
    file_bytes, ext = dataframe_to_excel_bytes(export_dfs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"estudio_viabilidad_gpg_{timestamp}.{ext}"

    st.download_button(
        "Descargar exportación completa",
        data=file_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == "xlsx" else "application/zip",
        use_container_width=True,
    )
    st.download_button(
        "Descargar cash-flow CSV",
        data=cashflow_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"cashflow_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "Descargar costes CSV",
        data=model["costes_df"].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"costes_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption("La exportación Excel usa xlsxwriter u openpyxl. Si no están disponibles, la app genera un ZIP con CSVs.")
