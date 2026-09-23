"""Acceso, cuenta y notificaciones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from .. import db
from ..config import settings
from ..security import COOKIE, requiere_usuario, usuario_actual, verificar_csrf
from ..web import render

router = APIRouter()

INICIO = {"colaborador": "/hoy", "director": "/equipo", "rrhh": "/rrhh", "dg": "/direccion", "superadmin": "/admin"}


def inicio_por_rol(u: dict) -> str:
    return INICIO.get(u["rol"], "/hoy")


@router.get("/login")
def login_get(request: Request, next: str = "/"):
    if usuario_actual(request):
        return RedirectResponse("/", status_code=307)
    return render(request, "login.html", None, next=next, error=None)


@router.post("/login")
def login_post(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form("/")):
    ip = request.client.host if request.client else "?"
    claves = (f"u:{email.strip().lower()}", f"ip:{ip}")
    if any(db.intentos_recientes(c, settings.LOGIN_VENTANA_MIN) >= settings.LOGIN_MAX_INTENTOS for c in claves):
        db.log("warn", "seguridad", "Acceso bloqueado por intentos", f"{email} {ip}")
        return render(request, "login.html", None, next=next, error="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.", status_code=429)
    u = db.verificar_credenciales(email, password)
    if not u:
        for c in claves:
            db.registrar_intento(c)
        return render(request, "login.html", None, next=next, error="Correo o contraseña incorrectos.", status_code=401)
    for c in claves:
        db.limpiar_intentos(c)
    token, _ = db.crear_sesion_auth(u["id"], settings.SESION_HORAS)
    destino = next if next.startswith("/") and not next.startswith("//") else "/"
    if destino == "/":
        destino = inicio_por_rol(u)
    resp = RedirectResponse(destino, status_code=303)
    resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, max_age=settings.SESION_HORAS * 3600, path="/")
    db.log("info", "acceso", "Inicio de sesión", ip, u["email"])
    return resp


@router.get("/salir")
def salir(request: Request):
    token = request.cookies.get(COOKIE, "")
    if token:
        db.cerrar_sesion_auth(token)
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE, path="/")
    return resp


@router.get("/cuenta")
def cuenta(request: Request, primer_acceso: int = 0, ok: int = 0):
    u = usuario_actual(request)
    if not u:
        return RedirectResponse("/login", status_code=307)
    return render(request, "cuenta.html", u, primer_acceso=primer_acceso or u.get("debe_cambiar_password"), ok=ok, error=None)


@router.post("/cuenta/password")
def cuenta_password(request: Request, actual: str = Form(""), nueva: str = Form(""), confirmar: str = Form(""), csrf: str = Form("")):
    u = usuario_actual(request)
    if not u:
        return RedirectResponse("/login", status_code=307)
    verificar_csrf(request, u, csrf)
    if not db.verificar_credenciales(u["email"], actual):
        return render(request, "cuenta.html", u, primer_acceso=u.get("debe_cambiar_password"), ok=0, error="La contraseña actual no es correcta.")
    if len(nueva) < settings.PASSWORD_MIN or nueva != confirmar:
        return render(request, "cuenta.html", u, primer_acceso=u.get("debe_cambiar_password"), ok=0,
                      error=f"La nueva contraseña debe tener al menos {settings.PASSWORD_MIN} caracteres y coincidir con la confirmación.")
    db.cambiar_password(u["id"], nueva)
    db.log("info", "acceso", "Cambio de contraseña", "", u["email"])
    return RedirectResponse(inicio_por_rol(u) if u.get("debe_cambiar_password") else "/cuenta?ok=1", status_code=303)


@router.get("/notificaciones")
def notificaciones(request: Request, u: dict = Depends(requiere_usuario)):
    lista = db.notificaciones(u["id"], limite=80)
    db.marcar_leidas(u["id"])
    return render(request, "notificaciones.html", u, lista=lista)
