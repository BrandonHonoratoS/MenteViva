"""Motor de sesiones: abre, conversa, cierra y analiza cada práctica con el avatar que corresponda.

Eficiencia de tokens
- Instrucciones estables primero (caché implícita), perfil y escenario después.
- Al modelo sólo viajan la memoria comprimida + los últimos `TURNOS_VENTANA` mensajes.
- La memoria se comprime con el modelo ligero cada `TURNOS_RESUMEN` turnos.
- El análisis final recibe la transcripción completa UNA sola vez.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from .. import db
from ..config import settings
from ..llm import PresupuestoAgotado, llm
from ..llm.gemini import ErrorLLM
from . import catalogo as C
from . import esquemas as E
from . import prompts as P
from . import validar as V
from .avatares import AVATARES, Juan, agente_para, json_compacto, transcript_texto

log = logging.getLogger("mv.motor")
_LOCKS: dict[int, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock(sesion_id: int) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(sesion_id, threading.Lock())


class SesionOcupada(RuntimeError):
    pass


# ── apertura ─────────────────────────────────────────────────────────────────
def iniciar(usuario: dict, habilidad_id: str, item: dict | None = None, nivel: str | None = None, competencia: str = "",
            objetivo: str = "", tipo: str = "practica", voluntaria: bool = False, escenario_extra: dict | None = None) -> dict:
    """Crea la sesión y genera el primer mensaje del avatar."""
    if db.sesion_en_curso(usuario["id"]):
        raise SesionOcupada("Ya tienes una sesión en curso. Termínala o descártala antes de abrir otra.")
    hab = C.habilidad(habilidad_id)
    if not hab:
        raise ValueError("Habilidad desconocida")
    agente = agente_para(habilidad_id)
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding", {})
    niv = db.nivel(usuario["id"], habilidad_id)
    nivel = nivel or (item or {}).get("nivel") or (niv or {}).get("nivel") or hab["niveles"][0]
    competencia = competencia or (item or {}).get("competencia") or ""
    objetivo = objetivo or (item or {}).get("objetivo") or ""
    escenario = dict(escenario_extra or {})
    if habilidad_id == "ventas":
        escenario.setdefault("etapa_debil", ob.get("etapa_debil", ""))
        escenario.setdefault("producto", ob.get("producto_concreto", ""))
    if habilidad_id == "ruta_dm" and not competencia:
        sig = C.nivel_dm_siguiente(nivel) or nivel
        competencia = (C.competencias_dm(sig) or ["Comunicación"])[0]

    sid = db.crear_sesion(usuario["id"], habilidad_id, agente.id, tipo=tipo, roadmap_item_id=(item or {}).get("id"), nivel=nivel,
                          competencia=competencia, objetivo=objetivo, escenario=escenario, voluntaria=voluntaria)
    db.log("info", "sesion", f"Sesión {sid} iniciada", f"{habilidad_id} · {nivel} · {competencia or '-'}", usuario["email"])
    try:
        continuar(db.sesion(sid), usuario)
    except (PresupuestoAgotado, ErrorLLM) as e:
        # La sesión queda abierta sin apertura: la pantalla la pedirá de nuevo (botón Reintentar / reintento automático).
        db.log("warn", "sesion", f"Sesión {sid}: apertura pendiente", str(e), usuario["email"])
        if isinstance(e, PresupuestoAgotado):
            db.actualizar_sesion(sid, estado="error", error=str(e), fin=db.now())
            raise
    return db.sesion(sid)


def continuar(sesion: dict, usuario: dict) -> dict | None:
    """Genera lo que falte para que la conversación avance: el diseño (Juan), la apertura o la respuesta a un mensaje del usuario
    que quedó sin contestar por un fallo de la IA. Idempotente: si no falta nada, no llama al modelo."""
    lk = _lock(sesion["id"])
    if not lk.acquire(blocking=False):
        raise SesionOcupada("El avatar todavía está respondiendo.")
    try:
        sesion = db.sesion(sesion["id"])
        if sesion["estado"] != "en_curso":
            raise SesionOcupada("La sesión ya terminó.")
        agente = agente_para(sesion["habilidad"])
        perfil = db.perfil(usuario["id"])
        escenario = dict(sesion.get("escenario") or {})
        if agente is Juan and not escenario.get("titulo"):
            historial = _historial_competencia(usuario["id"], sesion.get("competencia") or "")
            prompt, schema = Juan.prompt_diseno(sesion, usuario, perfil, historial)
            r = llm.generar(origen="juan.diseno", system=prompt, contents=[{"role": "user", "text": "Diseña la sesión."}], schema=schema,
                            thinking=settings.GEMINI_THINKING_ANALISIS, max_tokens=3000, usuario_id=usuario["id"], sesion_id=sesion["id"], temperatura=0.8)
            V.registrar_si_incompleto("juan.diseno", r.json, usuario.get("email", ""))
            dis = V.diseno_juan(r.json, sesion)
            escenario.update(dis)
            db.actualizar_sesion(sesion["id"], escenario_json=escenario, formato=dis["formato"])
            sesion = db.sesion(sesion["id"])
        mensajes = [m for m in db.mensajes(sesion["id"]) if m["rol"] in ("usuario", "avatar")]
        if not mensajes:
            texto_fijo, pista = agente.apertura(sesion)
            if texto_fijo:
                meta = {"tension": (escenario.get("dificultad_inicial") or 2) * 15, "estado": "en_curso"}
                db.guardar_mensaje(sesion["id"], "avatar", texto_fijo, meta)
                return {"texto": texto_fijo, **meta}
            return _generar_turno(sesion, usuario, perfil, pista, origen_extra="apertura")
        if mensajes[-1]["rol"] == "usuario":
            resp = _generar_turno(sesion, usuario, perfil)
            if mensajes[-1]["texto"].lower().strip(" .!¡¿?") in ("fin", "terminar", "adiós", "adios", "ya"):
                resp["estado"] = "fin"
            return resp
        ultimo = mensajes[-1]
        return {"texto": ultimo["texto"], **(ultimo.get("meta") or {})}
    finally:
        lk.release()


def _historial_competencia(usuario_id: int, competencia: str) -> list[dict]:
    out = []
    for s in db.sesiones(usuario_id=usuario_id, habilidad="ruta_dm", estado="completada", limite=30):
        if s.get("competencia") == competencia and s.get("resultado"):
            out.append({"fecha": s["inicio"], "score": s["resultado"].get("score_global"), "dominio": s["resultado"].get("nivel_dominio")})
    return list(reversed(out))


# ── conversación ─────────────────────────────────────────────────────────────
def _contenidos(sesion: dict, mensajes: list[dict], pista_apertura: str | None = None) -> list[dict]:
    contents: list[dict] = []
    memoria = (sesion.get("resumen") or {}).get("memoria")
    corte = (sesion.get("resumen") or {}).get("hasta_mensaje", 0)
    recientes = [m for m in mensajes if m["id"] > corte and m["rol"] in ("usuario", "avatar")]
    if len(recientes) > settings.TURNOS_VENTANA * 2:
        recientes = recientes[-settings.TURNOS_VENTANA * 2:]
    if memoria:
        contents.append({"role": "user", "text": f"[Memoria de lo conversado hasta ahora: {memoria}]"})
        contents.append({"role": "model", "text": "(continúo en personaje)"})
    for m in recientes:
        contents.append({"role": "user" if m["rol"] == "usuario" else "model", "text": m["texto"]})
    if pista_apertura:
        contents.append({"role": "user", "text": pista_apertura})
    if not contents or contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "text": "(inicio de la conversación)"})
    return contents


def _generar_turno(sesion: dict, usuario: dict, perfil: dict, pista: str | None = None, origen_extra: str = "turno") -> dict:
    agente = agente_para(sesion["habilidad"])
    mensajes = db.mensajes(sesion["id"])
    contents = _contenidos(sesion, mensajes, pista)
    restantes = C.turnos_max(sesion["habilidad"], sesion.get("nivel")) - int(sesion.get("turnos") or 0)
    if restantes <= 2 and not pista:
        contents[-1]["text"] += f"\n[sistema: quedan {max(restantes, 0)} turnos de práctica. Si no hay cierre, termina la sesión en este turno de forma natural y marca estado fin.]"
    r = llm.generar(origen=f"{agente.id}.{origen_extra}", system=agente.system(sesion, usuario, perfil), contents=contents, schema=agente.schema_para(sesion),
                    max_tokens=1200, temperatura=0.85, usuario_id=usuario["id"], sesion_id=sesion["id"])
    V.registrar_si_incompleto(f"{agente.id}.{origen_extra}", r.json, usuario.get("email", ""))
    js = V.turno(r.json, r.texto)
    texto = js["mensaje"]
    if not texto:
        raise ErrorLLM("La IA devolvió una respuesta vacía o incompleta. Pulsa Reintentar.")
    meta = {k: v for k, v in js.items() if k != "mensaje"}
    if "fase" in meta and meta["fase"] == "fin":
        meta["estado"] = "fin"
    db.guardar_mensaje(sesion["id"], "avatar", texto, meta)
    tension = int(meta.get("tension") or 0)
    if tension > int(sesion.get("tension_max") or 0):
        db.actualizar_sesion(sesion["id"], tension_max=tension)
    return {"texto": texto, **meta}


def turno(sesion: dict, usuario: dict, texto: str) -> dict:
    """Procesa un mensaje del usuario y devuelve la respuesta del avatar."""
    lk = _lock(sesion["id"])
    if not lk.acquire(blocking=False):
        raise SesionOcupada("El avatar todavía está respondiendo.")
    try:
        sesion = db.sesion(sesion["id"])
        if sesion["estado"] != "en_curso":
            raise SesionOcupada("La sesión ya terminó.")
        texto = (texto or "").strip()[:2000]
        if not texto:
            raise ValueError("Escribe algo para continuar.")
        db.guardar_mensaje(sesion["id"], "usuario", texto)
        sesion = db.sesion(sesion["id"])
        perfil = db.perfil(usuario["id"])
        if int(sesion["turnos"]) >= settings.TURNOS_MAX_SESION:
            db.guardar_mensaje(sesion["id"], "avatar", "Con esto cerramos la práctica por hoy. Vamos al análisis.", {"estado": "fin"})
            return {"texto": "Con esto cerramos la práctica por hoy. Vamos al análisis.", "estado": "fin"}
        if texto.lower().strip(" .!¡¿?") in ("fin", "terminar", "adiós", "adios", "ya"):
            resp = _generar_turno(sesion, usuario, perfil, None, origen_extra="turno")
            resp["estado"] = "fin"
            return resp
        resp = _generar_turno(sesion, usuario, perfil)
        _quiza_resumir(sesion, usuario)
        return resp
    finally:
        lk.release()


def _quiza_resumir(sesion: dict, usuario: dict) -> None:
    """Comprime la parte antigua de la conversación cuando excede la ventana (modelo ligero, ~150 tokens de salida).

    Se comprime todo lo anterior a los últimos TURNOS_VENTANA mensajes, así el avatar nunca pierde contexto: lo antiguo viaja
    como memoria breve y lo reciente completo.
    """
    sesion = db.sesion(sesion["id"])
    mensajes = db.mensajes(sesion["id"])
    corte = (sesion.get("resumen") or {}).get("hasta_mensaje", 0)
    recientes = [m for m in mensajes if m["id"] > corte and m["rol"] in ("usuario", "avatar")]
    if len(recientes) <= settings.TURNOS_VENTANA * 2:
        return
    antiguos = recientes[:-settings.TURNOS_VENTANA]
    previo = (sesion.get("resumen") or {}).get("memoria", "")
    texto = ("Memoria previa: " + previo + "\n" if previo else "") + "\n".join(f"{m['rol']}: {m['texto']}" for m in antiguos)
    try:
        r = llm.generar(origen="motor.resumen", system=P.RESUMEN_CONVERSACION, contents=[{"role": "user", "text": texto[-6000:]}], schema=E.RESUMEN,
                        clase="ligero", thinking="off", max_tokens=800, temperatura=0.2, usuario_id=usuario["id"], sesion_id=sesion["id"])
        memoria = (r.json or {}).get("memoria") or r.texto
        db.actualizar_sesion(sesion["id"], resumen_json={"memoria": memoria[:1200], "hasta_mensaje": antiguos[-1]["id"]})
    except (PresupuestoAgotado, ErrorLLM):
        pass


# ── cierre y análisis ────────────────────────────────────────────────────────
def terminar(sesion: dict, usuario: dict, en_hilo: bool = True) -> None:
    """Marca la sesión como 'analizando' y lanza el análisis final (feedback + analista)."""
    sesion = db.sesion(sesion["id"])
    if sesion["estado"] != "en_curso":
        return
    if int(sesion["turnos"]) == 0:
        db.actualizar_sesion(sesion["id"], estado="descartada", fin=db.now())
        return
    db.actualizar_sesion(sesion["id"], estado="analizando", fin=db.now())
    if en_hilo:
        threading.Thread(target=analizar, args=(sesion["id"],), daemon=True, name=f"analisis-{sesion['id']}").start()
    else:
        analizar(sesion["id"])


def descartar(sesion: dict) -> None:
    db.actualizar_sesion(sesion["id"], estado="descartada", fin=db.now())


def analizar(sesion_id: int) -> None:
    from . import analista, roadmap  # import tardío: evita ciclos
    sesion = db.sesion(sesion_id)
    if not sesion or sesion["estado"] != "analizando":
        return
    usuario = db.usuario(sesion["usuario_id"])
    try:
        mensajes = db.mensajes(sesion_id)
        agente = agente_para(sesion["habilidad"])
        transcript = transcript_texto(mensajes, usuario["nombre"], AVATARES[agente.id]["nombre"])
        if sesion["tipo"] == "diagnostico":
            roadmap.analizar_diagnostico(sesion, usuario, transcript)
            return
        prompt, schema = agente.prompt_feedback(sesion)
        r = llm.generar(origen=f"{agente.id}.feedback", system=prompt, contents=[{"role": "user", "text": "TRANSCRIPCIÓN:\n" + transcript}], schema=schema,
                        thinking=settings.GEMINI_THINKING_ANALISIS, max_tokens=8000, temperatura=0.3, usuario_id=usuario["id"], sesion_id=sesion_id)
        if not isinstance(r.json, dict):
            raise ErrorLLM("El análisis no devolvió un resultado válido. Pulsa Reintentar análisis.")
        resultado = {"elena": V.feedback_entrevistas, "celeste": V.feedback_ventas, "juan": V.feedback_dm}[agente.id](r.json, sesion)
        score = agente.score(resultado, sesion)
        resultado["score_global_100"] = score
        resultado["turnos"] = sesion["turnos"]
        db.actualizar_sesion(sesion_id, estado="completada", score_global=score, resultado_json=resultado)
        if sesion.get("roadmap_item_id"):
            db.actualizar_item(sesion["roadmap_item_id"], estado="completada", sesion_id=sesion_id)
        db.log("info", "sesion", f"Sesión {sesion_id} analizada", f"score {score}", usuario["email"])
        analista.post_sesion(db.sesion(sesion_id), usuario)
    except (PresupuestoAgotado, ErrorLLM) as e:
        db.actualizar_sesion(sesion_id, estado="error", error=str(e))
        db.log("error", "sesion", f"Sesión {sesion_id} sin análisis", str(e), usuario["email"])
    except Exception as e:  # noqa: BLE001
        log.exception("Fallo analizando sesión %s", sesion_id)
        db.actualizar_sesion(sesion_id, estado="error", error=f"Error interno: {e}")
        db.log("error", "sesion", f"Sesión {sesion_id} error interno", str(e), usuario["email"])


def reintentar_analisis(sesion_id: int) -> None:
    s = db.sesion(sesion_id)
    if s and s["estado"] == "error" and s["turnos"] > 0:
        db.actualizar_sesion(sesion_id, estado="analizando", error="")
        if settings.ANALISIS_SINCRONO:
            analizar(sesion_id)
        else:
            threading.Thread(target=analizar, args=(sesion_id,), daemon=True).start()


def minutos_transcurridos(sesion: dict) -> int:
    try:
        ini = datetime.fromisoformat(sesion["inicio"])
        fin = datetime.fromisoformat(sesion["fin"]) if sesion.get("fin") else datetime.now(timezone.utc)
        return max(0, int((fin - ini).total_seconds() // 60))
    except (TypeError, ValueError):
        return 0
