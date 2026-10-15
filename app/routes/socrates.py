"""Sócrates: biblioteca de master classes personalizadas, lección y chat de dudas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import db
from ..agents import catalogo as C
from ..agents import socrates as S
from ..llm import PresupuestoAgotado
from ..llm.gemini import ErrorLLM
from ..security import requiere_rol, requiere_usuario, verificar_csrf
from ..web import render

router = APIRouter()
colab = requiere_rol("colaborador")


def _habilidades(u: dict) -> list[dict]:
    return C.habilidades_empresa(db.empresa(u.get("empresa_id")))


@router.get("/socrates")
def biblioteca(request: Request, u: dict = Depends(colab), error: str = ""):
    perfil = db.perfil(u["id"])
    if perfil.get("estado") != "completo":
        return RedirectResponse("/diagnostico", status_code=307)
    habs, _otras = C.habilidades_relevantes(perfil.get("onboarding") or {}, perfil.get("diagnostico"), _habilidades(u))
    niveles = db.niveles(u["id"])
    mias = db.lecciones(u["id"])
    por_clave = {lec["clave"]: lec for lec in mias}
    # lecciones ligadas al plan: los próximos ítems pendientes de cada roadmap activo
    del_plan = []
    for rm in db.roadmaps(u["id"], ("activo",)):
        for it in [x for x in rm["items"] if x["estado"] == "pendiente"][:3]:
            tema = it.get("competencia") or S.tema_para_item(rm["habilidad"], it)
            del_plan.append({"item": it, "habilidad": rm["habilidad"], "tema": tema, "leccion": por_clave.get(db._clave_leccion(u["id"], rm["habilidad"], tema))})
    biblio = []
    for h in habs:
        temas = S.temas_biblioteca(h["id"], (niveles.get("ruta_dm") or {}).get("nivel"))
        for tm in temas:
            tm["leccion"] = por_clave.get(db._clave_leccion(u["id"], h["id"], tm["tema"]))
        biblio.append({"hab": h, "temas": temas})
    return render(request, "socrates.html", u, avatar=S.AVATAR, del_plan=del_plan, biblioteca=biblio, lecciones=mias, restantes=max(0, S.settings.SOCRATES_MAX_MES - db.lecciones_mes(u["id"])), error=error[:200])


@router.post("/socrates/estudiar")
def estudiar(request: Request, u: dict = Depends(colab), csrf: str = Form(""), habilidad: str = Form(""), tema: str = Form(""), competencia: str = Form(""), item: int = Form(0)):
    verificar_csrf(request, u, csrf)
    hab = C.habilidad(habilidad)
    if not hab or hab not in _habilidades(u) or not tema.strip():
        raise HTTPException(400, "Tema o habilidad no válidos")
    it = db.roadmap_item(item) if item else None
    if it and (it["usuario_id"] != u["id"] or it["habilidad"] != habilidad):
        it = None
    try:
        lec = S.obtener_o_crear(db.usuario(u["id"]), habilidad, tema.strip()[:120], competencia=competencia.strip()[:80], item=it)
    except (PresupuestoAgotado, ErrorLLM) as e:
        from urllib.parse import quote
        return RedirectResponse(f"/socrates?error={quote(str(e)[:200])}", status_code=303)
    return RedirectResponse(f"/socrates/{lec['id']}", status_code=303)


@router.get("/socrates/{lid}")
def leccion(request: Request, lid: int, u: dict = Depends(requiere_usuario)):
    lec = db.leccion(lid)
    if not lec or (lec["usuario_id"] != u["id"] and u["rol"] not in ("rrhh", "superadmin")):
        raise HTTPException(404, "Lección no encontrada")
    if lec["estado"] == "lista" and lec["usuario_id"] == u["id"] and not lec.get("leida_en"):
        db.actualizar_leccion(lid, leida_en=db.now())
        db.registrar_actividad(u["id"], minutos=5, bloques=1)
    chat = db.obtener_chat(u["id"], f"leccion:{lid}") if lec["usuario_id"] == u["id"] else None
    item = db.roadmap_item(lec["roadmap_item_id"]) if lec.get("roadmap_item_id") else None
    return render(request, "leccion.html", u, lec=lec, c=lec.get("contenido") or {}, avatar=S.AVATAR, chat=chat, item=item, hab=C.HABILIDADES.get(lec["habilidad"], {}),
                  propia=lec["usuario_id"] == u["id"])


@router.post("/socrates/{lid}/reintentar")
def reintentar(request: Request, lid: int, u: dict = Depends(colab), csrf: str = Form("")):
    verificar_csrf(request, u, csrf)
    lec = db.leccion(lid)
    if not lec or lec["usuario_id"] != u["id"]:
        raise HTTPException(404, "Lección no encontrada")
    S.reintentar(lid)
    return RedirectResponse(f"/socrates/{lid}", status_code=303)
