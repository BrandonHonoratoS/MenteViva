"""Renderizado de plantillas con el contexto común (usuario, navegación por rol, presupuesto, notificaciones)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.templating import Jinja2Templates

from . import db
from .agents import catalogo as C
from .agents.avatares import AVATARES
from .config import settings
from .security import NOMBRES_ROL

templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))

NAV = {
    "colaborador": [("/hoy", "Hoy", "home"), ("/roadmaps", "Mis planes", "map"), ("/catalogo", "Entrenar", "spark"), ("/mi-diagnostico", "Mi diagnóstico", "user"),
                    ("/historial", "Historial", "clock"), ("/autoevaluacion", "Autoevaluación", "check")],
    "director": [("/equipo", "Mi equipo", "team"), ("/metas", "Metas", "target"), ("/analista", "Analista", "brain"), ("/analisis", "Análisis", "doc")],
    "rrhh": [("/rrhh", "Organización", "chart"), ("/gestion", "Áreas y personas", "team"), ("/aprobaciones", "Aprobaciones", "check"), ("/metas", "Metas", "target"),
             ("/analista", "Analista", "brain"), ("/analisis", "Análisis", "doc"), ("/evaluaciones", "Evaluaciones", "star")],
    "dg": [("/direccion", "Dirección", "chart"), ("/analista", "Analista", "brain"), ("/analisis", "Análisis", "doc")],
    "superadmin": [("/admin", "Plataforma", "settings"), ("/admin/uso", "Uso de IA", "chart"), ("/admin/bitacora", "Bitácora", "doc")],
}


def fecha_local(ts: str | None, fmt: str = "%d %b %Y · %H:%M") -> str:
    if not ts:
        return "—"
    try:
        d = datetime.fromisoformat(ts)
        return d.astimezone(ZoneInfo(settings.TZ)).strftime(fmt)
    except (ValueError, TypeError):
        return ts


def fecha_corta(ts: str | None) -> str:
    return fecha_local(ts, "%d %b")


def _filtros():
    templates.env.filters["fecha"] = fecha_local
    templates.env.filters["fecha_corta"] = fecha_corta
    templates.env.filters["tojson_safe"] = lambda v: json.dumps(v, ensure_ascii=False, default=str).replace("</", "<\\/")
    templates.env.filters["num"] = lambda v, d=0: ("—" if v is None else (f"{v:,.{d}f}"))
    templates.env.filters["hab"] = lambda h: C.HABILIDADES.get(h, {}).get("nombre", h)
    templates.env.filters["hab_corto"] = lambda h: C.HABILIDADES.get(h, {}).get("corto", h)
    templates.env.filters["semaforo"] = C.semaforo
    templates.env.globals.update(AVATARES=AVATARES, HABILIDADES=C.HABILIDADES, CATEGORIAS=C.CATEGORIAS, RUTA_DM=C.RUTA_DM, NOMBRES_ROL=NOMBRES_ROL,
                                 NOMBRE_FORMATO=C.NOMBRE_FORMATO, APP=settings.APP_NAME, TAGLINE=settings.TAGLINE, VERSION=settings.VERSION)


_filtros()


def render(request: Request, nombre: str, usuario: dict | None = None, status_code: int = 200, **ctx):
    base = {"request": request, "u": usuario, "nav": NAV.get((usuario or {}).get("rol", ""), []), "ruta": request.url.path}
    if usuario:
        base["csrf"] = usuario.get("csrf", "")
        base["no_leidas"] = len(db.notificaciones(usuario["id"], solo_no_leidas=True, limite=20))
        if usuario["rol"] in ("superadmin", "rrhh"):
            base["presupuesto"] = db.presupuesto()
        else:
            p = db.presupuesto()
            base["presupuesto"] = {"agotado": p["agotado"], "aviso": p["aviso"], "pct": p["pct"]}
        base["llm_simulado"] = settings.LLM_PROVEEDOR == "stub"
    base.update(ctx)
    return templates.TemplateResponse(request, nombre, base, status_code=status_code)
