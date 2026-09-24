"""Tableros de Dirección General y Director de área, ficha del colaborador y evaluación del líder."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db, metrics
from ..agents import catalogo as C
from ..security import puede_ver_usuario, requiere_rol, requiere_usuario, verificar_csrf
from ..web import render

router = APIRouter()


@router.get("/direccion")
def direccion(request: Request, u: dict = Depends(requiere_rol("dg", "rrhh")), dias: int = 30):
    k = metrics.kpis_organizacion(u["empresa_id"], dias=max(7, min(365, dias)))
    return render(request, "organizacion.html", u, k=k, dias=dias, propuestas=db.propuestas(u["empresa_id"])[:6] if u["rol"] == "rrhh" else [],
                  analisis=db.analisis(u["empresa_id"], limite=4), titulo="Dirección General", areas=db.areas(u["empresa_id"]))


@router.get("/equipo")
def equipo(request: Request, u: dict = Depends(requiere_rol("director")), dias: int = 30):
    if not u.get("area_id"):
        return render(request, "error.html", u, codigo=200, detalle="Aún no tienes un área asignada. Pide a RRHH que te asigne como director de tu área.")
    k = metrics.kpis_organizacion(u["empresa_id"], area_id=u["area_id"], dias=max(7, min(365, dias)))
    area = db.area(u["area_id"])
    pendientes_eval = [r for r in k["colaboradores_resumen"] if not any(e["periodo"] == db.periodo() for e in db.evaluaciones(usuario_id=r["id"], tipo="lider"))]
    return render(request, "equipo.html", u, k=k, dias=dias, area=area, analisis=db.analisis(u["empresa_id"], area_id=u["area_id"], limite=4),
                  metas=db.metas(u["empresa_id"], area_id=u["area_id"])[:5], pendientes_eval=pendientes_eval, periodo=db.periodo())


@router.get("/colaborador/{uid}")
def colaborador(request: Request, uid: int, u: dict = Depends(requiere_usuario)):
    x = db.usuario(uid)
    if not x or not puede_ver_usuario(u, x) or x["rol"] not in ("colaborador", "director"):
        raise HTTPException(404, "Colaborador no encontrado")
    f = metrics.ficha(x, incluir_feedback=True)
    perfil = db.perfil(uid)
    return render(request, "colaborador.html", u, x=x, f=f, perfil=perfil, diag=perfil.get("diagnostico") or {}, roadmaps=db.roadmaps(uid, ("activo", "propuesto", "completado")),
                  sesiones=[s for s in db.sesiones(usuario_id=uid, limite=30) if s["tipo"] == "practica"], analisis=db.analisis(x["empresa_id"], usuario_id=uid, limite=10),
                  evaluaciones=db.evaluaciones(usuario_id=uid), propuestas=db.propuestas(x["empresa_id"], estado=None, usuario_id=uid, limite=10),
                  kpis={h: metrics.kpis_promedio(uid, h) for h in ("ventas", "entrevistas", "ruta_dm")}, periodo=db.periodo(),
                  puede_evaluar=u["rol"] == "director" and u.get("area_id") == x.get("area_id"), competencias=C.COMPETENCIAS_DIAGNOSTICO)


@router.get("/evaluar/{uid}")
def evaluar(request: Request, uid: int, u: dict = Depends(requiere_rol("director")), ok: int = 0):
    x = db.usuario(uid)
    if not x or not puede_ver_usuario(u, x) or x["rol"] != "colaborador":
        raise HTTPException(404, "Colaborador no encontrado")
    previas = db.evaluaciones(usuario_id=uid, tipo="lider")
    return render(request, "evaluar.html", u, x=x, preguntas=C.PREGUNTAS_LIDER, previas=previas, periodo=db.periodo(), ok=ok,
                  actual=next((e for e in previas if e["periodo"] == db.periodo()), None))


@router.post("/evaluar/{uid}")
async def evaluar_post(request: Request, uid: int, u: dict = Depends(requiere_rol("director"))):
    form = await request.form()
    verificar_csrf(request, u, form.get("csrf"))
    x = db.usuario(uid)
    if not x or not puede_ver_usuario(u, x) or x["rol"] != "colaborador":
        raise HTTPException(404)
    resp = {p["id"]: int(form.get(p["id"], 0) or 0) for p in C.PREGUNTAS_LIDER}
    if any(v < 1 or v > 5 for v in resp.values()):
        raise HTTPException(400, "Responde todas las preguntas del 1 al 5.")
    db.guardar_evaluacion("lider", u["id"], uid, db.periodo(), resp, str(form.get("comentario", ""))[:1000])
    db.notificar(uid, "Tu líder registró su evaluación del periodo", "Se integra a tus índices de aplicación y transferencia.", "/hoy", "info")
    db.log("info", "evaluaciones", f"Evaluación del líder para {x['email']}", db.periodo(), u["email"])
    return RedirectResponse(f"/evaluar/{uid}?ok=1", status_code=303)
