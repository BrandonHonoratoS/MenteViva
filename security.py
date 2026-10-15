"""Autenticación por cookie de sesión, CSRF, roles y alcance de datos por rol.

Roles (de mayor a menor alcance):
- superadmin  equipo Mente Viva: empresas, usuarios, modelo de IA, presupuesto, bitácora. No ve conversaciones.
- rrhh        gestiona áreas, usuarios, metas y aprobaciones de su empresa; ve transcripciones (con trazabilidad).
- dg          consulta la organización completa (métricas, nombres, recomendaciones); sin transcripciones.
- director    ve su área: scores, feedback, roadmaps, evaluaciones; sin transcripciones.
- colaborador ve sólo lo propio.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from . import db

COOKIE = "mv_sesion"
ROLES = {"superadmin": 5, "rrhh": 4, "dg": 3, "director": 2, "colaborador": 1}
NOMBRES_ROL = {"superadmin": "Mente Viva", "rrhh": "Recursos Humanos", "dg": "Dirección General",
               "director": "Director de área", "colaborador": "Colaborador"}


def usuario_actual(request: Request) -> dict | None:
    return db.usuario_por_token(request.cookies.get(COOKIE, ""))


def requiere_usuario(request: Request) -> dict:
    u = usuario_actual(request)
    if not u:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión requerida")
        raise HTTPException(status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": f"/login?next={request.url.path}"})
    if u.get("debe_cambiar_password") and not request.url.path.startswith(("/cuenta", "/salir", "/static", "/api/cuenta")):
        raise HTTPException(status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/cuenta?primer_acceso=1"})
    return u


def requiere_rol(*roles: str):
    def _dep(u: dict = Depends(requiere_usuario)) -> dict:
        if u["rol"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta sección")
        return u
    return _dep


def es_manager(u: dict) -> bool:
    return u["rol"] in ("rrhh", "dg", "director", "superadmin")


def puede_ver_usuario(u: dict, objetivo: dict | None) -> bool:
    """¿Puede `u` ver la ficha (scores, feedback, roadmaps) de `objetivo`?"""
    if not objetivo:
        return False
    if u["id"] == objetivo["id"]:
        return True
    if u["rol"] == "superadmin":
        return False   # el equipo Mente Viva no consulta datos personales de colaboradores
    if u.get("empresa_id") != objetivo.get("empresa_id"):
        return False
    if u["rol"] in ("rrhh", "dg"):
        return True
    if u["rol"] == "director":
        return objetivo.get("area_id") is not None and objetivo.get("area_id") == u.get("area_id")
    return False


def puede_ver_transcripcion(u: dict, sesion: dict) -> bool:
    """La conversación completa sólo la ven el propio colaborador y RRHH de su empresa."""
    if u["id"] == sesion["usuario_id"]:
        return True
    return u["rol"] == "rrhh" and u.get("empresa_id") == sesion.get("empresa_id")


def alcance_usuarios(u: dict) -> list[dict]:
    """Colaboradores visibles para un manager según su rol."""
    if u["rol"] == "director":
        return [x for x in db.usuarios(u["empresa_id"], area_id=u.get("area_id")) if x["rol"] == "colaborador" or x["id"] == u["id"]]
    if u["rol"] in ("rrhh", "dg"):
        return [x for x in db.usuarios(u["empresa_id"]) if x["rol"] in ("colaborador", "director")]
    return []


def verificar_csrf(request: Request, u: dict, token: str | None) -> None:
    """Toda petición que cambia estado debe traer el token CSRF de la sesión (formulario o cabecera X-CSRF)."""
    esperado = u.get("csrf", "")
    recibido = token or request.headers.get("X-CSRF", "")
    if not esperado or recibido != esperado:
        db.log("warn", "seguridad", "CSRF inválido", f"{request.method} {request.url.path}", u.get("email"))
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de seguridad inválido; recarga la página")
