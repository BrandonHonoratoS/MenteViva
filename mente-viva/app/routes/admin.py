"""Superadministración (equipo Mente Viva): empresas, habilidades personalizadas, primer usuario de RRHH, modelo de IA, presupuesto, uso y bitácora."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db
from ..agents import catalogo as C
from ..config import settings
from ..security import requiere_rol, verificar_csrf
from ..web import render

router = APIRouter(prefix="/admin")
sa = requiere_rol("superadmin")


@router.get("")
def admin(request: Request, u: dict = Depends(sa), ok: str = "", error: str = "", clave: str = ""):
    return render(request, "admin.html", u, empresas=db.empresas(), personalizadas=[h for h in C.HABILIDADES.values() if h["personalizada"]],
                  config={"modelo_principal": db.get_ajuste("modelo_principal", settings.GEMINI_MODEL), "modelo_ligero": db.get_ajuste("modelo_ligero", settings.GEMINI_MODEL_LIGERO),
                          "presupuesto_mxn": db.get_ajuste("presupuesto_mxn", settings.PRESUPUESTO_MXN), "tipo_cambio": db.get_ajuste("tipo_cambio", settings.TIPO_CAMBIO_MXN_USD),
                          "grounding_max_mes": db.get_ajuste("grounding_max_mes", settings.GROUNDING_MAX_MES), "proveedor": settings.LLM_PROVEEDOR,
                          "api_key": bool(settings.GEMINI_API_KEY), "precios": settings.PRICE_TABLE},
                  presupuesto_full=db.presupuesto(), ok=ok, error=error, clave=clave, superadmins=db.usuarios(rol="superadmin", activos=None))


@router.post("/empresas")
def empresa_crear(request: Request, u: dict = Depends(sa), csrf: str = Form(""), nombre: str = Form(""), industria: str = Form(""), rrhh_nombre: str = Form(""),
                  rrhh_email: str = Form(""), ruta_dm: int = Form(0)):
    verificar_csrf(request, u, csrf)
    if not nombre.strip():
        return RedirectResponse("/admin?error=Escribe+el+nombre+de+la+empresa", status_code=303)
    try:
        eid = db.crear_empresa(nombre, industria.strip()[:80], ["ruta_dm"] if ruta_dm else [])
    except Exception:  # noqa: BLE001
        return RedirectResponse("/admin?error=Ya+existe+esa+empresa", status_code=303)
    clave = ""
    if rrhh_email and "@" in rrhh_email:
        clave = "MV-" + secrets.token_urlsafe(6)
        try:
            db.crear_usuario(rrhh_email, clave, rrhh_nombre or "Recursos Humanos", "rrhh", eid, debe_cambiar=True)
        except Exception:  # noqa: BLE001
            clave = ""
            db.log("warn", "admin", "No se pudo crear el usuario RRHH", rrhh_email, u["email"])
    db.log("info", "admin", f"Empresa creada: {nombre}", "", u["email"])
    return RedirectResponse(f"/admin?ok=Empresa+creada&clave={clave}", status_code=303)


@router.post("/empresas/{eid}")
def empresa_editar(request: Request, eid: int, u: dict = Depends(sa), csrf: str = Form(""), accion: str = Form(""), habilidades: list[str] = Form([])):
    verificar_csrf(request, u, csrf)
    e = db.empresa(eid)
    if not e:
        raise HTTPException(404)
    if accion == "desactivar":
        db.actualizar_empresa(eid, activa=0)
    elif accion == "activar":
        db.actualizar_empresa(eid, activa=1)
    else:
        validas = [h for h in habilidades if h in C.HABILIDADES and C.HABILIDADES[h]["personalizada"]]
        db.actualizar_empresa(eid, habilidades_json=validas)
    return RedirectResponse("/admin?ok=Empresa+actualizada", status_code=303)


@router.post("/empresas/{eid}/rrhh")
def empresa_rrhh(request: Request, eid: int, u: dict = Depends(sa), csrf: str = Form(""), nombre: str = Form(""), email: str = Form("")):
    verificar_csrf(request, u, csrf)
    if not db.empresa(eid) or "@" not in email:
        raise HTTPException(400, "Datos inválidos")
    clave = "MV-" + secrets.token_urlsafe(6)
    try:
        db.crear_usuario(email, clave, nombre or "Recursos Humanos", "rrhh", eid, debe_cambiar=True)
    except Exception:  # noqa: BLE001
        return RedirectResponse("/admin?error=Ese+correo+ya+existe", status_code=303)
    return RedirectResponse(f"/admin?ok=Usuario+RRHH+creado&clave={clave}", status_code=303)


@router.post("/config")
def config(request: Request, u: dict = Depends(sa), csrf: str = Form(""), modelo_principal: str = Form(""), modelo_ligero: str = Form(""), presupuesto_mxn: float = Form(500),
           tipo_cambio: float = Form(20), grounding_max_mes: int = Form(40)):
    verificar_csrf(request, u, csrf)
    if modelo_principal.strip():
        db.set_ajuste("modelo_principal", modelo_principal.strip())
    if modelo_ligero.strip():
        db.set_ajuste("modelo_ligero", modelo_ligero.strip())
    db.set_ajuste("presupuesto_mxn", max(0.0, presupuesto_mxn))
    db.set_ajuste("tipo_cambio", max(1.0, tipo_cambio))
    db.set_ajuste("grounding_max_mes", max(0, grounding_max_mes))
    db.log("info", "admin", "Configuración de IA actualizada", f"{modelo_principal}/{modelo_ligero} · {presupuesto_mxn} MXN · tc {tipo_cambio}", u["email"])
    return RedirectResponse("/admin?ok=Configuración+guardada", status_code=303)


@router.post("/superadmins")
def superadmin_crear(request: Request, u: dict = Depends(sa), csrf: str = Form(""), nombre: str = Form(""), email: str = Form("")):
    verificar_csrf(request, u, csrf)
    if "@" not in email:
        raise HTTPException(400)
    clave = "MV-" + secrets.token_urlsafe(8)
    try:
        db.crear_usuario(email, clave, nombre or "Mente Viva", "superadmin", None, debe_cambiar=True)
    except Exception:  # noqa: BLE001
        return RedirectResponse("/admin?error=Ese+correo+ya+existe", status_code=303)
    return RedirectResponse(f"/admin?ok=Superadministrador+creado&clave={clave}", status_code=303)


@router.get("/uso")
def uso(request: Request, u: dict = Depends(sa), periodo: str = ""):
    p = periodo or db.periodo()
    return render(request, "uso.html", u, uso=db.uso_periodo(p), presupuesto_full=db.presupuesto(), periodo=p)


@router.get("/bitacora")
def bitacora(request: Request, u: dict = Depends(sa), nivel: str = ""):
    return render(request, "bitacora.html", u, filas=db.bitacora(400, nivel or None), nivel=nivel)
