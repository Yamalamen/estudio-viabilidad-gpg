"""
Tareas programadas con APScheduler.
Se arrancan UNA sola vez al iniciar la app Streamlit.
"""
import threading
from datetime import datetime

_scheduler_started = False
_lock = threading.Lock()


def start_scheduler():
    """Inicia el scheduler de alertas (una sola vez por proceso)."""
    global _scheduler_started
    with _lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone="Europe/Madrid")
        scheduler.add_job(
            _check_alertas_1mes,
            CronTrigger(hour=8, minute=0),
            id="alertas_1mes",
            replace_existing=True,
        )
        scheduler.add_job(
            _check_alertas_3meses,
            CronTrigger(hour=8, minute=5),
            id="alertas_3meses",
            replace_existing=True,
        )
        scheduler.start()
        print("[Scheduler] Iniciado correctamente — alertas diarias a las 08:00 h")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")


def _check_alertas_1mes():
    """Busca avisos con 30+ días sin cerrar y envía alertas."""
    try:
        from services.avisos import get_avisos_por_alertar, marcar_alerta_enviada
        from services.notificaciones import crear_notificacion
        from services.email_service import send_alerta_antiguedad
        from datetime import date

        avisos = get_avisos_por_alertar(dias=30)
        for av in avisos:
            if not av.get("coordinador_id"):
                continue
            try:
                fecha = datetime.strptime(av["fecha_solicitud"][:10], "%Y-%m-%d").date()
                dias  = (date.today() - fecha).days
            except Exception:
                dias = 30

            mensaje = (
                f"⚠️ El aviso #{av['num_aviso']} ({av['sede']}) "
                f"lleva {dias} días pendiente sin cerrar."
            )
            crear_notificacion(
                user_id=av["coordinador_id"],
                mensaje=mensaje,
                tipo="alerta_1mes",
                aviso_id=av["id"],
            )
            if av.get("coordinador_email"):
                send_alerta_antiguedad(
                    coordinador_email=av["coordinador_email"],
                    coordinador_nombre=av["coordinador_nombre"] or "Coordinador",
                    num_aviso=av["num_aviso"],
                    sede=av["sede"] or "",
                    dias=dias,
                    descripcion=av["descripcion"] or "",
                )
            marcar_alerta_enviada(av["id"], "1mes")
    except Exception as e:
        print(f"[Scheduler] Error en alertas 1 mes: {e}")


def _check_alertas_3meses():
    """Busca avisos con 90+ días sin cerrar y envía alertas urgentes."""
    try:
        from services.avisos import get_avisos_por_alertar, marcar_alerta_enviada
        from services.notificaciones import crear_notificacion
        from services.email_service import send_alerta_antiguedad
        from datetime import date

        avisos = get_avisos_por_alertar(dias=90)
        for av in avisos:
            if not av.get("coordinador_id"):
                continue
            try:
                fecha = datetime.strptime(av["fecha_solicitud"][:10], "%Y-%m-%d").date()
                dias  = (date.today() - fecha).days
            except Exception:
                dias = 90

            mensaje = (
                f"🔴 URGENTE: El aviso #{av['num_aviso']} ({av['sede']}) "
                f"lleva {dias} días pendiente — más de 3 meses sin cerrar."
            )
            crear_notificacion(
                user_id=av["coordinador_id"],
                mensaje=mensaje,
                tipo="alerta_3meses",
                aviso_id=av["id"],
            )
            if av.get("coordinador_email"):
                send_alerta_antiguedad(
                    coordinador_email=av["coordinador_email"],
                    coordinador_nombre=av["coordinador_nombre"] or "Coordinador",
                    num_aviso=av["num_aviso"],
                    sede=av["sede"] or "",
                    dias=dias,
                    descripcion=av["descripcion"] or "",
                )
            marcar_alerta_enviada(av["id"], "3meses")
    except Exception as e:
        print(f"[Scheduler] Error en alertas 3 meses: {e}")
