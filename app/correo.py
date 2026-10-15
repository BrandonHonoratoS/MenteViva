"""Correo saliente (SMTP) para los avisos de Mente Viva.

- Se activa con SMTP_HOST + SMTP_USER + SMTP_PASSWORD (y SMTP_FROM opcional). Gmail/Google Workspace: smtp.gmail.com, 587, contraseña de
  aplicación; Brevo/SendGrid/Resend: su host y API key como contraseña. Sin configuración, los avisos se quedan sólo en la plataforma.
- Cada aviso in-app se envía también por correo si la persona no lo desactivó (Mi cuenta) y está activa. El envío corre en un hilo y
  nunca bloquea ni rompe el aviso; los fallos quedan en la bitácora (con límite para no inundarla).
"""
from __future__ import annotations

import html
import logging
import smtplib
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr

from . import db
from .config import settings

log = logging.getLogger("mv.correo")
_ULTIMO_ERROR = {"t": 0.0}
ENVIADOS_PRUEBA: list[dict] = []   # en modo prueba (sin SMTP) se registran aquí en vez de enviarse


def activo() -> bool:
    return settings.EMAIL_ENABLED and bool(settings.SMTP_HOST and settings.SMTP_USER)


def _html(titulo: str, cuerpo: str, enlace: str, nombre: str) -> str:
    url = (settings.BASE_URL + enlace) if enlace.startswith("/") else (enlace or settings.BASE_URL)
    boton = f'<a href="{html.escape(url)}" style="display:inline-block;margin-top:18px;padding:12px 20px;border-radius:12px;background:#7C3AED;color:#fff;text-decoration:none;font-weight:700">Abrir en Mente Viva</a>'
    return f"""<!doctype html><html><body style="margin:0;background:#F6F4FF;font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#1E1B4B">
<div style="max-width:560px;margin:24px auto;background:#fff;border-radius:18px;padding:28px;border:1px solid #E9E6F7">
<div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#7C3AED;font-weight:700">Mente Viva</div>
<h2 style="margin:10px 0 6px;font-size:20px">{html.escape(titulo)}</h2>
<p style="color:#4B4870;line-height:1.5;margin:0">Hola {html.escape(nombre.split(' ')[0])}. {html.escape(cuerpo)}</p>
{boton}
<p style="margin-top:26px;font-size:12px;color:#8B88A8">Recibes este correo porque tienes activados los avisos por correo en Mente Viva. Puedes desactivarlos en <a href="{html.escape(settings.BASE_URL)}/cuenta" style="color:#7C3AED">Mi cuenta</a>.<br>¿Dudas? {html.escape(settings.SOPORTE_NOMBRE)} · {html.escape(settings.SOPORTE_TEL)} · {html.escape(settings.SOPORTE_EMAIL)}</p>
</div></body></html>"""


def enviar(destinatario: str, asunto: str, titulo: str, cuerpo: str, enlace: str = "", nombre: str = "") -> bool:
    """Envío síncrono. Devuelve True si salió (o si se registró en modo prueba)."""
    if not activo():
        ENVIADOS_PRUEBA.append({"a": destinatario, "asunto": asunto, "titulo": titulo, "cuerpo": cuerpo, "enlace": enlace})
        return settings.APP_ENV == "test"
    msg = EmailMessage()
    msg["Subject"] = f"{asunto}"
    msg["From"] = formataddr(("Mente Viva", settings.SMTP_FROM or settings.SMTP_USER))
    msg["To"] = destinatario
    msg.set_content(f"{titulo}\n\n{cuerpo}\n\n{settings.BASE_URL}{enlace if enlace.startswith('/') else ''}")
    msg.add_alternative(_html(titulo, cuerpo, enlace, nombre or destinatario), subtype="html")
    try:
        if settings.SMTP_SSL or settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
                s.ehlo()
                s.starttls()
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("correo a %s falló: %s", destinatario, e)
        if time.time() - _ULTIMO_ERROR["t"] > 300:   # una entrada en bitácora cada 5 minutos como máximo
            _ULTIMO_ERROR["t"] = time.time()
            db.log("warn", "correo", "No se pudo enviar un correo", f"{type(e).__name__}: {str(e)[:300]} (host {settings.SMTP_HOST}:{settings.SMTP_PORT})")
        return False


def enviar_async(destinatario: str, asunto: str, titulo: str, cuerpo: str, enlace: str = "", nombre: str = "") -> None:
    if settings.APP_ENV == "test" or not activo():
        enviar(destinatario, asunto, titulo, cuerpo, enlace, nombre)
        return
    threading.Thread(target=enviar, args=(destinatario, asunto, titulo, cuerpo, enlace, nombre), daemon=True, name="mv-correo").start()


def al_notificar(usuario_id: int, titulo: str, cuerpo: str, enlace: str, tipo: str) -> None:
    """Hook de db.notificar: reenvía el aviso por correo a quien lo tenga activado."""
    if not (activo() or settings.APP_ENV == "test"):
        return
    u = db.usuario(usuario_id)
    if not u or not u.get("activo") or not int(u.get("correo_notif") if u.get("correo_notif") is not None else 1):
        return
    enviar_async(u["email"], f"Mente Viva · {titulo}"[:120], titulo, cuerpo, enlace, u["nombre"])


def probar(destinatario: str) -> tuple[bool, str]:
    """Correo de prueba desde Admin."""
    if not activo():
        return False, "SMTP no configurado: define SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (y SMTP_FROM) en Render → Environment."
    ok = enviar(destinatario, "Mente Viva · prueba de correo", "El correo de Mente Viva funciona", "Este es un mensaje de prueba enviado desde el panel de administración.", "/hoy", "")
    return ok, ("Correo enviado; revisa la bandeja (y spam)." if ok else "No se pudo enviar: revisa la bitácora para ver el error del servidor SMTP.")


def instalar() -> None:
    if al_notificar not in db.NOTIF_HOOKS:
        db.NOTIF_HOOKS.append(al_notificar)
