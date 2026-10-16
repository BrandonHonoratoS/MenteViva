"""Pantallas del colaborador: Hoy, diagnóstico con Elena, planes, catálogo, sesiones, reportes, historial y autoevaluación."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db, metrics
from ..config import settings
from ..agents import catalogo as C
from ..agents import laboratorio as L
from ..agents import motor
from ..agents.avatares import AVATARES
from ..llm import PresupuestoAgotado
from ..llm.gemini import ErrorLLM
from ..security import puede_ver_transcripcion, puede_ver_usuario, requiere_rol, requiere_usuario, verificar_csrf
from ..web import render

router = APIRouter()
colab = requiere_rol("colaborador")
entrena = requiere_rol("colaborador", "director")   # los directores también entrenan (Liderazgo); sus resultados los ven RRHH y DG, no su equipo


def _encuesta_obligatoria(u: dict):
    """Tras la primera práctica completada, la encuesta de experiencia es obligatoria antes de abrir otra sesión."""
    if u["rol"] == "colaborador" and db.pendiente_encuesta(u["id"]):
        return RedirectResponse("/encuesta?obligatoria=1", status_code=307)
    return None


def _habilidades(u: dict) -> list[dict]:
    return C.habilidades_empresa(db.empresa(u.get("empresa_id")))


@router.get("/hoy")
def hoy(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    en_curso = db.sesion_en_curso(u["id"])
    resumen = metrics.resumen_colaborador(db.usuario(u["id"]))
    siguiente = db.siguiente_item(u["id"]) if perfil.get("estado") == "completo" else None
    if siguiente:
        from ..agents import socrates as S
        siguiente["tema_socrates"] = S.tema_para_item(siguiente["habilidad"], siguiente)
        lec = db.leccion_por_tema(u["id"], siguiente["habilidad"], siguiente["tema_socrates"])
        siguiente["leccion"] = lec if lec and lec["estado"] == "lista" else None
    roadmaps = db.roadmaps(u["id"], ("activo", "propuesto"))
    from ..agents import roadmap as RM
    plan_faltan = RM.habilidades_sin_plan(u) if perfil.get("estado") == "completo" and roadmaps else []
    recientes = [s for s in db.sesiones(usuario_id=u["id"], estado="completada", limite=5) if s["tipo"] in ("practica", "laboratorio")]
    niveles = db.niveles(u["id"])
    serie = metrics.serie_scores(u["id"])
    notif = db.notificaciones(u["id"], solo_no_leidas=True, limite=5)
    return render(request, "hoy.html", u, perfil=perfil, en_curso=en_curso, resumen=resumen, siguiente=siguiente, roadmaps=roadmaps, recientes=recientes,
                  niveles=niveles, serie=serie, notif=notif, habilidades=_habilidades(u), encuesta_pendiente=db.pendiente_encuesta(u["id"]),
                  racha=db.racha_dias(u["id"]), plan_faltan=plan_faltan, hoy_act=db.actividad_hoy(u["id"]), micro_min=settings.MICRO_MINUTOS, micro_horas=settings.MICRO_HORAS)


# ── diagnóstico con Elena ────────────────────────────────────────────────────
@router.get("/diagnostico")
def diagnostico(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    if perfil.get("estado") == "completo":
        return RedirectResponse("/mi-diagnostico", status_code=307)
    sesion = db.sesion_en_curso(u["id"])
    if sesion:
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
    abierta = db.sesion_en_curso(u["id"])
    if abierta:
        return RedirectResponse(f"/sesion/{abierta['id']}", status_code=303)
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


@router.post("/diagnostico/planes")
def diagnostico_planes(request: Request, u: dict = Depends(colab), csrf: str = Form("")):
    """Regenera los planes que faltaron (fallo transitorio de la IA al cerrar el diagnóstico)."""
    verificar_csrf(request, u, csrf)
    from ..agents import roadmap
    try:
        creados = roadmap.generar_roadmaps_faltantes(db.usuario(u["id"]))
    except (PresupuestoAgotado, ErrorLLM) as e:
        raise HTTPException(503, str(e))
    db.log("info", "roadmap", f"Planes regenerados para {u['email']}", ", ".join(creados), u["email"])
    return RedirectResponse("/roadmaps", status_code=303)


@router.post("/diagnostico/repetir")
def diagnostico_repetir(request: Request, u: dict = Depends(colab), csrf: str = Form("")):
    verificar_csrf(request, u, csrf)
    db.guardar_perfil(u["id"], estado="pendiente")
    return RedirectResponse("/diagnostico", status_code=303)


# ── planes y catálogo ────────────────────────────────────────────────────────
@router.get("/roadmaps")
def roadmaps(request: Request, u: dict = Depends(colab)):
    from ..agents import roadmap
    rms = db.roadmaps(u["id"])
    perfil = db.perfil(u["id"])
    plan = roadmap.resumen_plan_integral(u) if perfil.get("estado") == "completo" else None
    return render(request, "roadmaps.html", u, roadmaps=rms, niveles=db.niveles(u["id"]), en_curso=db.sesion_en_curso(u["id"]), perfil=perfil, plan=plan)


def _relevantes(u: dict, perfil: dict | None = None) -> tuple[list[dict], list[dict]]:
    perfil = perfil or db.perfil(u["id"])
    return C.habilidades_relevantes(perfil.get("onboarding") or {}, perfil.get("diagnostico"), _habilidades(u))


@router.get("/catalogo")
def catalogo(request: Request, u: dict = Depends(colab)):
    perfil = db.perfil(u["id"])
    relevantes, otras = _relevantes(u, perfil)
    return render(request, "catalogo.html", u, habilidades=relevantes, otras=otras, proximamente=C.PROXIMAMENTE, niveles=db.niveles(u["id"]), perfil=perfil,
                  en_curso=db.sesion_en_curso(u["id"]))


def _hab_entrenable(u: dict, habilidad: str) -> dict:
    hab = C.habilidad(habilidad)
    if not hab or hab not in _habilidades(u) or (u["rol"] == "director" and not hab.get("para_directores")):
        raise HTTPException(404, "Habilidad no disponible")
    return hab


@router.get("/entrenar/{habilidad}")
def entrenar(request: Request, habilidad: str, u: dict = Depends(entrena), item: int | None = None):
    hab = _hab_entrenable(u, habilidad)
    perfil = db.perfil(u["id"])
    if perfil.get("estado") != "completo" and u["rol"] == "colaborador":
        return RedirectResponse("/diagnostico", status_code=307)
    en_curso = db.sesion_en_curso(u["id"])
    if en_curso:
        return RedirectResponse(f"/sesion/{en_curso['id']}", status_code=307)
    bloqueo = _encuesta_obligatoria(u)
    if bloqueo:
        return bloqueo
    it = None if (item == 0 or u["rol"] == "director") else (db.roadmap_item(item) if item else db.siguiente_item(u["id"], habilidad))
    if it and (it["usuario_id"] != u["id"] or it["estado"] != "pendiente" or it.get("roadmap_estado") != "activo"):
        it = None
    if it and it.get("tipo") == "laboratorio":
        return RedirectResponse(f"/laboratorio?item={it['id']}", status_code=307)
    niv = db.nivel(u["id"], habilidad) or {}
    nivel = (it or {}).get("nivel") or niv.get("nivel") or hab["niveles"][0]
    sig_dm = C.nivel_dm_siguiente(nivel) if habilidad == "ruta_dm" else None
    from ..agents import socrates as S
    leccion = None
    if it and (u.get("modalidad") or "completa") == "completa":
        lec = db.leccion_por_tema(u["id"], habilidad, S.tema_para_item(habilidad, it))
        leccion = lec if lec and lec["estado"] == "lista" else None
    from ..agents import conocimiento as K
    estilo = (niv.get("competencias") or {}).get("estilo") if hab.get("test") == "liderazgo" else None
    historial = [x for x in db.sesiones(usuario_id=u["id"], habilidad=habilidad, estado="completada", limite=3) if x["tipo"] == "practica"]
    return render(request, "entrenar.html", u, hab=hab, item=it, nivel=nivel, niv=niv, perfil=perfil, avatar=AVATARES[hab["agente"]], leccion=leccion,
                  tema_socrates=S.tema_para_item(habilidad, it) if it else "",
                  competencias=C.competencias_dm(sig_dm) if sig_dm else [], sig_dm=sig_dm, valor_dm=C.valor_dm(sig_dm) if sig_dm else "",
                  duracion=C.duracion_min(habilidad, nivel), kpis=hab.get("kpis", []), pesos=(hab.get("pesos") or {}).get(nivel, {}),
                  test=K.TEST_LIDERAZGO if hab.get("test") == "liderazgo" else None, estilo=estilo, estilos=K.ESTILOS_LIDERAZGO, historial=historial,
                  audio_ok=settings.AUDIO_ENABLED and bool(hab.get("audio")), foto_ok=settings.FOTO_ENABLED and bool(hab.get("foto")))


@router.post("/entrenar/liderazgo/test")
async def test_liderazgo(request: Request, u: dict = Depends(entrena)):
    """Test de estilo de liderazgo (grid gerencial, 10 preguntas a/b/c/d): se guarda en el nivel de la habilidad y lo usa Patricia para diseñar la escena."""
    form = await request.form()
    verificar_csrf(request, u, form.get("csrf"))
    _hab_entrenable(u, "liderazgo")
    from ..agents import conocimiento as K
    respuestas = [str(form.get(f"q{i}", "")) for i in range(len(K.TEST_LIDERAZGO))]
    if any(r not in ("a", "b", "c", "d") for r in respuestas):
        raise HTTPException(400, "Responde las 10 preguntas del test.")
    est = K.estilo_liderazgo(respuestas)
    est["fecha"] = db.now()
    niv = db.nivel(u["id"], "liderazgo") or {}
    db.guardar_nivel(u["id"], "liderazgo", niv.get("nivel") or C.nivel_generico_estimado((db.perfil(u["id"]).get("onboarding") or {})), competencias={"estilo": est})
    db.log("info", "sesion", f"Test de liderazgo de {u['email']}", f"estilo {est['predominante']}", u["email"])
    return RedirectResponse("/entrenar/liderazgo", status_code=303)


@router.post("/entrenar/{habilidad}/iniciar")
def entrenar_iniciar(request: Request, habilidad: str, u: dict = Depends(entrena), csrf: str = Form(""), item: int = Form(0), nivel: str = Form(""),
                     competencia: str = Form(""), producto: str = Form(""), objetivo: str = Form("")):
    verificar_csrf(request, u, csrf)
    hab = _hab_entrenable(u, habilidad)
    if _encuesta_obligatoria(u):
        raise HTTPException(409, "Antes de tu siguiente práctica responde la encuesta de experiencia.")
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


# ── Laboratorio DM ───────────────────────────────────────────────────────────
def _lab_disponible(u: dict) -> dict:
    hab = C.habilidad("ruta_dm")
    if not hab or hab not in _habilidades(u):
        raise HTTPException(404, "El Laboratorio DM no está habilitado para tu empresa.")
    return hab


@router.get("/laboratorio")
def laboratorio(request: Request, u: dict = Depends(colab), item: int | None = None):
    hab = _lab_disponible(u)
    perfil = db.perfil(u["id"])
    if perfil.get("estado") != "completo":
        return RedirectResponse("/diagnostico", status_code=307)
    en_curso = db.sesion_en_curso(u["id"])
    if en_curso:
        return RedirectResponse(f"/sesion/{en_curso['id']}", status_code=307)
    bloqueo = _encuesta_obligatoria(u)
    if bloqueo:
        return bloqueo
    it = db.roadmap_item(item) if item else None
    if it and (it["usuario_id"] != u["id"] or it["estado"] != "pendiente" or it.get("tipo") != "laboratorio"):
        it = None
    previos = db.sesiones(usuario_id=u["id"], habilidad="ruta_dm", estado="completada", tipo="laboratorio", limite=10)
    return render(request, "laboratorio.html", u, hab=hab, item=it, avatar=AVATARES["juan"], previos=previos, lab=L, niv=db.nivel(u["id"], "ruta_dm") or {},
                  ultimo=(previos[0].get("resultado") or {}).get("laboratorio") if previos else None)


@router.post("/laboratorio/iniciar")
def laboratorio_iniciar(request: Request, u: dict = Depends(colab), csrf: str = Form(""), item: int = Form(0)):
    verificar_csrf(request, u, csrf)
    _lab_disponible(u)
    it = db.roadmap_item(item) if item else None
    if it and (it["usuario_id"] != u["id"] or it["estado"] != "pendiente"):
        it = None
    try:
        s = motor.iniciar(db.usuario(u["id"]), "ruta_dm", item=it, tipo="laboratorio", voluntaria=it is None)
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
                  turnos_max=C.turnos_max_sesion(s), duracion=C.duracion_sesion(s), propia=s["usuario_id"] == u["id"], micro_min=settings.MICRO_MINUTOS,
                  audio_ok=settings.AUDIO_ENABLED and bool(hab.get("audio")) and s["tipo"] == "practica", foto_ok=settings.FOTO_ENABLED and bool(hab.get("foto")) and s["tipo"] == "practica",
                  salida="/diagnostico" if s["tipo"] == "diagnostico" else ("/entrenar/liderazgo" if u["rol"] == "director" else "/hoy"))


@router.post("/sesion/{sid}/descartar")
def sesion_descartar(request: Request, sid: int, u: dict = Depends(requiere_usuario), csrf: str = Form("")):
    """Descartar desde Hoy o el catálogo (formulario): libera a la persona de una práctica abierta, trabada o con error."""
    verificar_csrf(request, u, csrf)
    s = db.sesion(sid)
    if not s or s["usuario_id"] != u["id"]:
        raise HTTPException(404, "Sesión no encontrada")
    if s["estado"] in ("en_curso", "error") or (s["estado"] == "analizando" and not motor.analizando_ahora(sid)):
        motor.descartar(s)
        if s["tipo"] == "diagnostico":
            db.guardar_perfil(u["id"], estado="onboarding", sesion_diagnostico_id=None)
        db.log("info", "sesion", f"Sesión {sid} descartada por la persona", s["estado"], u["email"])
    destino = request.headers.get("referer") or "/hoy"
    return RedirectResponse(destino if destino.split("?")[0].endswith(("/hoy", "/catalogo", "/entrenar/liderazgo")) else "/hoy", status_code=303)


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
                     if x["id"] < sid and x["tipo"] == ("laboratorio" if s["tipo"] == "laboratorio" else "practica")), None)
    chat = db.obtener_chat(u["id"], f"reporte:{sid}") if s["usuario_id"] == u["id"] else None
    analisis = db.analisis(s["empresa_id"], tipo="post_sesion", sesion_id=sid, limite=1) if u["rol"] in ("rrhh", "director", "dg") else []
    return render(request, "reporte.html", u, s=s, hab=hab, res=res, avatar=AVATARES[s["agente"]], anterior=anterior, chat=chat, propia=s["usuario_id"] == u["id"],
                  kpis_def={k["id"]: k for k in hab.get("kpis", [])}, pesos=(hab.get("pesos") or {}).get(s.get("nivel") or "", {}),
                  siguiente=db.siguiente_item(s["usuario_id"], s["habilidad"]), analisis=analisis[0] if analisis else None,
                  mostrar_transcripcion=puede_ver_transcripcion(u, s), mensajes=db.mensajes(sid) if puede_ver_transcripcion(u, s) else [],
                  minutos=motor.minutos_transcurridos(s), encuesta_pendiente=db.pendiente_encuesta(u["id"]) if s["usuario_id"] == u["id"] else None)


# ── encuesta de primera experiencia ──────────────────────────────────────────
@router.get("/encuesta")
def encuesta(request: Request, u: dict = Depends(colab), obligatoria: int = 0):
    from .. import encuesta as ENC
    return render(request, "encuesta.html", u, secciones=ENC.SECCIONES, previo={}, faltan=[], hecha=bool(db.encuesta_de(u["id"])), obligatoria=bool(obligatoria),
                  intro=ENC.INTRO, gracias=ENC.GRACIAS)


@router.post("/encuesta")
async def encuesta_post(request: Request, u: dict = Depends(colab)):
    from .. import encuesta as ENC
    form = await request.form()
    verificar_csrf(request, u, form.get("csrf"))
    if db.encuesta_de(u["id"]):
        return RedirectResponse("/encuesta", status_code=303)
    respuestas, faltan = ENC.validar(form)
    if faltan:
        return render(request, "encuesta.html", u, secciones=ENC.SECCIONES, previo=respuestas, faltan=faltan, hecha=False, status_code=400, obligatoria=True, intro=ENC.INTRO, gracias=ENC.GRACIAS)
    primera = db.pendiente_encuesta(u["id"])
    db.guardar_encuesta(u["id"], u.get("empresa_id"), respuestas, sesion_id=(primera or {}).get("id"))
    db.log("info", "encuesta", f"Encuesta de experiencia respondida por {u['email']}", f"calificación {respuestas.get('calificacion')} · NPS {respuestas.get('nps')}", u["email"])
    for m in db.usuarios(rol="superadmin"):
        db.notificar(m["id"], f"Nueva encuesta de experiencia: {u['nombre']}", f"Calificación {respuestas.get('calificacion')}/10 · NPS {respuestas.get('nps')} · pagaría: {respuestas.get('pagaria')}", "/admin/encuestas", "exito")
    return RedirectResponse("/encuesta", status_code=303)


@router.get("/historial")
def historial(request: Request, u: dict = Depends(entrena)):
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
