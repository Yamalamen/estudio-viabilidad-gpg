# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import math
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

st.set_page_config(page_title="Estudio Viabilidad Proyecto by Gpg", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.0rem; padding-bottom: 2rem; max-width: 1500px;}
h1, h2, h3 {letter-spacing: -0.02em;}
[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(18,25,40,0.96), rgba(10,14,24,0.96));
    border: 1px solid rgba(255,255,255,0.08);
    padding: 18px 18px 14px 18px;
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
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
</style>
""", unsafe_allow_html=True)

DEFAULT_INPUTS = {
    "activo": "C/ Los Cincuenta 3, Alicante",
    "referencia_catastral": "7653302YH1475D0001AL",
    "parcela_m2": 311.0,
    "sup_construida_sr_m2": 1000.0,
    "sup_construida_br_m2": 260.0,
    "sup_vendible_m2": 1000.0,
    "pem": 1_450_000.0,
    "precio_suelo": 315_000.0,
    "iva_compra_suelo_pct": 0.21,
    "ajd_pct": 0.015,
    "precio_vivienda": 260_000.0,
    "num_viviendas": 11,
    "precio_garaje": 25_000.0,
    "num_garajes": 0,
    "precio_trastero": 3_500.0,
    "num_trasteros": 0,
}
BASE_PEM = DEFAULT_INPUTS["pem"]

PROGRAM_PRESETS = {
    "11 viviendas": {
        "num_viviendas": 11,
        "num_garajes": 0,
        "num_trasteros": 0,
        "precio_vivienda": 260_000.0,
        "precio_garaje": 25_000.0,
        "precio_trastero": 3_500.0,
        "sup_construida_sr_m2": 1000.0,
        "sup_construida_br_m2": 260.0,
        "sup_vendible_m2": 1000.0,
    },
    "10 viviendas": {
        "num_viviendas": 10,
        "num_garajes": 0,
        "num_trasteros": 0,
        "precio_vivienda": 260_000.0,
        "precio_garaje": 25_000.0,
        "precio_trastero": 3_500.0,
        "sup_construida_sr_m2": 1000.0,
        "sup_construida_br_m2": 260.0,
        "sup_vendible_m2": 1000.0,
    },
}

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

COST_ITEMS = [
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Abogado inmobiliario + mercantil", "base": 5000.0, "obs": "Revisión contractual compra aplazada", "auto": False},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Revisión fiscal/notarial compra", "base": 1400.0, "obs": "Validar IVA/AJD y escritura", "auto": False},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Nota simple / cargas / contraste registral", "base": 650.0, "obs": "", "auto": False},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Anteproyecto de encaje", "base": 7000.0, "obs": "", "auto": False},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Topográfico", "base": 1300.0, "obs": "Pendiente", "auto": False},
    {"fase": "Fase 0 · Due Diligence y viabilidad previa", "hito": "Antes de firmar", "concepto": "Geotécnico", "base": 4000.0, "obs": "Pendiente", "auto": False},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Primer pago suelo", "base": 100000.0, "obs": "Parte del precio aplazado", "auto": False},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "IVA compra suelo", "base": 0.0, "obs": "Calculado sobre precio suelo", "auto": True},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "AJD compra suelo", "base": 0.0, "obs": "Calculado sobre precio suelo", "auto": True},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Notaría compraventa", "base": 1850.0, "obs": "", "auto": False},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Registro Propiedad", "base": 1300.0, "obs": "", "auto": False},
    {"fase": "Fase 1 · Adquisición del suelo", "hito": "Firma compra", "concepto": "Gestoría compraventa", "base": 500.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Proyecto básico", "base": 23000.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Proyecto ejecución", "base": 28000.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Dirección de obra", "base": 15000.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Dirección de ejecución", "base": 13000.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "CSS", "base": 5500.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Estudios técnicos complementarios", "base": 6500.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "Laboratorio / control calidad", "base": 7500.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Tras compra / proyecto", "concepto": "OCT", "base": 6500.0, "obs": "Si banco/seguro lo exige", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Solicitud licencia", "concepto": "Tasas licencia / expedientes", "base": 2500.0, "obs": "", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Solicitud licencia", "concepto": "ICIO", "base": 59000.0, "obs": "Base PEM prudente; impuesto fuera del PEM", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "Concesión licencia", "concepto": "Pago aplazado suelo", "base": 50000.0, "obs": "Parte del precio", "auto": False},
    {"fase": "Fase 2 · Proyecto, licencias y tramitación técnica", "hito": "A 6 meses si no licencia", "concepto": "Pago adicional obligado", "base": 50000.0, "obs": "Parte del precio", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Proyecto / trámite demolición", "base": 2750.0, "obs": "", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Demolición", "base": 30000.0, "obs": "", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Residuos demolición", "base": 9000.0, "obs": "", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Contingencia amianto", "base": 10000.0, "obs": "Si aparece", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Vallado / limpieza / implantación", "base": 6000.0, "obs": "", "auto": False},
    {"fase": "Fase 3 · Preparación del solar y preobra", "hito": "Antes de obra", "concepto": "Apeos / protección medianeras", "base": 10000.0, "obs": "", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Tasación ECO", "base": 3000.0, "obs": "", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Comisión apertura / estudio", "base": 13000.0, "obs": "", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Monitoring técnico banco", "base": 8500.0, "obs": "", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Tras licencia y preventas", "concepto": "Notaría / registro préstamo", "base": 3500.0, "obs": "", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Durante obra", "concepto": "Intereses", "base": 137500.0, "obs": "Muy sensible al banco/plazo", "auto": False},
    {"fase": "Fase 4 · Financiación de la promoción", "hito": "Durante obra", "concepto": "Otras comisiones bancarias", "base": 5000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "Construcción sobre rasante", "base": 1210000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "1 sótano (10 plazas + 10 trasteros)", "base": 260000.0, "obs": "Opción base recomendada", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Inicio obra", "concepto": "Ascensor", "base": 35000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Acometidas definitivas", "base": 25000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Urbanización interior / remates", "base": 32500.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Medios auxiliares / grúa / casetas", "base": 30000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Seguridad y salud ejecución", "base": 14000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Residuos de obra", "base": 17000.0, "obs": "", "auto": False},
    {"fase": "Fase 5 · Ejecución de obra", "hito": "Durante obra", "concepto": "Imprevistos / modificados", "base": 120000.0, "obs": "", "auto": False},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Al vender 4 viviendas", "concepto": "Pago aplazado suelo", "base": 50000.0, "obs": "Parte del precio", "auto": False},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Marketing / renders / dossier", "base": 10500.0, "obs": "", "auto": False},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Contratos privados / jurídico comercial", "base": 5000.0, "obs": "", "auto": False},
    {"fase": "Fase 6 · Comercialización y ventas", "hito": "Durante comercialización", "concepto": "Avales cantidades anticipadas", "base": 8000.0, "obs": "", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Fin promoción", "concepto": "Resto precio suelo", "base": 65000.0, "obs": "Parte del precio", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Primera ocupación / cierre admin.", "base": 1000.0, "obs": "", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Seguro decenal", "base": 12000.0, "obs": "", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Obra nueva y división horizontal", "base": 10000.0, "obs": "", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Final obra", "concepto": "Cancelaciones / novaciones / entrega", "base": 4500.0, "obs": "", "auto": False},
    {"fase": "Fase 7 · Entrega, cierre y postventa", "hito": "Postentrega", "concepto": "Repasos / postventa inicial", "base": 12000.0, "obs": "", "auto": False},
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

PEM_SENSITIVE_CONCEPTS = {
    "ICIO","Construcción sobre rasante","1 sótano (10 plazas + 10 trasteros)","Ascensor","Acometidas definitivas",
    "Urbanización interior / remates","Medios auxiliares / grúa / casetas","Seguridad y salud ejecución",
    "Residuos de obra","Imprevistos / modificados","Proyecto básico","Proyecto ejecución","Dirección de obra",
    "Dirección de ejecución","CSS","Estudios técnicos complementarios","Laboratorio / control calidad","OCT",
}

def eur(v: float) -> str:
    return f"{safe_float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(v: float) -> str:
    return f"{v * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def eur_m2(v: float) -> str:
    return f"{safe_float(v):,.2f} €/m²".replace(",", "X").replace(".", ",").replace("X", ".")


def ratio(v: float) -> str:
    return f"{safe_float(v):,.2f}x".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_es_number(v: float, decimals: int = 2) -> str:
    return f"{safe_float(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_es_currency(v: float) -> str:
    return fmt_es_number(v, 2)

def fmt_es_percent_from_ratio(v: float) -> str:
    return fmt_es_number(safe_float(v) * 100.0, 2)

def parse_es_number(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    s = s.replace("€", "").replace("%", "").replace("/m²", "").replace("m²", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default

def pct_display_from_ratio(v: float) -> str:
    return f"{safe_float(v) * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def decimal_to_percent_value(v: float) -> float:
    return safe_float(v) * 100.0

def percent_to_decimal_value(v: float) -> float:
    return safe_float(v) / 100.0

def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default

def normalise_pct(value) -> float:
    v = safe_float(value, 0.0)
    return v / 100.0 if abs(v) > 1 else v

def display_df(df: pd.DataFrame) -> pd.DataFrame:
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

def empty_accounting_tab_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["Fecha", "Concepto", "Importe (€)", "Observaciones"])

def normalise_accounting_tab_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["Fecha", "Concepto", "Observaciones"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str)
    if "Importe (€)" not in out.columns:
        out["Importe (€)"] = 0.0
    out["Importe (€)"] = pd.to_numeric(out["Importe (€)"], errors="coerce").fillna(0.0)
    return out[["Fecha", "Concepto", "Importe (€)", "Observaciones"]]

def build_additional_accounting_df(pem: float) -> pd.DataFrame:
    rows = []
    tabs_store = st.session_state.get("custom_accounting_tabs", {})
    for tab_name, df in tabs_store.items():
        tab_df = normalise_accounting_tab_df(df)
        for _, row in tab_df.iterrows():
            concepto = str(row["Concepto"]).strip()
            importe = safe_float(row["Importe (€)"])
            fecha = str(row["Fecha"]).strip()
            observaciones = str(row["Observaciones"]).strip()
            if not concepto and abs(importe) < 0.005 and not fecha and not observaciones:
                continue
            rows.append({
                "Fase": f"Contabilidad adicional · {tab_name}",
                "Hito": fecha or "Contabilidad adicional",
                "Concepto": concepto or "Apunte contable",
                "Coste editable (€)": importe,
                "% PEM": (importe / pem) if pem else 0.0,
                "Observaciones": observaciones,
                "Auto": False,
                "Coste (€)": importe,
                "Bucket": "otros",
            })
    return pd.DataFrame(rows)

def parse_month_from_date(value: str) -> int | None:
    s = (value or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return None
        return max(int(dt.month) - 1, 0)
    except Exception:
        return None

def init_state() -> None:
    if "program_preset" not in st.session_state:
        st.session_state["program_preset"] = "11 viviendas"
    if "editable_costs_store" not in st.session_state:
        st.session_state["editable_costs_store"] = build_base_cost_df()
    if "custom_accounting_tabs" not in st.session_state:
        st.session_state["custom_accounting_tabs"] = {"General": empty_accounting_tab_df()}
    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0

def build_base_cost_df() -> pd.DataFrame:
    rows = []
    for item in COST_ITEMS:
        coste = float(item["base"])
        rows.append({
            "Fase": item["fase"],
            "Hito": item["hito"],
            "Concepto": item["concepto"],
            "Coste editable (€)": coste,
            "% PEM": (coste / BASE_PEM) if BASE_PEM else 0.0,
            "Observaciones": item["obs"],
            "Auto": bool(item["auto"]),
        })
    return ensure_cost_editor_columns(pd.DataFrame(rows), BASE_PEM)

def ensure_cost_editor_columns(df: pd.DataFrame, pem: float) -> pd.DataFrame:
    out = df.copy()
    defaults = {"Fase":"","Hito":"","Concepto":"","Coste editable (€)":0.0,"% PEM":0.0,"Observaciones":"","Auto":False}
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    out["Fase"] = out["Fase"].fillna("").astype(str)
    out["Hito"] = out["Hito"].fillna("").astype(str)
    out["Concepto"] = out["Concepto"].fillna("").astype(str)
    out["Observaciones"] = out["Observaciones"].fillna("").astype(str)
    out["Auto"] = out["Auto"].fillna(False).astype(bool)
    out["Coste editable (€)"] = pd.to_numeric(out["Coste editable (€)"], errors="coerce").fillna(0.0)
    out["% PEM"] = pd.to_numeric(out["% PEM"], errors="coerce").fillna(0.0).apply(normalise_pct)
    if pem > 0:
        zero_pct = out["% PEM"].eq(0.0) & out["Coste editable (€)"].ne(0.0)
        out.loc[zero_pct, "% PEM"] = out.loc[zero_pct, "Coste editable (€)"] / pem
    return out[["Fase","Hito","Concepto","Coste editable (€)","% PEM","Observaciones","Auto"]]

def sync_cost_rows_with_pem(df: pd.DataFrame, pem: float) -> pd.DataFrame:
    out = ensure_cost_editor_columns(df, pem)
    if pem > 0:
        manual_mask = ~out["Auto"]
        out.loc[manual_mask, "Coste editable (€)"] = out.loc[manual_mask, "% PEM"] * pem
        out.loc[out["Auto"], "% PEM"] = out.loc[out["Auto"], "Coste editable (€)"] / pem
    else:
        out["% PEM"] = 0.0
    return out

def reconcile_cost_editor_changes(previous_df: pd.DataFrame, edited_df: pd.DataFrame, pem: float) -> pd.DataFrame:
    previous = ensure_cost_editor_columns(previous_df, pem)
    edited = ensure_cost_editor_columns(edited_df, pem)
    max_len = max(len(previous), len(edited))
    fill_values = {"Fase":"","Hito":"","Concepto":"","Coste editable (€)":0.0,"% PEM":0.0,"Observaciones":"","Auto":False}
    previous = previous.reindex(range(max_len)).fillna(fill_values)
    edited = edited.reindex(range(max_len)).fillna(fill_values)
    result = edited.copy()
    for idx in result.index:
        if bool(result.at[idx, "Auto"]):
            result.at[idx, "% PEM"] = (safe_float(result.at[idx, "Coste editable (€)"]) / pem) if pem else 0.0
            continue
        prev_cost = safe_float(previous.at[idx, "Coste editable (€)"])
        prev_pct = normalise_pct(previous.at[idx, "% PEM"])
        new_cost = safe_float(result.at[idx, "Coste editable (€)"])
        new_pct = normalise_pct(result.at[idx, "% PEM"])
        cost_changed = not math.isclose(new_cost, prev_cost, rel_tol=1e-9, abs_tol=0.01)
        pct_changed = not math.isclose(new_pct, prev_pct, rel_tol=1e-9, abs_tol=1e-9)
        if pct_changed and not cost_changed and pem > 0:
            result.at[idx, "Coste editable (€)"] = new_pct * pem
        else:
            result.at[idx, "% PEM"] = (new_cost / pem) if pem else 0.0
    return ensure_cost_editor_columns(result, pem)

def pem_scaled_cost(concepto: str, coste_base: float, pem: float) -> float:
    if BASE_PEM <= 0:
        return coste_base
    if concepto in PEM_SENSITIVE_CONCEPTS:
        return coste_base * (pem / BASE_PEM)
    return coste_base

def apply_program_preset(preset_name: str) -> None:
    preset = PROGRAM_PRESETS[preset_name]
    st.session_state["program_preset"] = preset_name
    for k, v in preset.items():
        st.session_state[k] = v

def build_inputs() -> dict:
    st.sidebar.header("Control del modelo")
    escenario = st.sidebar.selectbox("Escenario", list(SCENARIOS.keys()), index=0)
    active = SCENARIOS[escenario]
    st.sidebar.subheader("Preset de producto")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button("Preset 10", use_container_width=True):
            apply_program_preset("10 viviendas")
    with c2:
        if st.button("Preset 11", use_container_width=True):
            apply_program_preset("11 viviendas")
    st.sidebar.caption(f"Preset activo: **{st.session_state.get('program_preset', '11 viviendas')}**")
    st.sidebar.subheader("Activo")
    activo = st.sidebar.text_input("Activo", DEFAULT_INPUTS["activo"])
    rc = st.sidebar.text_input("Referencia catastral", DEFAULT_INPUTS["referencia_catastral"])
    parcela_m2 = st.sidebar.number_input("Parcela catastral (m²)", min_value=0.0, value=float(DEFAULT_INPUTS["parcela_m2"]), step=1.0)
    st.sidebar.subheader("Superficies")
    sup_construida_sr_m2 = st.sidebar.number_input("m² construidos sobre rasante", min_value=0.0, value=float(st.session_state.get("sup_construida_sr_m2", DEFAULT_INPUTS["sup_construida_sr_m2"])), step=10.0)
    sup_construida_br_m2 = st.sidebar.number_input("m² construidos bajo rasante", min_value=0.0, value=float(st.session_state.get("sup_construida_br_m2", DEFAULT_INPUTS["sup_construida_br_m2"])), step=10.0)
    sup_vendible_m2 = st.sidebar.number_input("m² vendibles", min_value=0.0, value=float(st.session_state.get("sup_vendible_m2", DEFAULT_INPUTS["sup_vendible_m2"])), step=10.0)
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
        "program_preset": st.session_state.get("program_preset", "11 viviendas"),
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
    df = ensure_cost_editor_columns(edited_df, inputs["pem"]).copy()
    if inputs["pem"] > 0:
        manual_mask = ~df["Auto"]
        df.loc[manual_mask, "Coste (€)"] = df.loc[manual_mask, "% PEM"] * inputs["pem"]
        df.loc[df["Auto"], "Coste (€)"] = df.loc[df["Auto"], "Coste editable (€)"]
    else:
        df["Coste (€)"] = df["Coste editable (€)"]
    for idx, row in df.iterrows():
        if not bool(row["Auto"]):
            df.at[idx, "Coste (€)"] = pem_scaled_cost(str(row["Concepto"]), safe_float(row["Coste (€)"]), inputs["pem"])
    obra_variable = df["Fase"].isin(["Fase 2 · Proyecto, licencias y tramitación técnica","Fase 4 · Financiación de la promoción","Fase 5 · Ejecución de obra"])
    df.loc[obra_variable, "Coste (€)"] = df.loc[obra_variable, "Coste (€)"] * (1 + inputs["sobrecoste_pct"])
    iva_compra_suelo = inputs["precio_suelo"] * inputs["iva_compra"]
    ajd_compra_suelo = inputs["precio_suelo"] * inputs["ajd"]

    def override(concepto: str, valor: float) -> None:
        mask = df["Concepto"].eq(concepto)
        if mask.any():
            df.loc[mask, "Coste (€)"] = valor
            df.loc[mask, "Coste editable (€)"] = valor
            df.loc[mask, "% PEM"] = valor / inputs["pem"] if inputs["pem"] else 0.0

    override("IVA compra suelo", iva_compra_suelo)
    override("AJD compra suelo", ajd_compra_suelo)

    pagos_suelo = ["Primer pago suelo", "Pago aplazado suelo", "Pago adicional obligado", "Resto precio suelo"]
    suelo_actual = df.loc[df["Concepto"].isin(pagos_suelo), "Coste (€)"].sum()
    ajuste_suelo = inputs["precio_suelo"] - suelo_actual
    idx = df.index[df["Concepto"].eq("Resto precio suelo")]
    if len(idx):
        df.loc[idx[0], "Coste (€)"] = df.loc[idx[0], "Coste (€)"] + ajuste_suelo
        df.loc[idx[0], "Coste editable (€)"] = df.loc[idx[0], "Coste (€)"]
        df.loc[idx[0], "% PEM"] = df.loc[idx[0], "Coste (€)"] / inputs["pem"] if inputs["pem"] else 0.0

    additional_df = build_additional_accounting_df(inputs["pem"])
    if not additional_df.empty:
        df = pd.concat([df, additional_df], ignore_index=True)

    df["Bucket"] = df["Fase"].map(PHASE_ALLOCATION).fillna("otros")
    df["% PEM"] = df["Coste (€)"] / inputs["pem"] if inputs["pem"] else 0.0
    return df

def compute_model(inputs: dict, edited_df: pd.DataFrame) -> dict:
    ingresos_viviendas = inputs["precio_vivienda"] * inputs["num_viviendas"] * (1 - inputs["caida_precios_pct"])
    ingresos_garajes = inputs["precio_garaje"] * inputs["num_garajes"] * (1 - inputs["caida_precios_pct"])
    ingresos_trasteros = inputs["precio_trastero"] * inputs["num_trasteros"] * (1 - inputs["caida_precios_pct"])
    ingresos_totales = ingresos_viviendas + ingresos_garajes + ingresos_trasteros
    costes_df = build_cost_df(inputs, edited_df)
    iva_compra_suelo = inputs["precio_suelo"] * inputs["iva_compra"]
    coste_total_con_iva = float(costes_df["Coste (€)"].sum())
    coste_total_sin_iva_compra = coste_total_con_iva - iva_compra_suelo
    margen_bruto = ingresos_totales - coste_total_sin_iva_compra
    margen_sobre_ventas = margen_bruto / ingresos_totales if ingresos_totales else 0.0
    coste_construccion_sr = float(costes_df.loc[costes_df["Concepto"] == "Construcción sobre rasante", "Coste (€)"].sum())
    coste_construccion_br = float(costes_df.loc[costes_df["Concepto"] == "1 sótano (10 plazas + 10 trasteros)", "Coste (€)"].sum())
    coste_construccion_total = coste_construccion_sr + coste_construccion_br
    coste_financiacion = float(costes_df.loc[costes_df["Fase"] == "Fase 4 · Financiación de la promoción", "Coste (€)"].sum())
    coste_contabilidad_adicional = float(costes_df.loc[costes_df["Bucket"] == "otros", "Coste (€)"].sum())
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
    ratios = {
        "suelo_sobre_pem": inputs["precio_suelo"] / inputs["pem"] if inputs["pem"] else 0.0,
        "coste_obra_sobre_pem": coste_construccion_total / inputs["pem"] if inputs["pem"] else 0.0,
        "financiacion_sobre_pem": coste_financiacion / inputs["pem"] if inputs["pem"] else 0.0,
        "cover_ratio": ingresos_totales / coste_total_sin_iva_compra if coste_total_sin_iva_compra else 0.0,
        "margen_comodo": margen_sobre_ventas >= 0.15,
    }
    return {
        "ingresos_viviendas": ingresos_viviendas,
        "ingresos_garajes": ingresos_garajes,
        "ingresos_trasteros": ingresos_trasteros,
        "ingresos_totales": ingresos_totales,
        "iva_compra_suelo": iva_compra_suelo,
        "costes_df": costes_df,
        "coste_total_con_iva": coste_total_con_iva,
        "coste_total_sin_iva_compra": coste_total_sin_iva_compra,
        "coste_contabilidad_adicional": coste_contabilidad_adicional,
        "coste_construccion_sr": coste_construccion_sr,
        "coste_construccion_br": coste_construccion_br,
        "coste_construccion_total": coste_construccion_total,
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
    horizon = max(inputs["mes_entrega"], inputs["mes_venta_4v"], 12) + 1
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
    for _, df in st.session_state.get("custom_accounting_tabs", {}).items():
        tab_df = normalise_accounting_tab_df(df)
        for _, row in tab_df.iterrows():
            importe = safe_float(row["Importe (€)"])
            if abs(importe) < 0.005:
                continue
            mes = parse_month_from_date(str(row["Fecha"]))
            if mes is None:
                salidas[inputs["mes_compra"]] += importe
            else:
                if mes > len(salidas) - 1:
                    extra = mes - (len(salidas) - 1)
                    salidas.extend([0.0] * extra)
                    entradas.extend([0.0] * extra)
                salidas[mes] += importe
    neto = [e - s for e, s in zip(entradas, salidas)]
    acumulado = []
    running = 0.0
    for v in neto:
        running += v
        acumulado.append(running)
    return pd.DataFrame({"Mes": list(range(len(neto))), "Entradas (€)": entradas, "Salidas (€)": salidas, "Flujo neto (€)": neto, "Flujo acumulado (€)": acumulado})

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
        return "Viable", "La promoción entra en una zona razonable de promotor: margen sólido, cobertura suficiente y estructura de costes defendible."
    if margen >= 0.15 and cover >= 1.15:
        return "Viable con control estricto", "La operación se puede defender, pero exige disciplina total en costes, financiación, ventas y fiscalidad."
    return "No recomendable", "El margen es insuficiente o demasiado frágil. Antes de seguir conviene renegociar suelo, mix comercial o estructura de costes."

def build_summary_df(inputs: dict, model: dict, risk_points: int, global_risk: str) -> pd.DataFrame:
    rows = [
        ["Activo", str(inputs["activo"])], ["Referencia catastral", str(inputs["referencia_catastral"])], ["Escenario", str(inputs["escenario"])],
        ["PEM", eur(inputs["pem"])], ["Ingresos totales", eur(model["ingresos_totales"])], ["Coste total ex IVA compra", eur(model["coste_total_sin_iva_compra"])],
        ["Caja total incl. IVA compra", eur(model["coste_total_con_iva"])], ["Contabilidad adicional", eur(model["coste_contabilidad_adicional"])],
        ["Margen bruto", eur(model["margen_bruto"])], ["Margen sobre ventas", pct(model["margen_sobre_ventas"])], ["Riesgo global", global_risk], ["Puntos de riesgo", str(risk_points)],
    ]
    return pd.DataFrame(rows, columns=["Campo", "Valor"])

def dataframe_to_excel_bytes(dfs: dict[str, pd.DataFrame]):
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "estudio_viabilidad_gpg.xlsx", "Descargar Excel", None
    except Exception:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for sheet_name, df in dfs.items():
                    df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "estudio_viabilidad_gpg.xlsx", "Descargar Excel", None
        except Exception:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for sheet_name, df in dfs.items():
                    zf.writestr(f"{sheet_name}.csv", df.to_csv(index=False).encode("utf-8-sig"))
            return zip_buffer.getvalue(), "application/zip", "estudio_viabilidad_gpg.zip", "Descargar ZIP CSV", "No se encontró motor Excel. Se genera ZIP con CSVs."

def build_pdf_bytes(inputs: dict, model: dict, risk_points: int, global_risk: str, dictamen_titulo: str, dictamen_texto: str):
    if not REPORTLAB_OK:
        return None
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    def line(label: str, value: str, y: float) -> float:
        c.drawString(15 * mm, y, f"{label}: {value}")
        return y - 5.2 * mm
    y = height - 18 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, y, "Estudio Viabilidad Proyecto by Gpg")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    y = line("Activo", str(inputs["activo"]), y)
    y = line("Escenario", str(inputs["escenario"]), y)
    y = line("PEM", eur(inputs["pem"]), y)
    y = line("Ingresos", eur(model["ingresos_totales"]), y)
    y = line("Coste total ex IVA compra", eur(model["coste_total_sin_iva_compra"]), y)
    y = line("Margen bruto", eur(model["margen_bruto"]), y)
    y = line("Margen sobre ventas", pct(model["margen_sobre_ventas"]), y)
    y = line("Contabilidad adicional", eur(model["coste_contabilidad_adicional"]), y)
    y = line("Riesgo global", str(global_risk), y)
    y = line("Puntos de riesgo", str(risk_points), y)
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

init_state()
inputs = build_inputs()

header_left, header_right = st.columns([0.72, 0.28])
with header_left:
    st.title("Estudio Viabilidad Proyecto by Gpg")
    st.caption("Versión definitiva: costes editables con % PEM sincronizado, contabilidad adicional por pestañas, exportación Excel/CSV/PDF y contabilidad integrada en el modelo.")
with header_right:
    st.info(f"Escenario activo: **{inputs['escenario']}**\n\nPEM: **{eur(inputs['pem'])}**\n\nm² vendibles: **{inputs['sup_vendible_m2']:.0f}**")

tabs = st.tabs(["Dashboard", "Costes editables", "Contabilidad adicional", "Ratios serios €/m²", "Resumen", "Cash-flow", "Riesgo", "Exportar"])
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = tabs

synced_editor_source = sync_cost_rows_with_pem(st.session_state["editable_costs_store"], inputs["pem"])

with tab2:
    st.subheader("Costes editables")
    left, right = st.columns([0.2, 0.8])
    with left:
        if st.button("Resetear tabla base", use_container_width=True):
            st.session_state["editable_costs_store"] = build_base_cost_df()
            st.session_state["reset_counter"] += 1
            st.rerun()
    with right:
        st.caption("Los importes y el % PEM se muestran en formato español real. Ejemplo: 10.955,49 y 2,35. La columna Bucket se ha eliminado.")

    editor_display_df = synced_editor_source.copy()
    editor_display_df["Coste editable (€)"] = editor_display_df["Coste editable (€)"].apply(fmt_es_currency)
    editor_display_df["% PEM"] = editor_display_df["% PEM"].apply(fmt_es_percent_from_ratio)

    editor_df = st.data_editor(
        editor_display_df,
        key=f"editable_costs_editor_{st.session_state['reset_counter']}",
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        disabled=["Auto"],
        column_config={
            "Fase": st.column_config.TextColumn("Fase"),
            "Hito": st.column_config.TextColumn("Hito"),
            "Concepto": st.column_config.TextColumn("Concepto"),
            "Coste editable (€)": st.column_config.TextColumn("Coste editable (€)", help="Formato: 10.955,49"),
            "% PEM": st.column_config.TextColumn("% PEM", help="Formato: 2,35"),
            "Observaciones": st.column_config.TextColumn("Observaciones"),
            "Auto": st.column_config.CheckboxColumn("Auto"),
        },
        column_order=["Fase", "Hito", "Concepto", "Coste editable (€)", "% PEM", "Observaciones", "Auto"],
    )

    editor_df["Coste editable (€)"] = editor_df["Coste editable (€)"].apply(parse_es_number)
    editor_df["% PEM"] = editor_df["% PEM"].apply(lambda x: parse_es_number(x) / 100.0)

    st.session_state["editable_costs_store"] = reconcile_cost_editor_changes(synced_editor_source, editor_df, inputs["pem"])
    st.metric("Total costes editables base", eur(float(st.session_state["editable_costs_store"]["Coste editable (€)"].sum())))

with tab3:
    st.subheader("Contabilidad adicional")
    top_a, top_b = st.columns([0.65, 0.35])
    with top_a:
        new_tab_name = st.text_input("Nombre de nueva pestaña contable", key="new_accounting_tab_name")
    with top_b:
        st.write("")
        if st.button("Añadir pestaña contable", use_container_width=True):
            tab_name = (new_tab_name or "").strip()
            if tab_name and tab_name not in st.session_state["custom_accounting_tabs"]:
                st.session_state["custom_accounting_tabs"][tab_name] = empty_accounting_tab_df()
                st.rerun()
    accounting_tab_names = list(st.session_state["custom_accounting_tabs"].keys())
    accounting_tabs = st.tabs(accounting_tab_names)
    summary_rows = []
    for idx, tab_name in enumerate(accounting_tab_names):
        with accounting_tabs[idx]:
            head_left, head_right = st.columns([0.78, 0.22])
            with head_left:
                st.caption(f"Apuntes incluidos en la contabilidad general: **{tab_name}**")
            with head_right:
                if len(accounting_tab_names) > 1 and st.button(f"Eliminar {tab_name}", key=f"delete_tab_{idx}", use_container_width=True):
                    st.session_state["custom_accounting_tabs"].pop(tab_name, None)
                    st.rerun()
            current_df = normalise_accounting_tab_df(st.session_state["custom_accounting_tabs"][tab_name])
            edited_accounting_df = st.data_editor(
                current_df,
                key=f"accounting_editor_{idx}",
                hide_index=True,
                width="stretch",
                num_rows="dynamic",
                column_config={
                    "Fecha": st.column_config.TextColumn("Fecha", help="Puedes poner un mes (ej. 6) o una fecha real."),
                    "Concepto": st.column_config.TextColumn("Concepto"),
                    "Importe (€)": st.column_config.NumberColumn("Importe (€)", step=500.0, format="%.2f"),
                    "Observaciones": st.column_config.TextColumn("Observaciones"),
                },
            )
            cleaned = normalise_accounting_tab_df(edited_accounting_df)
            st.session_state["custom_accounting_tabs"][tab_name] = cleaned
            total_tab = float(cleaned["Importe (€)"].sum()) if not cleaned.empty else 0.0
            summary_rows.append({"Pestaña": tab_name, "Importe (€)": total_tab, "% PEM": (total_tab / inputs["pem"]) if inputs["pem"] else 0.0})
    contabilidad_resumen_df = pd.DataFrame(summary_rows)
    total_conta = float(contabilidad_resumen_df["Importe (€)"].sum()) if not contabilidad_resumen_df.empty else 0.0
    m1, m2 = st.columns(2)
    m1.metric("Total contabilidad adicional", eur(total_conta))
    m2.metric("% PEM contabilidad adicional", pct((total_conta / inputs["pem"]) if inputs["pem"] else 0.0))
    if not contabilidad_resumen_df.empty:
        conta_show = contabilidad_resumen_df.copy()
        conta_show["Importe (€)"] = conta_show["Importe (€)"].map(eur)
        conta_show["% PEM"] = conta_show["% PEM"].map(pct_display_from_ratio)
        st.dataframe(display_df(conta_show), width="stretch", hide_index=True)

editable_cost_df = sync_cost_rows_with_pem(st.session_state["editable_costs_store"], inputs["pem"])
model = compute_model(inputs, editable_cost_df)
cashflow_df = build_cashflow(inputs, model)
risk_df, risk_points, global_risk = build_risk_df()
dictamen_titulo, dictamen_texto = build_dictamen(model, global_risk)

alertas = []
if risk_points >= 14:
    alertas.append("riesgo global alto")
if inputs["iva_compra"] >= 0.21:
    alertas.append("fiscalidad de compra sensible; exige validación escrita")
if model["margen_sobre_ventas"] < 0.15:
    alertas.append("margen por debajo del 15% orientativo")
if model["coste_contabilidad_adicional"] > 0:
    alertas.append("hay contabilidad adicional incorporada en el coste total")

with tab1:
    st.markdown(f"""
        <div class="gpg-card">
            <div class="gpg-kicker">Análisis promotor profesional</div>
            <div class="gpg-big">Estudio Viabilidad Proyecto by Gpg</div>
            <div class="gpg-sub">
                Activo: <strong>{inputs["activo"]}</strong> · Escenario: <strong>{inputs["escenario"]}</strong> ·
                PEM: <strong>{eur(inputs["pem"])}</strong> · m² vendibles: <strong>{inputs["sup_vendible_m2"]:.0f}</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
    row1 = st.columns(5)
    row1[0].metric("Ingresos brutos", eur(model["ingresos_totales"]))
    row1[1].metric("Coste total ex IVA compra", eur(model["coste_total_sin_iva_compra"]))
    row1[2].metric("Margen bruto", eur(model["margen_bruto"]))
    row1[3].metric("Margen sobre ventas", pct(model["margen_sobre_ventas"]))
    row1[4].metric("Cobertura ventas/coste", ratio(model["ratios"]["cover_ratio"]))
    row2 = st.columns(5)
    row2[0].metric("Contabilidad adicional", eur(model["coste_contabilidad_adicional"]))
    row2[1].metric("€ / m² coste total vendible", eur_m2(model["precio_m2_coste_total_vendible"]))
    row2[2].metric("€ / m² venta vendible", eur_m2(model["precio_m2_venta_vendible"]))
    row2[3].metric("€ / m² margen vendible", eur_m2(model["margen_m2_vendible"]))
    row2[4].metric("Riesgo global", global_risk)
    ficha = pd.DataFrame([["Activo", inputs["activo"]],["Referencia catastral", inputs["referencia_catastral"]],["PEM referencia", eur(inputs["pem"])],["Preset de producto", inputs["program_preset"]],["Mes licencia", str(inputs["mes_licencia"])],["Mes inicio obra", str(inputs["mes_inicio_obra"])],["Mes venta 4 viviendas", str(inputs["mes_venta_4v"])],["Mes entrega / escrituras", str(inputs["mes_entrega"])]], columns=["Campo","Valor"])
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

with tab4:
    st.subheader("Ratios serios €/m²")
    ratios_m2 = pd.DataFrame([
        ["m² construidos sobre rasante", f'{inputs["sup_construida_sr_m2"]:,.0f} m²'.replace(",", ".")],
        ["m² construidos bajo rasante", f'{inputs["sup_construida_br_m2"]:,.0f} m²'.replace(",", ".")],
        ["m² construidos totales", f'{inputs["sup_construida_total_m2"]:,.0f} m²'.replace(",", ".")],
        ["m² vendibles", f'{inputs["sup_vendible_m2"]:,.0f} m²'.replace(",", ".")],
        ["Precio m² construcción sobre rasante", eur_m2(model["precio_m2_construccion_sr"])],
        ["Precio m² construcción bajo rasante", eur_m2(model["precio_m2_construccion_br"])],
        ["Precio m² construcción total", eur_m2(model["precio_m2_construccion_total"])],
        ["Precio m² coste total vendible", eur_m2(model["precio_m2_coste_total_vendible"])],
        ["Precio venta m² vendible", eur_m2(model["precio_m2_venta_vendible"])],
        ["Margen m² vendible", eur_m2(model["margen_m2_vendible"])],
        ["Repercusión suelo m² vendible", eur_m2(model["repercusion_suelo_m2_vendible"])],
        ["Repercusión suelo m² sobre rasante", eur_m2(model["repercusion_suelo_m2_sr"])],
    ], columns=["Concepto", "Valor"])
    st.dataframe(display_df(ratios_m2), width="stretch", hide_index=True)

with tab5:
    st.subheader("Resumen económico")
    ingresos_df = pd.DataFrame([
        ["Viviendas", model["ingresos_viviendas"], model["ingresos_viviendas"] / inputs["pem"] if inputs["pem"] else 0.0],
        ["Garajes", model["ingresos_garajes"], model["ingresos_garajes"] / inputs["pem"] if inputs["pem"] else 0.0],
        ["Trasteros", model["ingresos_trasteros"], model["ingresos_trasteros"] / inputs["pem"] if inputs["pem"] else 0.0],
        ["Ingresos brutos totales", model["ingresos_totales"], model["ingresos_totales"] / inputs["pem"] if inputs["pem"] else 0.0],
    ], columns=["Concepto", "Importe (€)", "% PEM"])
    ingresos_show = ingresos_df.copy()
    ingresos_show["Importe (€)"] = ingresos_show["Importe (€)"].map(eur)
    ingresos_show["% PEM"] = ingresos_show["% PEM"].map(pct_display_from_ratio)
    st.dataframe(display_df(ingresos_show), width="stretch", hide_index=True)
    costes_show = model["costes_df"][["Fase", "Hito", "Concepto", "Coste (€)", "% PEM", "Observaciones"]].copy()
    costes_show["Coste (€)"] = costes_show["Coste (€)"].map(eur)
    costes_show["% PEM"] = costes_show["% PEM"].map(pct_display_from_ratio)
    st.subheader("Costes consolidados")
    st.dataframe(display_df(costes_show), width="stretch", hide_index=True)

with tab6:
    st.subheader("Cash-flow mensual")
    cf_show = cashflow_df.copy()
    for col in ["Entradas (€)", "Salidas (€)", "Flujo neto (€)", "Flujo acumulado (€)"]:
        cf_show[col] = cf_show[col].map(eur)
    st.dataframe(display_df(cf_show), width="stretch", hide_index=True)
    st.line_chart(cashflow_df.set_index("Mes")[["Entradas (€)", "Salidas (€)", "Flujo neto (€)", "Flujo acumulado (€)"]])

with tab7:
    st.subheader("Semáforo automático de riesgo")
    risk_show = risk_df.rename(columns={"categoria":"Categoría","estado":"Estado","puntos":"Puntos","comentario":"Comentario"})
    st.dataframe(display_df(risk_show), width="stretch", hide_index=True)
    if global_risk == "Alto":
        st.error(f"Riesgo global {global_risk} · {risk_points} puntos")
    elif global_risk == "Medio":
        st.warning(f"Riesgo global {global_risk} · {risk_points} puntos")
    else:
        st.success(f"Riesgo global {global_risk} · {risk_points} puntos")

with tab8:
    st.subheader("Exportación")
    export_costes = model["costes_df"][["Fase", "Hito", "Concepto", "Coste (€)", "% PEM", "Observaciones"]].copy()
    export_resumen = build_summary_df(inputs, model, risk_points, global_risk)
    export_ingresos = pd.DataFrame([
        {"Concepto": "Viviendas", "Importe (€)": model["ingresos_viviendas"]},
        {"Concepto": "Garajes", "Importe (€)": model["ingresos_garajes"]},
        {"Concepto": "Trasteros", "Importe (€)": model["ingresos_trasteros"]},
        {"Concepto": "Ingresos totales", "Importe (€)": model["ingresos_totales"]},
    ])
    export_dfs = {"Resumen": export_resumen,"Ingresos": export_ingresos,"Costes": export_costes,"Cashflow": cashflow_df,"Riesgo": risk_df}
    contabilidad_adicional_df = build_additional_accounting_df(inputs["pem"])
    if not contabilidad_adicional_df.empty:
        export_dfs["Contabilidad"] = contabilidad_adicional_df[["Fase", "Hito", "Concepto", "Coste (€)", "% PEM", "Observaciones"]]
    for tab_name, df in st.session_state.get("custom_accounting_tabs", {}).items():
        export_dfs[f"Conta_{tab_name}"[:31]] = normalise_accounting_tab_df(df)
    excel_bytes, excel_mime, excel_filename, excel_label, excel_warning = dataframe_to_excel_bytes(export_dfs)
    csv_bytes = export_costes.to_csv(index=False).encode("utf-8-sig")
    pdf_bytes = build_pdf_bytes(inputs, model, risk_points, global_risk, dictamen_titulo, dictamen_texto)
    c1, c2, c3 = st.columns(3)
    c1.download_button(excel_label, data=excel_bytes, file_name=excel_filename, mime=excel_mime, use_container_width=True)
    if excel_warning:
        c1.caption(excel_warning)
    c2.download_button("Descargar CSV de costes", data=csv_bytes, file_name="costes_estudio_gpg.csv", mime="text/csv", use_container_width=True)
    if pdf_bytes is not None:
        c3.download_button("Descargar PDF resumen", data=pdf_bytes, file_name="estudio_viabilidad_gpg.pdf", mime="application/pdf", use_container_width=True)
    st.caption("La contabilidad adicional se integra en costes, márgenes, cash-flow y exportaciones.")
