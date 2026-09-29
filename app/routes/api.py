"""API JSON usada por la interfaz (chat de sesiones, onboarding, chats del analista y del coach)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import db
from ..config import settings
from ..agents import analista, catalogo as C, motor
from ..agents.avatares import AVATARES
from ..llm import PresupuestoAgotado
from ..llm.gemini import ErrorLLM
from ..security import es_manager, requiere_usuario, verificar_csrf

router = APIRouter(prefix="/api")


async def _json(request: Request) -> dict:
    try:
        return await request.json()
    except ValueError:
        return {}


def _sesion_propia(sid: int, u: dict) -> dict:
    s = db.sesion(sid)
    if not s or s["usuario_id"] != u["id"]:
        raise HTTPException(404, "Sesión no encontrada")
    return s


@router.post("/sesiones/{sid}/mensaje")
async def mensaje(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    try:
        r = motor.turno(s, db.usuario(u["id"]), body.get("texto", ""))
    except motor.SesionOcupada as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    s = db.sesion(sid)
    fin = r.get("estado") == "fin" or r.get("fase") == "fin"
    if fin:
        motor.terminar(s, db.usuario(u["id"]), en_hilo=not settings.ANALISIS_SINCRONO)
    return {"mensaje": r.get("texto"), "meta": {k: v for k, v in r.items() if k != "texto"}, "turnos": s["turnos"],
            "turnos_max": C.turnos_max(s["habilidad"], s.get("nivel")), "fin": fin}


@router.post("/sesiones/{sid}/continuar")
async def continuar(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    """Reintenta lo que falte (diseño, apertura o respuesta pendiente) tras un fallo transitorio de la IA."""
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    try:
        r = motor.continuar(s, db.usuario(u["id"]))
    except motor.SesionOcupada as e:
        raise HTTPException(409, str(e))
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    s = db.sesion(sid)
    fin = bool(r) and (r.get("estado") == "fin" or r.get("fase") == "fin")
    if fin:
        motor.terminar(s, db.usuario(u["id"]), en_hilo=not settings.ANALISIS_SINCRONO)
    mensajes = db.mensajes(sid)
    return {"mensaje": (r or {}).get("texto"), "meta": {k: v for k, v in (r or {}).items() if k != "texto"}, "turnos": s["turnos"],
            "turnos_max": C.turnos_max(s["habilidad"], s.get("nivel")), "fin": fin, "n_mensajes": len([m for m in mensajes if m["rol"] in ("usuario", "avatar")]),
            "escenario": {k: (s.get("escenario") or {}).get(k) for k in ("titulo", "encuadre", "situacion", "formato", "personaje")}}


@router.post("/sesiones/{sid}/terminar")
async def terminar(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    motor.terminar(s, db.usuario(u["id"]), en_hilo=not settings.ANALISIS_SINCRONO)
    s = db.sesion(sid)
    return {"estado": s["estado"]}


@router.post("/sesiones/{sid}/descartar")
async def descartar(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    if s["estado"] in ("en_curso", "error"):
        motor.descartar(s)
        if s["tipo"] == "diagnostico":
            db.guardar_perfil(u["id"], estado="onboarding", sesion_diagnostico_id=None)
    return {"estado": db.sesion(sid)["estado"]}


@router.post("/sesiones/{sid}/reintentar")
async def reintentar(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    if s["tipo"] == "diagnostico":
        db.guardar_perfil(u["id"], estado="analizando")
    motor.reintentar_analisis(sid)
    return {"estado": db.sesion(sid)["estado"]}


@router.get("/sesiones/{sid}/estado")
def estado(sid: int, u: dict = Depends(requiere_usuario)):
    s = _sesion_propia(sid, u)
    destino = None
    if s["estado"] == "completada":
        destino = "/mi-diagnostico" if s["tipo"] == "diagnostico" else f"/sesion/{sid}/reporte"
    return {"estado": s["estado"], "error": s.get("error") or "", "destino": destino, "score": s.get("score_global")}


@router.post("/diagnostico/onboarding")
async def onboarding(request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    respuestas = body.get("respuestas") or {}
    validas = {}
    for v in C.ONBOARDING:
        val = respuestas.get(v["id"])
        if v.get("multiple"):
            val = [x for x in (val or []) if x in v["opciones"]]
            if val:
                validas[v["id"]] = val
        elif val in v["opciones"]:
            validas[v["id"]] = val
    if str(body.get("producto_concreto", "")).strip():
        validas["producto_concreto"] = str(body["producto_concreto"]).strip()[:200]
    faltan = [v["id"] for v in C.ONBOARDING if v["id"] not in validas and v["grupo"] in ("Tu rol", "Tu plan")]
    if faltan:
        raise HTTPException(400, "Faltan respuestas: " + ", ".join(faltan))
    perfil = db.perfil(u["id"])
    if perfil.get("estado") == "completo":
        raise HTTPException(400, "El diagnóstico ya está completo.")
    db.guardar_perfil(u["id"], onboarding=validas, estado="onboarding")
    return {"ok": True}


@router.post("/analista/chat")
async def analista_chat(request: Request, u: dict = Depends(requiere_usuario)):
    if not es_manager(u) or u["rol"] == "superadmin":
        raise HTTPException(403, "El Analista atiende a directores, RRHH y Dirección General.")
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    texto = str(body.get("texto", "")).strip()[:2000]
    if not texto:
        raise HTTPException(400, "Escribe tu pregunta.")
    try:
        return analista.chat(u, texto)
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))


@router.post("/analista/chat/limpiar")
async def analista_limpiar(request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    db.borrar_chat(u["id"], "analista")
    return {"ok": True}


@router.post("/reporte/{sid}/chat")
async def reporte_chat(sid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    s = _sesion_propia(sid, u)
    if s["estado"] != "completada":
        raise HTTPException(400, "La sesión no tiene reporte todavía.")
    texto = str(body.get("texto", "")).strip()[:1500]
    if not texto:
        raise HTTPException(400, "Escribe tu pregunta.")
    try:
        r = analista.coach_reporte(u, s, texto)
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    return {"texto": r["texto"], "avatar": AVATARES[s["agente"]]["nombre"]}


@router.get("/notificaciones/pendientes")
def pendientes(u: dict = Depends(requiere_usuario)):
    return {"n": len(db.notificaciones(u["id"], solo_no_leidas=True, limite=20))}
