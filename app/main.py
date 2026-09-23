"""Mente Viva · plataforma de entrenamiento de habilidades blandas con agentes de IA (FastAPI)."""
from __future__ import annotations

import logging
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db, scheduler
from .config import settings
from .routes import admin, api, auth, colaborador, exportes, gestion, tableros
from .security import COOKIE, usuario_actual
from .web import render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("mv")

@asynccontextmanager
async def _vida(app: FastAPI):
    db.init_db()
    scheduler.iniciar()
    log.info("%s v%s lista · LLM=%s · datos=%s", settings.APP_NAME, settings.VERSION, settings.LLM_PROVEEDOR, settings.DB_PATH)
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, docs_url=None, redoc_url=None, openapi_url=None, lifespan=_vida)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "web" / "static")), name="static")
for r in (auth.router, colaborador.router, api.router, gestion.router, tableros.router, admin.router, exportes.router):
    app.include_router(r)


@app.middleware("http")
async def seguridad(request: Request, call_next):
    """Cabeceras de seguridad y bloqueo de peticiones mutantes de origen cruzado (primera barrera CSRF)."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sfs = request.headers.get("sec-fetch-site", "")
        origen = request.headers.get("origin", "")
        host = request.headers.get("host", "")
        if sfs in ("cross-site",) or (origen and host and origen.split("://")[-1] != host and sfs != "none"):
            db.log("warn", "seguridad", "Petición rechazada por origen cruzado", f"{request.method} {request.url.path} origen={origen}")
            return JSONResponse({"error": "Origen no permitido"}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    resp.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com 'unsafe-inline'; "
                                               "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; "
                                               "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    if settings.APP_ENV == "production":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    if exc.status_code == 307 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=307)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    u = usuario_actual(request)
    return render(request, "error.html", u, status_code=exc.status_code, codigo=exc.status_code, detalle=exc.detail)


@app.exception_handler(Exception)
async def _exc(request: Request, exc: Exception):
    log.exception("Error no controlado en %s", request.url.path)
    db.log("error", "app", f"Error en {request.url.path}", str(exc)[:500])
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Error interno. Inténtalo de nuevo."}, status_code=500)
    return render(request, "error.html", usuario_actual(request), status_code=500, codigo=500, detalle="Algo salió mal. El equipo Mente Viva ya tiene el registro.")


@app.get("/")
def raiz(request: Request):
    u = usuario_actual(request)
    if not u:
        return RedirectResponse("/login", status_code=307)
    return RedirectResponse(auth.inicio_por_rol(u), status_code=307)


@app.get("/salud")
def salud():
    return {"ok": True, "version": settings.VERSION}
