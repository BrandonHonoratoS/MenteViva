"""Exportes: PDF de sesión y ficha, Excel de tablero y sesiones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .. import db, metrics
from ..reports import excel, pdf
from ..security import puede_ver_usuario, requiere_rol, requiere_usuario

router = APIRouter()


@router.get("/sesion/{sid}/reporte.pdf")
def sesion_pdf(sid: int, u: dict = Depends(requiere_usuario)):
    s = db.sesion(sid)
    if not s or s["estado"] != "completada" or s["tipo"] != "practica" or not puede_ver_usuario(u, db.usuario(s["usuario_id"])):
        raise HTTPException(404, "Reporte no disponible")
    datos = pdf.reporte_sesion(s, db.usuario(s["usuario_id"]))
    db.log("info", "exportes", f"PDF sesión {sid}", "", u["email"])
    return Response(datos, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="menteviva_sesion_{sid}.pdf"'})


@router.get("/colaborador/{uid}/ficha.pdf")
def ficha_pdf(uid: int, u: dict = Depends(requiere_usuario)):
    x = db.usuario(uid)
    if not x or not puede_ver_usuario(u, x):
        raise HTTPException(404)
    datos = pdf.ficha_colaborador(metrics.ficha(x, incluir_feedback=True))
    return Response(datos, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="menteviva_ficha_{uid}.pdf"'})


@router.get("/exportar/tablero.xlsx")
def tablero_xlsx(u: dict = Depends(requiere_rol("rrhh", "dg", "director")), dias: int = 30):
    area_id = u.get("area_id") if u["rol"] == "director" else None
    k = metrics.kpis_organizacion(u["empresa_id"], area_id=area_id, dias=max(7, min(365, dias)))
    e = db.empresa(u["empresa_id"]) or {}
    datos = excel.tablero(k, e.get("nombre", ""), f"Área {u.get('area_nombre')}" if area_id else "Organización")
    db.log("info", "exportes", "Excel tablero", "", u["email"])
    return Response(datos, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="menteviva_tablero.xlsx"'})


@router.get("/exportar/sesiones.xlsx")
def sesiones_xlsx(u: dict = Depends(requiere_rol("rrhh", "dg", "director"))):
    area_id = u.get("area_id") if u["rol"] == "director" else None
    ss = [s for s in db.sesiones(empresa_id=u["empresa_id"], area_id=area_id, estado="completada", limite=5000) if s["tipo"] == "practica"]
    return Response(excel.sesiones(ss), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="menteviva_sesiones.xlsx"'})
