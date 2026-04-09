"""
Servicio de envío de emails via Microsoft 365 (SMTP).
Las credenciales se leen del fichero config_email.py o variables de entorno.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────
try:
    from config_email import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, FROM_NAME
except ImportError:
    SMTP_SERVER   = os.getenv("SMTP_SERVER",   "smtp.office365.com")
    SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USER    = os.getenv("EMAIL_USER",    "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    FROM_NAME     = os.getenv("FROM_NAME",     "Mantenimiento Sedes Judiciales")


def _send(to_email: str, subject: str, body_html: str) -> bool:
    """Envía un correo HTML. Devuelve True si se envió correctamente."""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print(f"[EMAIL] Sin credenciales configuradas — email NO enviado a {to_email}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{EMAIL_USER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"[EMAIL] Enviado a {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando a {to_email}: {e}")
        return False


def _base_template(titulo: str, cuerpo: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#1A1A2E;background:#F5F7FA;padding:20px;">
      <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;
                  box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden;">
        <div style="background:#1E3A5F;padding:20px 30px;">
          <h2 style="color:#fff;margin:0;">⚙️ Mantenimiento Sedes Judiciales</h2>
          <p style="color:#A0C4FF;margin:5px 0 0;">Alicante · Departamento de Mantenimiento</p>
        </div>
        <div style="padding:24px 30px;">
          <h3 style="color:#1E3A5F;">{titulo}</h3>
          {cuerpo}
        </div>
        <div style="background:#F0F4F8;padding:12px 30px;font-size:12px;color:#666;">
          Mensaje automático generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </div>
      </div>
    </body></html>
    """


def send_asignacion(coordinador_email: str, coordinador_nombre: str,
                    num_aviso: int, sede: str, descripcion: str) -> bool:
    subject = f"[Mantenimiento] Nuevo aviso asignado — Aviso #{num_aviso}"
    cuerpo = f"""
    <p>Hola <strong>{coordinador_nombre}</strong>,</p>
    <p>Se te ha asignado un nuevo aviso de mantenimiento:</p>
    <table style="border-collapse:collapse;width:100%;">
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;width:140px;">Nº Aviso</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0;">{num_aviso}</td></tr>
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;">Sede</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0;">{sede}</td></tr>
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;">Descripción</td>
          <td style="padding:8px;">{descripcion[:300]}{'...' if len(descripcion or '')>300 else ''}</td></tr>
    </table>
    <p style="margin-top:16px;">Accede a la aplicación para ver los detalles completos y actualizar el estado.</p>
    """
    return _send(coordinador_email, subject, _base_template("Aviso asignado", cuerpo))


def send_falta_material(laura_email: str, coordinador_nombre: str,
                        num_aviso: int, sede: str, material: str) -> bool:
    subject = f"[Mantenimiento] Falta material — Aviso #{num_aviso}"
    cuerpo = f"""
    <p>Hola <strong>Laura</strong>,</p>
    <p>El coordinador <strong>{coordinador_nombre}</strong> ha indicado que falta material
       para el aviso <strong>#{num_aviso}</strong> en la sede <strong>{sede}</strong>.</p>
    <div style="background:#FFF3CD;border-left:4px solid #FFC107;padding:12px 16px;border-radius:4px;margin:16px 0;">
      <strong>Material necesario:</strong><br/>{material}
    </div>
    <p>Por favor, gestiona el suministro del material indicado.</p>
    """
    return _send(laura_email, subject, _base_template("⚠️ Falta material", cuerpo))


def send_alerta_antiguedad(coordinador_email: str, coordinador_nombre: str,
                           num_aviso: int, sede: str, dias: int, descripcion: str) -> bool:
    if dias >= 90:
        color = "#DC3545"
        label = f"más de 3 meses ({dias} días)"
        icon  = "🔴"
    else:
        color = "#FD7E14"
        label = f"más de 1 mes ({dias} días)"
        icon  = "🟠"

    subject = f"[Mantenimiento] {icon} Aviso pendiente #{num_aviso} — {label}"
    cuerpo = f"""
    <p>Hola <strong>{coordinador_nombre}</strong>,</p>
    <p>El siguiente aviso lleva <strong style="color:{color};">{label}</strong> sin cerrarse:</p>
    <table style="border-collapse:collapse;width:100%;">
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;width:140px;">Nº Aviso</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0;">{num_aviso}</td></tr>
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;">Sede</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0;">{sede}</td></tr>
      <tr><td style="padding:8px;background:#F5F7FA;font-weight:bold;">Descripción</td>
          <td style="padding:8px;">{descripcion[:300]}{'...' if len(descripcion or '')>300 else ''}</td></tr>
    </table>
    <p style="margin-top:16px;">Por favor, actualiza el estado del aviso o contacta con el supervisor.</p>
    """
    return _send(coordinador_email, subject, _base_template(f"{icon} Aviso pendiente sin cerrar", cuerpo))
