"""API JSON usada por la interfaz (chat de sesiones, onboarding, chats del analista y del coach)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

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
            "turnos_max": C.turnos_max_sesion(s), "fin": fin}


def _respuesta_turno(sid: int, u: dict, r: dict) -> dict:
    s = db.sesion(sid)
    fin = r.get("estado") == "fin" or r.get("fase") == "fin"
    if fin:
        motor.terminar(s, db.usuario(u["id"]), en_hilo=not settings.ANALISIS_SINCRONO)
    return {"mensaje": r.get("texto"), "meta": {k: v for k, v in r.items() if k != "texto"}, "turnos": s["turnos"], "turnos_max": C.turnos_max_sesion(s), "fin": fin}


def _turno_con_adjunto(sid: int, u: dict, texto: str, meta: dict) -> dict:
    s = _sesion_propia(sid, u)
    try:
        r = motor.turno(s, db.usuario(u["id"]), texto, meta_usuario=meta)
    except motor.SesionOcupada as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    return _respuesta_turno(sid, u, r)


@router.post("/sesiones/{sid}/audio")
async def audio(sid: int, request: Request, u: dict = Depends(requiere_usuario), archivo: UploadFile = File(...), csrf: str = Form(""), duracion: float = Form(0.0)):
    """Grabación de voz: se transcribe y se mide (una llamada), se guarda sólo la transcripción con sus métricas y el avatar responde."""
    verificar_csrf(request, u, csrf)
    s = _sesion_propia(sid, u)
    hab = C.habilidad(s["habilidad"]) or {}
    if not settings.AUDIO_ENABLED or not hab.get("audio"):
        raise HTTPException(400, "Esta práctica no usa grabaciones de voz.")
    if s["estado"] != "en_curso":
        raise HTTPException(409, "La sesión ya terminó.")
    from ..agents import adjuntos as AD
    data = await archivo.read()
    try:
        a = AD.transcribir_audio(db.usuario(u["id"]), s, data, archivo.content_type or "", duracion or None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    finally:
        del data   # el audio no se conserva
    out = _turno_con_adjunto(sid, u, AD.texto_mensaje_audio(a), {"audio": a})
    out["transcripcion"] = a["transcripcion"]
    out["audio"] = {k: a[k] for k in ("duracion_s", "ppm", "muletillas", "muletillas_min", "ritmo", "variedad_vocal", "seguridad", "energia_cierre")}
    return out


@router.post("/sesiones/{sid}/foto")
async def foto(sid: int, request: Request, u: dict = Depends(requiere_usuario), archivo: UploadFile = File(...), csrf: str = Form(""), comentario: str = Form("")):
    """Foto del outfit (propia o de referencia): se describe de forma objetiva (una llamada), se guarda sólo la descripción y el avatar responde."""
    verificar_csrf(request, u, csrf)
    s = _sesion_propia(sid, u)
    hab = C.habilidad(s["habilidad"]) or {}
    if not settings.FOTO_ENABLED or not hab.get("foto"):
        raise HTTPException(400, "Esta práctica no usa fotos.")
    if s["estado"] != "en_curso":
        raise HTTPException(409, "La sesión ya terminó.")
    from ..agents import adjuntos as AD
    data = await archivo.read()
    try:
        f = AD.describir_foto(db.usuario(u["id"]), s, data, archivo.content_type or "", archivo.filename or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))
    finally:
        del data   # la imagen no se conserva
    out = _turno_con_adjunto(sid, u, AD.texto_mensaje_foto(f, comentario[:500]), {"foto": f})
    out["foto"] = {"codigo_detectado": f["codigo_detectado"], "descripcion": f["descripcion"][:300], "es_outfit": f["es_outfit"]}
    return out


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
            "turnos_max": C.turnos_max_sesion(s), "fin": fin, "n_mensajes": len([m for m in mensajes if m["rol"] in ("usuario", "avatar")]),
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
    if s["estado"] in ("en_curso", "error") or (s["estado"] == "analizando" and not motor.analizando_ahora(sid)):
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
    if s["estado"] == "analizando" and not motor.analizando_ahora(sid):
        motor.lanzar_analisis(sid)   # el análisis se interrumpió (reinicio del servidor): se relanza solo
        s = db.sesion(sid)
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


@router.post("/socrates/{lid}/chat")
async def socrates_chat(lid: int, request: Request, u: dict = Depends(requiere_usuario)):
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    lec = db.leccion(lid)
    if not lec or lec["usuario_id"] != u["id"]:
        raise HTTPException(404, "Lección no encontrada")
    if lec["estado"] != "lista":
        raise HTTPException(409, "La lección todavía no está lista.")
    texto = str(body.get("texto", "")).strip()[:2000]
    if not texto:
        raise HTTPException(400, "Escribe tu duda.")
    from ..agents import socrates as S
    try:
        return S.chat(db.usuario(u["id"]), lec, texto)
    except PresupuestoAgotado as e:
        raise HTTPException(402, str(e))
    except ErrorLLM as e:
        raise HTTPException(503, str(e))


@router.post("/actividad/bloque")
async def actividad_bloque(request: Request, u: dict = Depends(requiere_usuario)):
    """La pantalla de sesión/lección avisa cuando se completó un bloque de 5 minutos (modalidad "Prepárate 5 minutos")."""
    body = await _json(request)
    verificar_csrf(request, u, body.get("csrf"))
    db.registrar_actividad(u["id"], minutos=settings.MICRO_MINUTOS, bloques=1)
    r = db.racha_dias(u["id"])
    return {"ok": True, "racha": r["dias"], "bloques_hoy": db.actividad_hoy(u["id"])["bloques"]}


@router.get("/socrates/{lid}/estado")
def socrates_estado(lid: int, u: dict = Depends(requiere_usuario)):
    lec = db.leccion(lid)
    if not lec or lec["usuario_id"] != u["id"]:
        raise HTTPException(404, "Lección no encontrada")
    return {"estado": lec["estado"], "error": lec.get("error") or ""}


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
