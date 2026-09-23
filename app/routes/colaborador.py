"""Pantallas del colaborador: Hoy, diagnóstico con Elena, planes, catálogo, sesiones, reportes, historial y autoevaluación."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db, metrics
from ..agents import catalogo as C
from ..agents import motor
from ..agents.avatares import AVATARES
from ..llm import PresupuestoAgotado
from ..llm.gemini import ErrorLLM
from ..security import puede_ver_transcripcion, puede_ver_usuario, requiere_rol, requiere_usuario, verificar_csrf
from ..web import render

router = APIRouter()
colab = requiere_rol("colaborador")


def _habilidades(u: dict) -> list[dict]:
    return C.habilidades_empresa(db.empresa(u.get("empresa_id")))


@router.get("/hoy")
def hoy(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    en_curso = db.sesion_en_curso(u["id"])
    resumen = metrics.resumen_colaborador(db.usuario(u["id"]))
    siguiente = db.siguiente_item(u["id"]) if perfil.get("estado") == "completo" else None
    roadmaps = db.roadmaps(u["id"], ("activo", "propuesto"))
    recientes = [s for s in db.sesiones(usuario_id=u["id"], estado="completada", limite=5) if s["tipo"] == "practica"]
    niveles = db.niveles(u["id"])
    serie = metrics.serie_scores(u["id"])
    notif = db.notificaciones(u["id"], solo_no_leidas=True, limite=5)
    return render(request, "hoy.html", u, perfil=perfil, en_curso=en_curso, resumen=resumen, siguiente=siguiente, roadmaps=roadmaps, recientes=recientes,
                  niveles=niveles, serie=serie, notif=notif, habilidades=_habilidades(u))


# ── diagnóstico con Elena ────────────────────────────────────────────────────
@router.get("/diagnostico")
def diagnostico(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    if perfil.get("estado") == "completo":
        return RedirectResponse("/mi-diagnostico", status_code=307)
    sesion = db.sesion_en_curso(u["id"])
    if sesion and sesion["tipo"] != "diagnostico":
        return RedirectResponse(f"/sesion/{sesion['id']}", status_code=307)
    if perfil.get("estado") == "analizando" and perfil.get("sesion_diagnostico_id"):
        return RedirectResponse(f"/sesion/{perfil['sesion_diagnostico_id']}", status_code=307)
    habs = {h["id"] for h in _habilidades(u)}
    variables = [v for v in C.ONBOARDING if not (v["grupo"] == "Ruta DM" and "ruta_dm" not in habs)]
    return render(request, "diagnostico.html", u, perfil=perfil, sesion=sesion, variables=variables, grupo_ventas=C.GRUPO_VENTAS_IDS,
                  mensajes=db.mensajes(sesion["id"]) if sesion else [])


@router.post("/diagnostico/iniciar")
def diagnostico_iniciar(request: Request, u: dict = Depends(colab), csrf: str = Form("")):
    verificar_csrf(request, u, csrf)
    perfil = db.perfil(u["id"])
    if perfil.get("estado") not in ("onboarding", "entrevista"):
        raise HTTPException(400, "Primero responde el cuestionario de perfil.")
    if db.sesion_en_curso(u["id"]):
        return RedirectResponse("/diagnostico", status_code=303)
    try:
        s = motor.iniciar(db.usuario(u["id"]), "entrevistas", tipo="diagnostico", nivel="Intermedio", objetivo="Diagnóstico inicial de competencias")
    except (PresupuestoAgotado, ErrorLLM) as e:
        return render(request, "diagnostico.html", u, perfil=perfil, sesion=None, variables=C.ONBOARDING, grupo_ventas=C.GRUPO_VENTAS_IDS, mensajes=[], error=str(e))
    db.guardar_perfil(u["id"], estado="entrevista", sesion_diagnostico_id=s["id"])
    return RedirectResponse(f"/sesion/{s['id']}", status_code=303)


@router.get("/mi-diagnostico")
def mi_diagnostico(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    if perfil.get("estado") != "completo":
        return RedirectResponse("/diagnostico", status_code=307)
    return render(request, "mi_diagnostico.html", u, perfil=perfil, diag=perfil.get("diagnostico") or {}, niveles=db.niveles(u["id"]),
                  roadmaps=db.roadmaps(u["id"], ("activo", "propuesto")), competencias=C.COMPETENCIAS_DIAGNOSTICO)


@router.post("/diagnostico/repetir")
def diagnostico_repetir(request: Request, u: dict = Depends(colab), csrf: str = Form("")):
    verificar_csrf(request, u, csrf)
    db.guardar_perfil(u["id"], estado="pendiente")
    return RedirectResponse("/diagnostico", status_code=303)


# ── planes y catálogo ────────────────────────────────────────────────────────
@router.get("/roadmaps")
def roadmaps(request: Request, u: dict = Depends(colab)):
    rms = db.roadmaps(u["id"])
    return render(request, "roadmaps.html", u, roadmaps=rms, niveles=db.niveles(u["id"]), en_curso=db.sesion_en_curso(u["id"]), perfil=db.perfil(u["id"]))


@router.get("/catalogo")
def catalogo(request: Request, u: dict = Depends(colab)):
    return render(request, "catalogo.html", u, habilidades=_habilidades(u), proximamente=C.PROXIMAMENTE, niveles=db.niveles(u["id"]), perfil=db.perfil(u["id"]),
                  en_curso=db.sesion_en_curso(u["id"]))


@router.get("/entrenar/{habilidad}")
def entrenar(request: Request, habilidad: str, u: dict = Depends(colab), item: int | None = None):
    hab = C.habilidad(habilidad)
    if not hab or hab not in _habilidades(u):
        raise HTTPException(404, "Habilidad no disponible")
    perfil = db.perfil(u["id"])
    if perfil.get("estado") != "completo":
        return RedirectResponse("/diagnostico", status_code=307)
    en_curso = db.sesion_en_curso(u["id"])
    if en_curso:
        return RedirectResponse(f"/sesion/{en_curso['id']}", status_code=307)
    it = None if item == 0 else (db.roadmap_item(item) if item else db.siguiente_item(u["id"], habilidad))
    if it and (it["usuario_id"] != u["id"] or it["estado"] != "pendiente" or it.get("roadmap_estado") != "activo"):
        it = None
    niv = db.nivel(u["id"], habilidad) or {}
    nivel = (it or {}).get("nivel") or niv.get("nivel") or hab["niveles"][0]
    sig_dm = C.nivel_dm_siguiente(nivel) if habilidad == "ruta_dm" else None
    return render(request, "entrenar.html", u, hab=hab, item=it, nivel=nivel, niv=niv, perfil=perfil, avatar=AVATARES[hab["agente"]],
                  competencias=C.competencias_dm(sig_dm) if sig_dm else [], sig_dm=sig_dm, valor_dm=C.valor_dm(sig_dm) if sig_dm else "",
                  duracion=C.duracion_min(habilidad, nivel), kpis=hab.get("kpis", []), pesos=(hab.get("pesos") or {}).get(nivel, {}))


@router.post("/entrenar/{habilidad}/iniciar")
def entrenar_iniciar(request: Request, habilidad: str, u: dict = Depends(colab), csrf: str = Form(""), item: int = Form(0), nivel: str = Form(""),
                     competencia: str = Form(""), producto: str = Form(""), objetivo: str = Form("")):
    verificar_csrf(request, u, csrf)
    hab = C.habilidad(habilidad)
    if not hab or hab not in _habilidades(u):
        raise HTTPException(404, "Habilidad no disponible")
    it = db.roadmap_item(item) if item else None
    if it and (it["usuario_id"] != u["id"] or it["estado"] != "pendiente"):
        it = None
    if nivel and nivel not in hab["niveles"]:
        nivel = ""
    extra = {"producto": producto.strip()[:200]} if producto.strip() else {}
    try:
        s = motor.iniciar(db.usuario(u["id"]), habilidad, item=it, nivel=nivel or None, competencia=competencia.strip()[:80], objetivo=objetivo.strip()[:300],
                          voluntaria=it is None, escenario_extra=extra)
    except motor.SesionOcupada as e:
        raise HTTPException(409, str(e))
    except (PresupuestoAgotado, ErrorLLM) as e:
        raise HTTPException(503, str(e))
    return RedirectResponse(f"/sesion/{s['id']}", status_code=303)


# ── sesión y reporte ─────────────────────────────────────────────────────────
@router.get("/sesion/{sid}")
def sesion(request: Request, sid: int, u: dict = Depends(requiere_usuario)):
    s = db.sesion(sid)
    if not s or not puede_ver_transcripcion(u, s):
        raise HTTPException(404, "Sesión no encontrada")
    if s["estado"] in ("completada",) and s["usuario_id"] == u["id"]:
        return RedirectResponse(f"/sesion/{sid}/reporte", status_code=307)
    hab = C.HABILIDADES[s["habilidad"]]
    return render(request, "sesion.html", u, s=s, hab=hab, avatar=AVATARES[s["agente"]], mensajes=db.mensajes(sid),
                  turnos_max=C.turnos_max(s["habilidad"], s.get("nivel")), duracion=C.duracion_min(s["habilidad"], s.get("nivel")), propia=s["usuario_id"] == u["id"])


@router.get("/sesion/{sid}/reporte")
def reporte(request: Request, sid: int, u: dict = Depends(requiere_usuario)):
    s = db.sesion(sid)
    if not s or not puede_ver_usuario(u, db.usuario(s["usuario_id"])):
        raise HTTPException(404, "Sesión no encontrada")
    if s["estado"] != "completada":
        return RedirectResponse(f"/sesion/{sid}", status_code=307) if s["usuario_id"] == u["id"] else render(request, "error.html", u, codigo=404, detalle="La sesión aún no tiene reporte.")
    if s["tipo"] == "diagnostico":
        return RedirectResponse("/mi-diagnostico" if s["usuario_id"] == u["id"] else f"/colaborador/{s['usuario_id']}", status_code=307)
    hab = C.HABILIDADES[s["habilidad"]]
    res = s.get("resultado") or {}
    anterior = next((x for x in db.sesiones(usuario_id=s["usuario_id"], habilidad=s["habilidad"], estado="completada", limite=20)
                     if x["id"] < sid and x["tipo"] == "practica"), None)
    chat = db.obtener_chat(u["id"], f"reporte:{sid}") if s["usuario_id"] == u["id"] else None
    analisis = db.analisis(s["empresa_id"], tipo="post_sesion", sesion_id=sid, limite=1) if u["rol"] in ("rrhh", "director", "dg") else []
    return render(request, "reporte.html", u, s=s, hab=hab, res=res, avatar=AVATARES[s["agente"]], anterior=anterior, chat=chat, propia=s["usuario_id"] == u["id"],
                  kpis_def={k["id"]: k for k in hab.get("kpis", [])}, pesos=(hab.get("pesos") or {}).get(s.get("nivel") or "", {}),
                  siguiente=db.siguiente_item(s["usuario_id"], s["habilidad"]), analisis=analisis[0] if analisis else None,
                  mostrar_transcripcion=puede_ver_transcripcion(u, s), mensajes=db.mensajes(sid) if puede_ver_transcripcion(u, s) else [],
                  minutos=motor.minutos_transcurridos(s))


@router.get("/historial")
def historial(request: Request, u: dict = Depends(colab)):
    ss = db.sesiones(usuario_id=u["id"], limite=200)
    return render(request, "historial.html", u, sesiones=ss, serie=metrics.serie_scores(u["id"], limite=30), resumen=metrics.resumen_colaborador(db.usuario(u["id"])))


@router.get("/autoevaluacion")
def autoevaluacion(request: Request, u: dict = Depends(colab), ok: int = 0):
    return render(request, "autoevaluacion.html", u, preguntas=C.PREGUNTAS_AUTO, previas=db.evaluaciones(usuario_id=u["id"], tipo="auto"), periodo=db.periodo(), ok=ok)


@router.post("/autoevaluacion")
async def autoevaluacion_post(request: Request, u: dict = Depends(colab)):
    form = await request.form()
    verificar_csrf(request, u, form.get("csrf"))
    resp = {p["id"]: int(form.get(p["id"], 0) or 0) for p in C.PREGUNTAS_AUTO}
    if any(v < 1 or v > 5 for v in resp.values()):
        raise HTTPException(400, "Responde todas las preguntas del 1 al 5.")
    db.guardar_evaluacion("auto", u["id"], u["id"], db.periodo(), resp, str(form.get("comentario", ""))[:1000])
    return RedirectResponse("/autoevaluacion?ok=1", status_code=303)
