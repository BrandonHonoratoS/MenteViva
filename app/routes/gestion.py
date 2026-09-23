"""RRHH: organización, áreas y personas, aprobaciones, metas, análisis, evaluaciones y chat con el Analista (también directores/DG)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db, metrics
from ..agents import analista
from ..agents import catalogo as C
from ..security import alcance_usuarios, requiere_rol, verificar_csrf
from ..web import render

router = APIRouter()
rrhh = requiere_rol("rrhh")
managers = requiere_rol("rrhh", "director", "dg")
rrhh_o_director = requiere_rol("rrhh", "director")


@router.get("/rrhh")
def rrhh_dashboard(request: Request, u: dict = Depends(rrhh), dias: int = 30):
    k = metrics.kpis_organizacion(u["empresa_id"], dias=max(7, min(365, dias)))
    return render(request, "organizacion.html", u, k=k, dias=dias, propuestas=db.propuestas(u["empresa_id"])[:8], analisis=db.analisis(u["empresa_id"], limite=4),
                  titulo="Organización", areas=db.areas(u["empresa_id"]))


# ── áreas y personas ─────────────────────────────────────────────────────────
@router.get("/gestion")
def gestion(request: Request, u: dict = Depends(rrhh), ok: str = "", error: str = "", clave: str = ""):
    return render(request, "gestion.html", u, areas=db.areas(u["empresa_id"]), usuarios=db.usuarios(u["empresa_id"], activos=None), ok=ok, error=error, clave=clave,
                  roles=[("colaborador", "Colaborador"), ("director", "Director de área"), ("rrhh", "Recursos Humanos"), ("dg", "Dirección General")])


@router.post("/gestion/areas")
def area_crear(request: Request, u: dict = Depends(rrhh), csrf: str = Form(""), nombre: str = Form(""), director_id: int = Form(0)):
    verificar_csrf(request, u, csrf)
    if not nombre.strip():
        return RedirectResponse("/gestion?error=Escribe+el+nombre+del+área", status_code=303)
    try:
        db.crear_area(u["empresa_id"], nombre, director_id or None)
    except Exception:  # noqa: BLE001 — nombre duplicado
        return RedirectResponse("/gestion?error=Ya+existe+un+área+con+ese+nombre", status_code=303)
    db.log("info", "gestion", f"Área creada: {nombre}", "", u["email"])
    return RedirectResponse("/gestion?ok=Área+creada", status_code=303)


@router.post("/gestion/areas/{aid}")
def area_editar(request: Request, aid: int, u: dict = Depends(rrhh), csrf: str = Form(""), nombre: str = Form(""), director_id: int = Form(0)):
    verificar_csrf(request, u, csrf)
    a = db.area(aid)
    if not a or a["empresa_id"] != u["empresa_id"]:
        raise HTTPException(404)
    if director_id:
        d = db.usuario(director_id)
        if not d or d["empresa_id"] != u["empresa_id"]:
            raise HTTPException(400, "Director inválido")
        if d["rol"] == "colaborador":
            db.actualizar_usuario(d["id"], rol="director")
    db.actualizar_area(aid, nombre=nombre or None, director_id=director_id)
    return RedirectResponse("/gestion?ok=Área+actualizada", status_code=303)


@router.post("/gestion/usuarios")
def usuario_crear(request: Request, u: dict = Depends(rrhh), csrf: str = Form(""), nombre: str = Form(""), email: str = Form(""), puesto: str = Form(""),
                  rol: str = Form("colaborador"), area_id: int = Form(0)):
    verificar_csrf(request, u, csrf)
    if rol not in ("colaborador", "director", "rrhh", "dg") or "@" not in email or not nombre.strip():
        return RedirectResponse("/gestion?error=Revisa+nombre,+correo+y+rol", status_code=303)
    clave = "MV-" + secrets.token_urlsafe(6)
    try:
        uid = db.crear_usuario(email, clave, nombre, rol, u["empresa_id"], area_id or None, puesto.strip()[:80], debe_cambiar=True)
    except Exception:  # noqa: BLE001 — correo duplicado
        return RedirectResponse("/gestion?error=Ese+correo+ya+está+registrado", status_code=303)
    if rol == "director" and area_id:
        db.actualizar_area(area_id, director_id=uid)
    db.log("info", "gestion", f"Usuario creado: {email} ({rol})", "", u["email"])
    return RedirectResponse(f"/gestion?ok=Usuario+creado&clave={clave}", status_code=303)


@router.post("/gestion/usuarios/{uid}")
def usuario_editar(request: Request, uid: int, u: dict = Depends(rrhh), csrf: str = Form(""), accion: str = Form("editar"), nombre: str = Form(""), puesto: str = Form(""),
                   rol: str = Form(""), area_id: int = Form(0)):
    verificar_csrf(request, u, csrf)
    x = db.usuario(uid)
    if not x or x["empresa_id"] != u["empresa_id"] or x["rol"] == "superadmin":
        raise HTTPException(404)
    if accion == "desactivar":
        if x["id"] == u["id"]:
            return RedirectResponse("/gestion?error=No+puedes+desactivar+tu+propia+cuenta", status_code=303)
        db.actualizar_usuario(uid, activo=0)
        return RedirectResponse("/gestion?ok=Usuario+desactivado", status_code=303)
    if accion == "activar":
        db.actualizar_usuario(uid, activo=1)
        return RedirectResponse("/gestion?ok=Usuario+reactivado", status_code=303)
    if accion == "restablecer":
        clave = "MV-" + secrets.token_urlsafe(6)
        db.cambiar_password(uid, clave)
        with db.conn() as con:
            con.execute("UPDATE usuarios SET debe_cambiar_password=1 WHERE id=?", (uid,))
        db.log("info", "gestion", f"Contraseña restablecida: {x['email']}", "", u["email"])
        return RedirectResponse(f"/gestion?ok=Contraseña+temporal+generada&clave={clave}", status_code=303)
    campos = {}
    if nombre.strip():
        campos["nombre"] = nombre.strip()[:80]
    campos["puesto"] = puesto.strip()[:80]
    if rol in ("colaborador", "director", "rrhh", "dg"):
        campos["rol"] = rol
    campos["area_id"] = area_id or None
    db.actualizar_usuario(uid, **campos)
    return RedirectResponse("/gestion?ok=Usuario+actualizado", status_code=303)


# ── aprobaciones ─────────────────────────────────────────────────────────────
@router.get("/aprobaciones")
def aprobaciones(request: Request, u: dict = Depends(rrhh), estado: str = "pendiente"):
    return render(request, "aprobaciones.html", u, propuestas=db.propuestas(u["empresa_id"], estado=None if estado == "todas" else estado), estado=estado)


@router.post("/aprobaciones/{pid}")
def decidir(request: Request, pid: int, u: dict = Depends(rrhh), csrf: str = Form(""), decision: str = Form(""), motivo: str = Form("")):
    verificar_csrf(request, u, csrf)
    p = db.propuesta(pid)
    if not p or p["empresa_id"] != u["empresa_id"]:
        raise HTTPException(404)
    if decision not in ("aprobada", "rechazada", "atendida"):
        raise HTTPException(400, "Decisión inválida")
    if not db.decidir_propuesta(pid, decision, u["id"], motivo.strip()[:500]):
        return RedirectResponse("/aprobaciones?estado=todas", status_code=303)
    if decision == "aprobada":
        if p["tipo"] == "ascenso_dm":
            analista.aplicar_ascenso_dm(p, u)
        elif p["tipo"] == "roadmap":
            rid = (p.get("detalle") or {}).get("roadmap_id")
            if rid:
                db.actualizar_roadmap(rid, estado="activo", aprobado_por=u["id"])
                db.notificar(p["usuario_id"], "RRHH aprobó tu plan", f"Tu plan de {C.HABILIDADES.get((p.get('detalle') or {}).get('habilidad', ''), {}).get('nombre', '')} ya está activo.", "/roadmaps", "exito")
    elif decision == "rechazada" and p["tipo"] == "roadmap":
        rid = (p.get("detalle") or {}).get("roadmap_id")
        if rid:
            db.actualizar_roadmap(rid, estado="rechazado")
    if p.get("usuario_id") and p["tipo"] in ("ascenso_dm",) and decision == "rechazada":
        db.notificar(p["usuario_id"], "Ascenso en revisión", "RRHH decidió esperar; sigue entrenando las competencias del siguiente nivel.", "/roadmaps", "aviso")
    db.log("info", "aprobaciones", f"Propuesta #{pid} {decision}", p["titulo"], u["email"])
    return RedirectResponse("/aprobaciones", status_code=303)


# ── metas ────────────────────────────────────────────────────────────────────
@router.get("/metas")
def metas(request: Request, u: dict = Depends(rrhh_o_director), ok: str = ""):
    area_id = u.get("area_id") if u["rol"] == "director" else None
    habs = C.habilidades_empresa(db.empresa(u["empresa_id"]))
    return render(request, "metas.html", u, metas=db.metas(u["empresa_id"], area_id=area_id, solo_activas=False), areas=db.areas(u["empresa_id"]),
                  colaboradores=[x for x in alcance_usuarios(u) if x["rol"] == "colaborador"], habilidades=habs, ok=ok, competencias_dm=[c for n in C.RUTA_DM for c in n["competencias"]])


@router.post("/metas")
def meta_crear(request: Request, u: dict = Depends(rrhh_o_director), csrf: str = Form(""), habilidad: str = Form(""), competencia: str = Form(""),
               score_minimo: float = Form(75), plazo: str = Form(""), prioridad: str = Form("media"), descripcion: str = Form(""), area_id: int = Form(0), usuario_id: int = Form(0)):
    verificar_csrf(request, u, csrf)
    if habilidad not in C.HABILIDADES:
        raise HTTPException(400, "Habilidad inválida")
    if u["rol"] == "director":
        area_id = u.get("area_id") or 0
        if usuario_id and not any(x["id"] == usuario_id for x in alcance_usuarios(u)):
            raise HTTPException(403, "Ese colaborador no está en tu área")
    db.crear_meta(u["empresa_id"], habilidad, u["id"], area_id or None, usuario_id or None, competencia.strip()[:80], max(0, min(100, score_minimo)), plazo or None,
                  prioridad if prioridad in ("alta", "media", "baja") else "media", descripcion.strip()[:400])
    db.log("info", "metas", f"Meta creada: {habilidad} ≥ {score_minimo}", descripcion[:100], u["email"])
    return RedirectResponse("/metas?ok=1", status_code=303)


@router.post("/metas/{mid}/cerrar")
def meta_cerrar(request: Request, mid: int, u: dict = Depends(rrhh_o_director), csrf: str = Form("")):
    verificar_csrf(request, u, csrf)
    db.cerrar_meta(mid)
    return RedirectResponse("/metas", status_code=303)


# ── análisis y chat con el Analista ──────────────────────────────────────────
@router.get("/analisis")
def analisis(request: Request, u: dict = Depends(managers), tipo: str = ""):
    area_id = u.get("area_id") if u["rol"] == "director" else None
    lista = db.analisis(u["empresa_id"], tipo=tipo or None, area_id=area_id, limite=120)
    if u["rol"] == "director":
        ids = {x["id"] for x in alcance_usuarios(u)}
        lista = [a for a in lista if (a.get("usuario_id") in ids) or (a.get("area_id") == area_id) or (a["tipo"] == "investigacion")]
    return render(request, "analisis.html", u, lista=lista, tipo=tipo)


@router.get("/analista")
def analista_chat(request: Request, u: dict = Depends(managers)):
    ch = db.obtener_chat(u["id"], "analista", "Analista")
    sugerencias = {
        "director": ["¿Quién de mi equipo necesita atención esta semana y por qué?", "Dame la ficha de mi colaborador con menor score", "¿Qué dice la evidencia sobre cómo entrenar manejo de objeciones?"],
        "rrhh": ["Resume el estado de la organización en 5 líneas", "¿Quién está listo para ascender en la Ruta DM?", "Investiga mejores prácticas para medir transferencia del aprendizaje"],
        "dg": ["¿Cómo va la organización este mes?", "¿Qué área avanza más y cuál necesita apoyo?", "¿Qué retorno estamos viendo del entrenamiento?"],
    }.get(u["rol"], [])
    return render(request, "analista.html", u, chat=ch, sugerencias=sugerencias, presupuesto_full=db.presupuesto())


@router.get("/evaluaciones")
def evaluaciones(request: Request, u: dict = Depends(rrhh)):
    colabs = [x for x in db.usuarios(u["empresa_id"]) if x["rol"] == "colaborador"]
    evals = db.evaluaciones(empresa_id=u["empresa_id"])
    ult = {}
    for e in evals:
        ult.setdefault((e["usuario_id"], e["tipo"]), e)
    filas = [{"u": c, "lider": ult.get((c["id"], "lider")), "auto": ult.get((c["id"], "auto"))} for c in colabs]
    return render(request, "evaluaciones.html", u, filas=filas, periodo=db.periodo(), evals=evals[:50])
